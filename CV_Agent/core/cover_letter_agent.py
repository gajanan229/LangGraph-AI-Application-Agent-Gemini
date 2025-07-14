import os
import json
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

class CoverLetterSections(BaseModel):
    """A Pydantic model for the cover letter's introduction and conclusion."""
    introduction: str = Field(description="The generated introduction for the cover letter.")
    conclusion: str = Field(description="The generated conclusion for the cover letter.")

# --- LLM Initialization ---
# Deepseek for intro and conclusion 
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
deepseek = ChatDeepSeek(model="deepseek-reasoner", temperature=1, api_key=DEEPSEEK_API_KEY, max_retries=2)

# Gemini for body (from resume_agent.py)
gemini = ChatGoogleGenerativeAI( 
    model="gemini-2.5-flash-lite-preview-06-17",
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
                1. Start with a creative, thematic hook that connects to the company's mission or values in an original way 
                2. Use metaphors or creative framings that feel natural and smooth, not forced or overly direct
                3. Weave in specific technical projects naturally without being too explicit about connections (avoid phrases like "much like", "mirroring", "similar to")
                4. Include enough personal details and technical experience to give substance
                5. Show personality and genuine enthusiasm through storytelling, not generic excitement phrases
                6. Be 4-5 sentences maximum with engaging, flowing language
                7. Do not use em dashes, hyphens for clauses, or corporate buzzwords like "synergy", "leverage", "utilize"
                8. Use non-technical language unless the technical term appears in the job description - if you must use technical terms, add brief descriptive context
                9. Avoid being too direct or sales-y in the opening - draw them in first, then connect

                Technical language guidelines:
                - Only use technical terms that appear in the job description
                - For other technical terms, use descriptive phrases (e.g., "AI agent framework" instead of "LangChain")
                - Keep explanations brief and accessible to non-technical readers

                Voice and tone:
                - Natural, smooth connections rather than forced parallels
                - Genuine enthusiasm through storytelling, not generic excitement
                - Professional but personable, avoiding overly poetic or preachy language
                - Let connections emerge organically rather than stating them explicitly
                - Creative but authentic voice that reflects genuine interest

                Avoid these overused openings:
                - "In a world where..."
                - "Amidst the..."
                - "As a [student/developer]..."
                - "I was excited to discover..."
                - "Imagine if..."
                - "In today's digital landscape..."

                Avoid these forced connection patterns:
                - "much like [company]..."
                - "mirroring your..."
                - "similar to how [company]..."
                - Em dashes for clauses
                - Overly direct comparisons
                - Corporate buzzwords (synergy, leverage, utilize, streamline)

                Focus on:
                - Finding unique angles related to the company's industry/mission/values
                - Original metaphors or perspectives that haven't been overused
                - Specific technical details woven naturally into the narrative
                - Personality that makes the reader want to learn more about you

                JOB DESCRIPTION: {jd_text}

                CANDIDATE'S RESUME: {resume_context}

                Output in json format with a single key 'introduction' containing the generated text.
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
                You are an expert cover letter writer. Generate a compelling conclusion for a cover letter that maintains the creative voice and theme established in the introduction.

                The conclusion should:
                1. Echo the theme/metaphor from the introduction subtly and naturally, not through explicit "just as" or "much like" constructions
                2. Show confidence and readiness to contribute, not just eagerness to learn
                3. Position the interview as a natural next step using invitational language, not presumptuous or demanding tone
                4. Reference the role naturally without over-specifying location details or repeating job title verbatim
                5. Be 3-4 sentences maximum for impact and flow
                6. Maintain the same creative, thoughtful voice as the introduction
                7. Do not use em dashes, hyphens for clauses, or corporate buzzwords

                Voice and tone:
                - Same personality and creativity as the introduction
                - Confident but respectful, not presumptuous or demanding
                - Natural flow that feels like a logical conclusion
                - Professional but personable
                - Invitational rather than assumptive about next steps

                Technical language guidelines:
                - Only use technical terms that appear in the job description
                - For other technical concepts, use descriptive phrases accessible to non-technical readers
                - Keep explanations brief and natural

                Avoid these forced callback patterns:
                - "Just as [company/intro theme]..."
                - "Much like..."
                - "Similar to how..."
                - "In the same spirit of..."
                - Direct equation statements like "aligns with your vision"

                Avoid these presumptuous phrases:
                - "Let's explore..."
                - "I'm confident that a conversation...is a natural next step"
                - "I believe discussing...is a natural next step"
                - Over-specific location references 

                Interview reference guidelines:
                - Use invitational language: "I would welcome the opportunity to discuss..."
                - Make it feel natural without being demanding
                - Reference the mission/impact rather than specific logistics
                - Be confident but not presumptuous

                Focus on:
                - Organic theme integration that feels natural
                - Confident readiness to contribute
                - Respectful invitation to continue the conversation
                - Natural flow that doesn't over-specify details

                INTRODUCTION: {intro_text}
                JOB DESCRIPTION: {jd_text}
                CANDIDATE'S RESUME: {resume_context}

                Output in json format with a single key 'conclusion' containing the generated text.
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

    Output in json format with keys 'introduction' and 'conclusion'.
    """
    
    structured_llm = deepseek.with_structured_output(CoverLetterSections, method="json_mode")
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
        You are an expert cover letter writer. Generate 3 body paragraphs that bridge the introduction and conclusion while maintaining the established creative voice and weaving together technical projects, work experience, and personal qualities.

        INTRODUCTION (for context and theme continuity):
        {intro_text}

        CONCLUSION (for context and flow):
        {conclusion_text}

        The body paragraphs should:

        **Content Integration:**
        1. Weave together technical projects, work experience, and personal qualities into a cohesive narrative
        2. Show who you are as a person, not just what you've built
        3. Include collaborative experiences, leadership moments, or growth stories from work/academic settings
        4. Connect your experiences to the company's mission through your actions and values, not explicit statements
        5. Demonstrate problem-solving approach and working style through specific examples

        **Voice and Storytelling:**
        1. Maintain the creative, engaging voice from the introduction while being substantive
        2. Use varied sentence structures and narrative techniques to keep the reader engaged
        3. Show personality through anecdotes, insights, and reflections
        4. Create smooth, natural transitions that advance your story
        5. Subtly carry forward thematic elements from the introduction

        **Balance Technical and Personal:**
        - Technical projects should be presented as problem-solving stories, not feature lists
        - Include moments of collaboration, learning from others, or teaching/mentoring
        - Show your working style and approach to challenges
        - Demonstrate growth, adaptability, and curiosity through experiences
        - Reference relevant work experience, internships, or team projects

        **Technical Language Guidelines:**
        - Only use technical terms that appear in the job description
        - For other technical concepts, use descriptive phrases accessible to non-technical readers
        - Focus on the "why" and "how" of your work, not just the "what"
        - Explain impact and learning, not just implementation details

        **Avoid These Patterns:**
        - Mechanical project descriptions: "I built X, it did Y, I learned Z"
        - Repetitive paragraph structures
        - Generic transitions: "Most recently...", "Building on this..."
        - Bland corporate language: "I'm eager to apply", "aligns with mission"
        - Pure technical focus without human elements
        - Em dashes or hyphens for clauses

        **Paragraph Approach:**
        - **First paragraph**: Your strongest technical project woven with personal insights or collaborative elements
        - **Second paragraph**: Complementary experience (work, leadership, different type of project) that shows another dimension
        - **Third paragraph (if needed)**: Bridge technical skills with personal qualities or address any gaps while showing growth

        **Engagement Techniques:**
        - Use specific moments and concrete details that paint a picture
        - Show your thought process and problem-solving approach
        - Include insights about your working style or what drives you
        - Reference interactions with teammates, users, or stakeholders
        - Demonstrate curiosity and learning mindset through experiences

        **Flow and Transitions:**
        - Each paragraph should build on the previous one naturally
        - Vary paragraph lengths and structures for rhythm
        - Connect experiences through themes or insights, not just chronology
        - Lead naturally into your conclusion's confident tone

        Remember: The body should reveal who you are as a person and teammate, not just what you've built. Show your personality, working style, and values through your experiences.

        JOB DESCRIPTION:
        {jd_text}

        CANDIDATE'S RESUME:
        {resume_context}

        SELECTED PROJECTS:
        {projects_context}

        Output only the body paragraphs as a single text block with appropriate paragraph breaks.
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