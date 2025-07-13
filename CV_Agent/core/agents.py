import os
from dotenv import load_dotenv
from typing import TYPE_CHECKING, Any, Dict, List
import time
from collections import deque

from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI

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
# These models enforce a specific JSON schema for the LLM's responses,
# improving reliability and preventing parsing errors.


class SelectedProjects(BaseModel):
    """A Pydantic model for the list of selected project titles."""
    project_titles: List[str] = Field(
        description="A list of 2-4 selected project titles from the master resume."
    )


class ResumeSection(BaseModel):
    """A Pydantic model for any rewritten resume section."""
    rewritten_text: str = Field(
        description="The rewritten text for a resume section (e.g., summary or project description)."
    )


class CoverLetterSections(BaseModel):
    """A Pydantic model for the cover letter's introduction and conclusion."""
    introduction: str = Field(description="The generated introduction for the cover letter.")
    conclusion: str = Field(description="The generated conclusion for the cover letter.")


class CoverLetterBody(BaseModel):
    """A Pydantic model for the body of the cover letter."""
    body_paragraphs: str = Field(
        description="The generated body paragraphs for the cover letter, as a single block of text."
    )


# --- LLM Initialization ---
# Initialize the Gemini model with a structured output instruction.
# A lower temperature is used to reduce randomness for these specific tasks.
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.3,
    # This is a critical setting for ensuring the LLM returns valid JSON
    model_kwargs={"response_format": {"type": "json_object"}},
)


# --- Agent Functions ---
# Each function represents a node in the LangGraph, performing one specific task.


def select_projects(state: "GraphState") -> Dict[str, Any]:
    """
    Selects the most relevant projects from the master resume using the RAG pipeline.
    """
    print("---AGENT: Selecting relevant projects---")
    jd_text = state["job_description_text"]
    project_retriever = state["rag_retrievers"]["projects"]

    # Retrieve relevant project documents from the vector store
    retrieved_docs = project_retriever
    # project_context = "\n\n---\n\n".join([doc.page_content for doc in retrieved_docs])

    prompt = f"""
    You are a senior technical recruiter building a candidate's resume for a specific job.
    Your task is to select the 2 to 4 most relevant projects from the candidate's master list that best match the job description.

    JOB DESCRIPTION:
    {jd_text}

    CANDIDATE'S PROJECTS:
    {retrieved_docs}

    Based on the job description, analyze the candidate's projects. Your choices should maximize keyword overlap and demonstrate the most complex and applicable skills.
    Return ONLY the titles of the projects you have selected.
    """

    structured_llm = llm.with_structured_output(SelectedProjects)
    response = invoke_llm_with_rate_limiting(structured_llm, prompt)

    return {"selected_project_titles": response.project_titles}


def generate_summary(state: "GraphState") -> Dict[str, Any]:
    """Generates a tailored professional summary for the resume."""
    print("---AGENT: Generating resume summary---")
    jd_text = state["job_description_text"]
    structured_resume = state["master_resume_structured"]
    
    # Use full resume text for broader context
    resume_context = structured_resume['full_text']

    prompt = f"""
    You are an expert resume writer. Synthesize the provided job description and the candidate's full resume to write a concise, professional summary (3-4 sentences), write it in first person.
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


def rewrite_projects(state: "GraphState") -> Dict[str, Any]:
    """
    Rewrites the bullet points for each selected project to align with the job description.
    This agent loops internally to process each selected project.
    """
    print("---AGENT: Rewriting selected project descriptions---")
    jd_text = state["job_description_text"]
    selected_titles = state["selected_project_titles"]
    all_projects = state["master_resume_structured"]["projects"]
    rewritten_projects = {}

    for title in selected_titles:
        # Find the original project data
        original_project = next((p for p in all_projects if p["title"] == title), None)
        if not original_project:
            continue

        print(f"  - Rewriting project: {title}")
        prompt = f"""
            You are a highly skilled technical resume writer. Using the Action Verb–Duty–Result formula, transform the original project description for "{title}" into concise, impactful sentences. Follow these rules exactly:

            1. Output each point as a standalone sentence on its own line no matter what, with no bullet characters or extra formatting.
            2. The FIRST sentence must summarize the project's purpose, scope, and key impact.
            3. For all sentences EXCEPT the final "Technologies used" line:
                - Identify keywords from the TARGET JOB DESCRIPTION that are relevant to the sentence.
                - Wrap those keywords in double asterisks (`**keyword**`) for bolding.
                - To avoid over-bolding, **do not bold the same keyword more than once** in this section. Choose its most impactful location.
            4. The FINAL sentence must start with "Technologies used:", followed by a list of technologies. You may bold any technologies that appear in the job description.
            5. Do NOT invent or assume any facts; use only the information provided.
            6. only return the rewritten project description, no other text.

            TARGET JOB DESCRIPTION:
            {jd_text}

            ORIGINAL PROJECT DESCRIPTION for "{title}":
            {original_project['description']}
        """
        # print(prompt)
        print(original_project['description'])
        structured_llm = llm.with_structured_output(ResumeSection)
        response = invoke_llm_with_rate_limiting(structured_llm, prompt)
        print(response.rewritten_text)
        rewritten_projects[title] = response.rewritten_text

    return {"generated_resume_projects": rewritten_projects} 

# --- Placeholder agents for Cover Letter (to be fully implemented later) --- 

def generate_cl_intro_conclusion(state: "GraphState") -> Dict[str, Any]:
    """Generates the introduction and conclusion for the cover letter."""
    print("---AGENT: Generating cover letter intro & conclusion---")
    jd_text = state["job_description_text"]
    structured_resume = state["master_resume_structured"]
    
    # Use full resume context for personalization
    resume_context = structured_resume['full_text']
    
    prompt = f"""
    You are an expert cover letter writer. Based on the job description and candidate's resume, 
    generate a compelling introduction and conclusion for a cover letter.

    The introduction should:
    1. First sentence: Open with a creative hook draws the reader in with a brief narrative that shows genuine enthusiasm for the role and company—demonstrate why this opportunity speaks to you personally, not just that it does.
    2. Address the specific role and company (extract from job description)
    3. highlight your top 1–2 strengths or experiences that align with the role, weaving in language from the job description so it feels tailored and sincere.
    4. Create an engaging opening that highlights the candidate's most relevant strengths
    5. Be 3-4 sentences maximum

    The conclusion should:
    1. Reiterate interest and summarize key value proposition
    2. Include a call to action
    3. Be professional and confident
    4. Be 3-4 sentences maximum

    Do not use an em dash in either paragraph.

    JOB DESCRIPTION:
    {jd_text}

    CANDIDATE'S RESUME:
    {resume_context}
    """
    
    structured_llm = llm.with_structured_output(CoverLetterSections)
    response = invoke_llm_with_rate_limiting(structured_llm, prompt)
    
    return {
        "generated_cl_intro": response.introduction,
        "generated_cl_conclusion": response.conclusion
    }

def generate_cl_body(state: "GraphState") -> Dict[str, Any]:
    """
    Generates the body paragraphs for the cover letter, using the pre-generated
    introduction and conclusion as context.
    """
    print("---AGENT: Generating cover letter body---")
    jd_text = state["job_description_text"]
    structured_resume = state["master_resume_structured"]
    selected_projects = state["generated_resume_projects"]
    intro_text = state["generated_cl_intro"]
    conclusion_text = state["generated_cl_conclusion"]
    
    # Use both full resume and selected projects for context
    resume_context = structured_resume['full_text']
    projects_context = "\n".join([f"{title}: {desc}" for title, desc in selected_projects.items()])
    
    prompt = f"""
    You are an expert cover letter writer. You have already been provided with an introduction and conclusion.
    Your task is to generate ONLY the body paragraphs (3-4 paragraphs) that will fit between them. The body should logically connect the opening to the closing.

    INTRODUCTION (for context):
    {intro_text}

    CONCLUSION (for context):
    {conclusion_text}

    Now, create the body paragraphs. Focus on:
    1. Specific achievements and projects from the resume that align with job requirements.
    2. Connecting the candidate's technical skills to the needs mentioned in the job description.
    3. Explaining why the candidate is specifically interested in this role and company.
    4. Quantifying impact and results where possible.
    5. The body paragraphs should flow well from one to the next, including the transition from the introduction and to the conclusion.
    6. If the candidate doesnt have some of the skills mentioned in the job description, make connections to other skills/experiences, or explain that they are eager to learn.
    7. Dont be too technical, repetitive, or boring. explain what was done, why it was done, and what i learned, dont be too stuck up on the technical details.
    8. be creative and think outside the box, engaging the reader.  

    Each paragraph should be 3-5 sentences. Make it personal, specific, and compelling. Do not have all the paragraphs be the same length.
    Do not use an em dash in any paragraph.
    Return ONLY the body paragraphs as a single text block, with paragraph breaks where appropriate.

    JOB DESCRIPTION (for reference):
    {jd_text}

    CANDIDATE'S FULL RESUME (for reference):
    {resume_context}

    SELECTED PROJECTS (for reference):
    {projects_context}
    """
    
    structured_llm = llm.with_structured_output(CoverLetterBody)
    response = invoke_llm_with_rate_limiting(structured_llm, prompt)
    
    return {"generated_cl_body": response.body_paragraphs}

def regenerate_cl_with_feedback(state: "GraphState") -> Dict[str, Any]:
    """Regenerates cover letter sections based on user feedback."""
    print("---AGENT: Regenerating cover letter with feedback---")
    jd_text = state["job_description_text"]
    structured_resume = state["master_resume_structured"]
    feedback_history = state["cl_feedback_history"]
    current_intro = state["generated_cl_intro"]
    current_body = state["generated_cl_body"]
    current_conclusion = state["generated_cl_conclusion"]
    
    # Get the latest feedback
    latest_feedback = feedback_history[-1] if feedback_history else ""
    
    prompt = f"""
    You are an expert cover letter writer. The user has provided feedback on the current cover letter.
    Please regenerate the cover letter sections incorporating their feedback while maintaining professionalism.

    CURRENT COVER LETTER:
    Introduction: {current_intro}
    
    Body: {current_body}
    
    Conclusion: {current_conclusion}

    USER FEEDBACK: {latest_feedback}

    JOB DESCRIPTION:
    {jd_text}

    CANDIDATE'S RESUME:
    {structured_resume['full_text']}

    Please regenerate ALL three sections (intro, body, conclusion) incorporating the feedback.
    """
    
    # Generate new intro and conclusion
    intro_conclusion_llm = llm.with_structured_output(CoverLetterSections)
    intro_conclusion_response = invoke_llm_with_rate_limiting(intro_conclusion_llm, prompt + "\n\nGenerate the introduction and conclusion:")
    
    # Generate new body
    body_llm = llm.with_structured_output(CoverLetterBody)
    body_response = invoke_llm_with_rate_limiting(body_llm, prompt + "\n\nGenerate the body paragraphs:")
    
    return {
        "generated_cl_intro": intro_conclusion_response.introduction,
        "generated_cl_conclusion": intro_conclusion_response.conclusion,
        "generated_cl_body": body_response.body_paragraphs,
        "user_action": ""  # Clear the user action to prevent infinite loops
    } 


# --- Resume Length Optimization Agents & Helpers ---

import math

# --- Constants for Length Calculation ---
# These can be adjusted based on the desired output format
LINE_WIDTH_CHARS = 88  # Assumes a standard 8.5x11 page with 1-inch margins and 10pt font
PAGE_LINE_LIMIT = 58   # Standard lines per page for single-spaced text

def _estimate_document_lines(text: str) -> int:
    """Estimates the number of lines a block of text will occupy."""
    if not text:
        return 0
    lines = text.split('\n')
    total_lines = 0
    for line in lines:
        # Calculate how many lines this specific line will wrap into
        # Add 1 for the line itself, then extra for wraps
        if len(line) == 0:
            total_lines += 1 # An empty line still takes up one line
        else:
            total_lines += math.ceil(len(line) / LINE_WIDTH_CHARS)
    return total_lines

def _assemble_resume_text(state: "GraphState") -> str:
    """Assembles the generated resume parts into a single string for length checking."""
    structured_resume = state["master_resume_structured"]
    summary = state["generated_resume_summary"]
    projects = state["generated_resume_projects"]

    # This is a simplified assembly. A real implementation would use the master
    # resume as a template and inject the generated content.
    full_text = f"CONTACT\n{structured_resume.get('contact_info', '')}\n\n"
    full_text += f"SUMMARY\n{summary}\n\n"
    
    # Add skills and education from master resume
    full_text += f"SKILLS\n{structured_resume.get('skills', '')}\n\n"
    full_text += f"EDUCATION\n{structured_resume.get('education', '')}\n\n"

    full_text += "PROJECTS\n"
    for title in state["selected_project_titles"]:
        desc = projects.get(title)
        if desc:
            full_text += f"{title}\n{desc}\n\n"
        
    return full_text.strip()


def assemble_and_check_length(state: "GraphState") -> Dict[str, Any]:
    """Assembles the resume and checks if it exceeds the one-page limit."""
    print("---AGENT: Assembling resume and checking length---")
    
    # Ensure previous fix choice doesn't persist
    if "resume_fix_choice" in state:
        state["resume_fix_choice"] = ""

    full_text = _assemble_resume_text(state)
    line_count = _estimate_document_lines(full_text)
    is_too_long = line_count > PAGE_LINE_LIMIT
    
    if is_too_long:
        print(f"  - Resume is too long: {line_count} lines (limit: {PAGE_LINE_LIMIT}).")
    else:
        print(f"  - Resume length is OK: {line_count} lines (limit: {PAGE_LINE_LIMIT}).")
        
    return {
        "generated_resume_full_text": full_text,
        "resume_line_count": line_count,
        "resume_is_too_long": is_too_long,
    }

def shorten_resume(state: "GraphState") -> Dict[str, Any]:
    """
    Attempts to shorten the resume using a tiered strategy based on how much
    it exceeds the page limit.
    """
    print("---AGENT: Shortening resume---")
    line_count = state["resume_line_count"]
    lines_over = line_count - PAGE_LINE_LIMIT
    projects = state["generated_resume_projects"].copy()
    titles = state["selected_project_titles"].copy()
    
    # Tier 1: Remove a whole project if significantly over
    if lines_over > 10 and len(titles) > 2:
        # For simplicity, remove the last project. A better implementation
        # would re-rank projects for relevance and remove the least relevant.
        removed_title = titles.pop()
        del projects[removed_title]
        print(f"  - Resume significantly long. Removing project: {removed_title}")
        return {"selected_project_titles": titles, "generated_resume_projects": projects}

    # Tier 3: Remove the least valuable bullet point from the longest project
    else:
        # Find the project with the longest description to target for shortening
        if not projects:
            return {} # No projects to shorten
            
        longest_project_title = max(projects, key=lambda p: len(projects.get(p, '')))
        project_text = projects[longest_project_title]
        
        prompt = f"""
        You are a ruthless resume editor. Your goal is to make a document fit on one page.
        Analyze the following project description and remove the single, least impactful sentence to save space. Never remove the "Technologies used:" line.
        Return ONLY the rewritten project description with that one sentence removed. Do not add, change, or rephrase anything else, including the double asterisks (`**keyword**`) for bolding. Output each point as a standalone sentence on its own line, this is important.

        ORIGINAL PROJECT DESCRIPTION:
        {project_text}
        """
        structured_llm = llm.with_structured_output(ResumeSection)
        response = invoke_llm_with_rate_limiting(structured_llm, prompt)
        
        print(f"  - Shortening project by removing one line from: {longest_project_title}")
        projects[longest_project_title] = response.rewritten_text
        return {"generated_resume_projects": projects} 

    return {} # Should not be reached in normal flow 