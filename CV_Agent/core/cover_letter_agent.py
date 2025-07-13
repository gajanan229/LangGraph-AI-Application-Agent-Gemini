import os
from dotenv import load_dotenv
from typing import TYPE_CHECKING, Any, Dict, List
import time
from collections import deque

from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_deepseek import ChatDeepSeek

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
class CoverLetterIntro(BaseModel):
    """Pydantic model for the cover letter introduction."""
    introduction: str = Field(description="The generated introduction for the cover letter.")

class CoverLetterConclusion(BaseModel):
    """Pydantic model for the cover letter conclusion."""
    conclusion: str = Field(description="The generated conclusion for the cover letter.")

class CoverLetterBody(BaseModel):
    """Pydantic model for the body of the cover letter."""
    body_paragraphs: str = Field(
        description="The generated body paragraphs for the cover letter, as a single block of text."
    )

# --- LLM Initialization ---
# Deepseek for intro and conclusion 
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
deepseek = ChatDeepSeek(model="deepseek-reasoner", temperature=0.3, api_key=DEEPSEEK_API_KEY, max_retries=2)

# Gemini for body (from resume_agent.py)
gemini = ChatGoogleGenerativeAI( 
    model="gemini-2.0-flash",
    temperature=0.3,
    model_kwargs={"response_format": {"type": "json_object"}},
)

# --- Agent Functions ---
def generate_intro(state: "GraphState") -> Dict[str, Any]:
    print("---AGENT: Generating cover letter intro---")
    jd_text = state["job_description_text"]
    structured_resume = state["master_resume_structured"]
    resume_context = structured_resume['full_text']
    
    prompt = f"""
    You are an expert cover letter writer. Generate a compelling introduction for a cover letter based on the job description and candidate's resume.
    The introduction should:
    1. Start with a creative hook that draws the reader in, reflecting company values, my enthusiasm, interest, and commitment.
    2. Avoid common openers like 'I'm excited to apply' or 'imagine'.
    3. Show, not tell, creating a theme and vibe that carries through.
    4. Be 3-4 sentences maximum.
    5. Do not use em dashes.

    JOB DESCRIPTION: {jd_text}
    CANDIDATE'S RESUME: {resume_context}
    """
    
    structured_llm = deepseek.with_structured_output(CoverLetterIntro, method="json_mode")
    response = invoke_llm_with_rate_limiting(structured_llm, prompt)
    return {"generated_cl_intro": response.introduction}

def generate_conclusion(state: "GraphState") -> Dict[str, Any]:
    print("---AGENT: Generating cover letter conclusion---")
    jd_text = state["job_description_text"]
    structured_resume = state["master_resume_structured"]
    intro_text = state["generated_cl_intro"]
    resume_context = structured_resume['full_text']
    
    prompt = f"""
    You are an expert cover letter writer. Generate a compelling conclusion for a cover letter, continuing the theme from the introduction.
    The conclusion should:
    1. Be like a final pitch, professional and creative.
    2. Thank them and nudge for an interview to prove fit, not too direct.
    3. Be 3-4 sentences maximum.
    4. Do not use em dashes.

    INTRODUCTION: {intro_text}
    JOB DESCRIPTION: {jd_text}
    CANDIDATE'S RESUME: {resume_context}
    """
    
    structured_llm = deepseek.with_structured_output(CoverLetterConclusion, method="json_mode")
    response = invoke_llm_with_rate_limiting(structured_llm, prompt)
    return {"generated_cl_conclusion": response.conclusion}

def generate_intro_conclusion(state: "GraphState") -> Dict[str, Any]:
    intro_res = generate_intro(state)
    concl_res = generate_conclusion({**state, **intro_res})
    return {**intro_res, **concl_res}

def edit_intro_conclusion(state: "GraphState") -> Dict[str, Any]:
    print("---AGENT: Editing intro and conclusion with feedback---")
    feedback = state["user_feedback_intro_concl"]
    current_intro = state["generated_cl_intro"]
    current_conclusion = state["generated_cl_conclusion"]
    jd_text = state["job_description_text"]
    resume_context = state["master_resume_structured"]['full_text']
    
    prompt = f"""
    Regenerate intro and conclusion incorporating feedback.
    Feedback: {feedback}
    Current Intro: {current_intro}
    Current Conclusion: {current_conclusion}
    JOB: {jd_text}
    RESUME: {resume_context}
    """
    
    structured_llm = deepseek.with_structured_output(CoverLetterSections, method="json_mode")  # Assume CoverLetterSections is a model with both intro and conclusion
    response = invoke_llm_with_rate_limiting(structured_llm, prompt)
    return {
        "generated_cl_intro": response.introduction,
        "generated_cl_conclusion": response.conclusion
    }

def generate_body(state: "GraphState") -> Dict[str, Any]:
    print("---AGENT: Generating cover letter body---")
    jd_text = state["job_description_text"]
    structured_resume = state["master_resume_structured"]
    selected_projects = state["generated_resume_projects"]
    intro_text = state["generated_cl_intro"]
    conclusion_text = state["generated_cl_conclusion"]
    resume_context = structured_resume['full_text']
    projects_context = "\n".join([f"{title}: {desc}" for title, desc in selected_projects.items()])
    
    prompt = f"""
    Generate body paragraphs continuing theme from intro and leading to conclusion.
    INTRO: {intro_text}
    CONCLUSION: {conclusion_text}
    JOB: {jd_text}
    RESUME: {resume_context}
    PROJECTS: {projects_context}
    """
    
    structured_llm = gemini.with_structured_output(CoverLetterBody)
    response = invoke_llm_with_rate_limiting(structured_llm, prompt)
    return {"generated_cl_body": response.body_paragraphs}

def adjust_body_length(state: "GraphState") -> Dict[str, Any]:
    print("---AGENT: Adjusting body for length---")
    intro = state["generated_cl_intro"]
    conclusion = state["generated_cl_conclusion"]
    body = state["generated_cl_body"]
    lines = calculate_cover_letter_lines(intro + "\n\n" + body + "\n\n" + conclusion)
    
    if lines > 40:
        # Shorten body
        prompt = f"Shorten body to fit under 40 lines. Current: {lines}"
        structured_llm = gemini.with_structured_output(CoverLetterBody)
        response = invoke_llm_with_rate_limiting(structured_llm, prompt)
        return {"generated_cl_body": response.body_paragraphs}
    elif lines < 25:
        # Expand body
        prompt = f"Expand body to at least 25 lines. Current: {lines}. Use context: {state['job_description_text']}"
        structured_llm = gemini.with_structured_output(CoverLetterBody)
        response = invoke_llm_with_rate_limiting(structured_llm, prompt)
        return {"generated_cl_body": response.body_paragraphs}
    return {}

def edit_body(state: "GraphState") -> Dict[str, Any]:
    print("---AGENT: Editing body with feedback---")
    feedback = state["user_feedback_body"]
    current_body = state["generated_cl_body"]
    prompt = f"Regenerate body with feedback: {feedback}. Current: {current_body}"
    structured_llm = gemini.with_structured_output(CoverLetterBody)
    response = invoke_llm_with_rate_limiting(structured_llm, prompt)
    # After edit, re-adjust length
    state["generated_cl_body"] = response.body_paragraphs
    return adjust_body_length(state)

def calculate_cover_letter_lines(text: str) -> int:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=72, rightMargin=72, topMargin=72, bottomMargin=72)
    styles = getSampleStyleSheet()
    style = styles['Normal']
    style.fontName = 'Times-Roman'
    style.fontSize = 11
    style.leading = 11 * 1.2  # 13.2 pt leading
    flowables = [Paragraph(text, style)]
    total_height = 0
    for flowable in flowables:
        w, h = flowable.wrap(doc.width, 1000000)
        total_height += h
    approx_lines = int(total_height / style.leading)
    print(f"  - Approximated lines: {approx_lines}")
    return approx_lines 