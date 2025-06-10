import os
from dotenv import load_dotenv
from typing import TYPE_CHECKING, Any, Dict, List

from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

if TYPE_CHECKING:
    from .graph import GraphState

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
    response = structured_llm.invoke(prompt)

    return {"selected_project_titles": response.project_titles}


def generate_summary(state: "GraphState") -> Dict[str, Any]:
    """Generates a tailored professional summary for the resume."""
    print("---AGENT: Generating resume summary---")
    jd_text = state["job_description_text"]
    structured_resume = state["master_resume_structured"]
    
    # Use full resume text for broader context
    resume_context = structured_resume['full_text']

    prompt = f"""
    You are an expert resume writer. Synthesize the provided job description and the candidate's full resume to write a concise, professional summary (3-4 sentences).
    This summary must be tailored specifically to the job, highlighting the most relevant skills and experiences.
    Start with a powerful statement about the candidate's profile.

    JOB DESCRIPTION:
    {jd_text}

    CANDIDATE'S FULL RESUME:
    {resume_context}
    """
    structured_llm = llm.with_structured_output(ResumeSection)
    response = structured_llm.invoke(prompt)
    
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

            1. Output each point as a standalone sentence on its own line, with no bullet characters or extra formatting.
            2. The FIRST sentence must summarize the project's purpose, scope, and key impact to give the reader a clear overview.
            3. Any MIDDLE sentences should:
            • Start with a strong action verb,  
            • Describe your duty,  
            • Quantify the result whenever possible,  
            • Weave in relevant keywords from the target job description naturally.
            4. The FINAL sentence must list only the technologies used—exactly as they appear in the original description, in the same order.
            5. Do NOT invent or assume any facts; use only the information provided.

            TARGET JOB DESCRIPTION:
            {jd_text}

            ORIGINAL PROJECT DESCRIPTION for "{title}":
            {original_project['description']}
        """
        # print(prompt)
        structured_llm = llm.with_structured_output(ResumeSection)
        response = structured_llm.invoke(prompt)
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
    response = structured_llm.invoke(prompt)
    
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

    Each paragraph should be 3-5 sentences. Make it personal, specific, and compelling.
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
    response = structured_llm.invoke(prompt)
    
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
    intro_conclusion_response = intro_conclusion_llm.invoke(prompt + "\n\nGenerate the introduction and conclusion:")
    
    # Generate new body
    body_llm = llm.with_structured_output(CoverLetterBody)
    body_response = body_llm.invoke(prompt + "\n\nGenerate the body paragraphs:")
    
    return {
        "generated_cl_intro": intro_conclusion_response.introduction,
        "generated_cl_conclusion": intro_conclusion_response.conclusion,
        "generated_cl_body": body_response.body_paragraphs,
        "user_action": ""  # Clear the user action to prevent infinite loops
    } 