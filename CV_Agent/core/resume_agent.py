import os
import re
from dotenv import load_dotenv
from typing import TYPE_CHECKING, Any, Dict, List
import time
from collections import deque

from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI

from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from typing import Dict

load_dotenv()

if TYPE_CHECKING:
    from .graph import GraphState
 
# --- Rate Limiter ---
class RateLimiter:
    """A simple rate limiter to manage API calls efficiently."""

    def __init__(self, max_requests: int, per_seconds: int):
        self.max_requests = max_requests
        self.per_seconds = per_seconds
        self.timestamps = deque()

    def wait(self):
        """Blocks only when necessary and for the exact time required."""
        while True:
            now = time.time()
            # Remove timestamps older than the time window
            while self.timestamps and self.timestamps[0] <= now - self.per_seconds:
                self.timestamps.popleft()

            if len(self.timestamps) < self.max_requests:
                break  # We are under the limit

            # We are at the limit, calculate precise sleep time
            time_to_wait = self.per_seconds - (now - self.timestamps[0])
            if time_to_wait > 0:
                print(f"---RATE LIMITER: Pausing for {time_to_wait:.2f}s to respect API limits.---")
                time.sleep(time_to_wait)
    
    def add_request_timestamp(self):
        """Records that a request has been made."""
        self.timestamps.append(time.time())

# Gemini Flash has a limit of 15 RPM. We set it to 14 to be safe.
limiter = RateLimiter(max_requests=14, per_seconds=60)

def invoke_llm_with_rate_limiting(llm_structured_runnable: Any, prompt_text: str) -> Any:
    """
    Wrapper function that invokes a LangChain runnable while respecting our rate limit.
    """
    limiter.wait()
    try:
        response = llm_structured_runnable.invoke(prompt_text)
    finally:
        # Add timestamp even if call fails to prevent tight retry loops from
        # hammering the API and getting the key blocked.
        limiter.add_request_timestamp()
    return response

# --- Pydantic Models for Structured LLM Output ---
class ResumeSection(BaseModel):
    """A Pydantic model for any rewritten resume section."""
    rewritten_text: str = Field(
        description="The rewritten text for a resume section (e.g., summary or project description)."
    )

class SelectedProjects(BaseModel):
    """A Pydantic model for the list of selected project titles, ordered."""
    project_titles: List[str] = Field(
        description="A list of 4 selected project titles from the master resume, ordered from most to least relevant."
    )

class ShortenedProject(BaseModel):
    """Pydantic model for shortened project description."""
    shortened_description: str = Field(description="Shortened project description with min 3 bullets.")

class OptimizedProject(BaseModel):
    """Pydantic model for optimized project description with bolded keywords."""
    optimized_description: str = Field(description="Project description with bolded keywords.")

# --- LLM Initialization ---
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite-preview-06-17",
    temperature=0.3,
    model_kwargs={"response_format": {"type": "json_object"}},
)

# Copied and adapted from agents.py
def generate_summary(state: "GraphState") -> Dict[str, Any]:
    """Generates a tailored professional summary for the resume."""
    print("---AGENT: Generating resume summary---")
    jd_text = state["job_description_text"]
    structured_resume = state["master_resume_structured"]
    
    # Use full resume text for broader context
    resume_context = structured_resume['full_text']

    prompt = f"""
    You are an expert resume writer. Synthesize the provided job description and the candidate's full resume to write a concise, professional summary (2-3 sentences), write it in first person.
    This summary must be tailored specifically to the job, highlighting the most relevant skills and experiences.
    Start with a powerful statement about the candidate's profile, also mention the year of study and the degree. **You must wrap the year of study in double asterisks (e.g., `**third-year**`) and nothing else.**

    JOB DESCRIPTION:
    {jd_text}

    CANDIDATE'S FULL RESUME:
    {resume_context}
    """ 
    structured_llm = llm.with_structured_output(ResumeSection)
    response = invoke_llm_with_rate_limiting(structured_llm, prompt)
    
    return {"generated_resume_summary": response.rewritten_text} 

def select_projects_ordered(state: "GraphState") -> Dict[str, Any]:
    """
    Selects and orders the 4 most relevant projects from the master resume using the RAG pipeline.
    """
    print("---AGENT: Selecting and ordering relevant projects---")
    jd_text = state["job_description_text"]
    project_retriever = state["rag_retrievers"]["projects"]

    # Retrieve relevant project documents from the vector store
    retrieved_docs = project_retriever

    prompt = f"""
    You are a senior technical recruiter building a candidate's resume for a specific job.
    Your task is to select and order the top 4 most relevant projects from the candidate's master list that best match the job description, from most relevant to least.

    JOB DESCRIPTION:
    {jd_text}

    CANDIDATE'S PROJECTS:
    {retrieved_docs}

    Based on the job description, analyze the candidate's projects. Your choices should maximize keyword overlap and demonstrate the most complex and applicable skills.
    Return ONLY the titles of the projects you have selected, ordered from most to least relevant.
    """

    structured_llm = llm.with_structured_output(SelectedProjects)
    response = invoke_llm_with_rate_limiting(structured_llm, prompt) 

    return {"selected_project_titles": response.project_titles} 

def adjust_projects_for_length(state: "GraphState") -> Dict[str, Any]:
    print("---AGENT: Adjusting projects for length---")
    jd_text = state["job_description_text"]
    summary = state["generated_resume_summary"]
    selected_titles = state["selected_project_titles"]  # Assume top 5
    all_projects = state["master_resume_structured"]["projects"]

    # Extract original descriptions for selected
    projects = {title: next(p['description'] for p in all_projects if p['title'] == title) for title in selected_titles[:4]}

    lines = calculate_resume_lines(summary, projects)
    max_lines = 24
    too_short_threshold = max_lines - 5
    way_too_long_threshold = max_lines + 8  
    slightly_too_long_threshold = max_lines 

    adjusted_titles = selected_titles[:4] 
    adjusted_projects = projects.copy()

    if lines < too_short_threshold:
        if len(selected_titles) > len(adjusted_titles):
            next_title = selected_titles[len(adjusted_titles)]
            adjusted_titles.append(next_title)
            adjusted_projects[next_title] = next(p['description'] for p in all_projects if p['title'] == next_title)
            print(f"  - Added project: {next_title}")

    while lines > way_too_long_threshold and len(adjusted_titles) > 3:
        # Remove least important (last in ordered list)
        removed_title = adjusted_titles.pop()
        del adjusted_projects[removed_title]
        print(f"  - Removed project: {removed_title}")
        lines = calculate_resume_lines(summary, adjusted_projects)

    # Iterative shortening if slightly too long
    iterations = 0 
    max_iterations = 8
    # Create a new LLM instance with a lower temperature for shortening
    llm_shorten_temp = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite-preview-06-17",
        temperature=0.1,  # Low temperature for precise shortening
        model_kwargs={"response_format": {"type": "json_object"}}, 
    )
    llm_shorten = llm_shorten_temp.with_structured_output(ShortenedProject)
    print(f"  - Initial lines: {lines}, way_too_long_threshold: {way_too_long_threshold}, slightly_too_long_threshold: {slightly_too_long_threshold}, max_iterations: {max_iterations}, iterations: {iterations}")
    initial_lines_too_long = lines - max_lines # Capture initial "too long by"
    while slightly_too_long_threshold + 1 < lines and iterations < max_iterations:
        # Find longest project
        longest_title = max(adjusted_projects, key=lambda t: len(adjusted_projects[t]))
        original_desc = adjusted_projects[longest_title] 
        print(f"too long: {lines-max_lines}")
        prompt = f"""
        Shorten this project description slightly while keeping all information, min 3 bullets: first overview (what, why, how), second details, last 'Technologies used:'.
        Shorten long lines, combine if needed, do not invent facts.
        always use Using the Action Verb–Duty–Result formula (other than the last bullet)
        Each sentence, except the 'Technologies used:' line, must be on its own new line, and approximately 1 line in a letter-sized page. Do not include actual bullet point characters, just newlines.
        in the last iteration the entire resume was {initial_lines_too_long} lines too long, right now the entire resume is {lines-max_lines} lines too long. this is just 1 project, if the resume is too long (ex. greater than 1.5 lines) remove line/s from this project. do not remove the 'Technologies used:' line. 
        always output each sentence on its own line. each sentence should be approximately 1 line in a letter-sized page. each sentence should be treated as a bullet point.     
        always output each sentence on its own line

        ORIGINAL:
        {original_desc}

        JOB DESCRIPTION for context: 
        {jd_text}
        """
        initial_lines_too_long = lines - max_lines
        
        try:
            response = invoke_llm_with_rate_limiting(llm_shorten, prompt)
            
            # Check if response is valid
            if response is None or not hasattr(response, 'shortened_description') or response.shortened_description is None:
                print(f"  - LLM failed to return valid response for {longest_title}, keeping original description")
                # If LLM fails, we can either keep original or try a simpler approach
                # For now, let's just trim some characters from the original
                original_lines = original_desc.split('\n')
                if len(original_lines) > 3:
                    # Remove one line from the middle (not first or last)
                    original_lines.pop(-2)  # Remove second to last line
                adjusted_projects[longest_title] = '\n'.join(original_lines)
                continue
            
            # Post-process to ensure each sentence is on a new line
            shortened_text = response.shortened_description.strip()
            
            # Split into sentences and clean up
            # Split on periods followed by space and capital letter, or period at end of string
            sentences = re.split(r'\.(?=\s+[A-Z]|$)', shortened_text)
            
            # Clean up each sentence and add period back if needed
            processed_sentences = []
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence:  # Skip empty sentences
                    # Add period back if it doesn't end with punctuation
                    if not sentence.endswith(('.', ':', '!')):
                        sentence += '.'
                    processed_sentences.append(sentence)
            
            # Join with newlines to ensure each sentence is on its own line
            adjusted_projects[longest_title] = '\n'.join(processed_sentences)
            
            print(f"  - Shortened project: {longest_title}")
            print(f"  - Shortened description: {adjusted_projects[longest_title]}")
            
        except Exception as e:
            print(f"  - Error shortening project {longest_title}: {e}")
            print(f"  - Keeping original description")
            # Fallback: keep the original description if shortening fails
            adjusted_projects[longest_title] = original_desc
            continue
        lines = calculate_resume_lines(summary, adjusted_projects) 
        print(f"  - Shortened lines: {lines}")
        iterations += 1
        
    return {"selected_project_titles": adjusted_titles, "generated_resume_projects": adjusted_projects}

def optimize_projects(state: "GraphState") -> Dict[str, Any]:
    print("---AGENT: Optimizing projects with keyword bolding---")
    jd_text = state["job_description_text"]
    projects_to_optimize = state["generated_resume_projects"] # Changed from adjusted_projects
    optimized = {}

    for title, desc in projects_to_optimize.items(): 
        prompt = f""" 
        Optimize this project description by bolding relevant keywords from the job description.
        Wrap keywords in **keyword**, bold each unique keyword only once in the most impactful location.
        Do not change any text otherwise. 

        JOB DESCRIPTION: 
        {jd_text}

        PROJECT DESCRIPTION:
        {desc} 
        """
        structured_llm = llm.with_structured_output(OptimizedProject)
        response = invoke_llm_with_rate_limiting(structured_llm, prompt)
        optimized[title] = response.optimized_description

    return {"optimized_projects": optimized}

def assemble_formatted_resume(state: "GraphState") -> Dict[str, Any]:
    print("---AGENT: Assembling formatted resume---")
    structured_resume = state["master_resume_structured"]
    summary = state["generated_resume_summary"]
    projects = state["optimized_projects"] # This is correct, as optimize_projects now returns 'optimized_projects'

    full_text = f"CONTACT\n{structured_resume.get('contact_info', '')}\n\n"
    full_text += f"SUMMARY\n{summary}\n\n"
    full_text += f"SKILLS\n{structured_resume.get('skills', '')}\n\n"
    full_text += f"EDUCATION\n{structured_resume.get('education', '')}\n\n"
    full_text += "PROJECTS\n"
    for title, desc in projects.items():
        full_text += f"{title}\n{desc}\n\n"
    
    # Final length check
    final_lines = calculate_resume_lines(summary, projects)
    print(f"  - Final resume lines: {final_lines}")

    return {"generated_resume_full_text": full_text.strip(), "resume_line_count": final_lines}

def calculate_resume_lines(summary: str, projects: Dict[str, str]) -> int:

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    style = styles['Normal']
    style.fontName = 'Times-Roman'
    style.fontSize = 10.5
    style.leading = 10.5 * 1.09  # ≈11.445 pt
    style.spaceAfter = 0
    style.spaceBefore = 0

    bullet_style = ParagraphStyle('Bullet', parent=style)
    bullet_style.leftIndent = 36  # 1.27 cm ≈36 pt
    bullet_style.firstLineIndent = -17.85  # Hanging 0.63 cm ≈ -17.85 pt

    flowables = []

    # Add summary (normal style)
    flowables.append(Paragraph('SUMMARY', style))
    for line in summary.split('\n'):
        flowables.append(Paragraph(line, style))

    # Add projects
    flowables.append(Paragraph('PROJECTS', style))
    for title, desc in projects.items():
        flowables.append(Paragraph(title, style))  # Title normal
        bullet_lines = [line.strip() for line in desc.split('\n') if line.strip()]
        for line in bullet_lines:
            flowables.append(Paragraph(line, bullet_style, bulletText='• '))

    total_height = 0
    for flowable in flowables:
        w, h = flowable.wrap(doc.width, 1000000)  # Large height to allow full wrap
        total_height += h

    approx_lines = int(total_height / style.leading)  # Remove + len(flowables) for accuracy
    print(f"  - Approximated lines: {approx_lines}")
    return approx_lines  