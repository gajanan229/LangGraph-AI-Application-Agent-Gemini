import os
from typing import TYPE_CHECKING, Any, Dict, List

from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI

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
    retrieved_docs = project_retriever.invoke(jd_text)
    project_context = "\n\n---\n\n".join([doc.page_content for doc in retrieved_docs])

    prompt = f"""
    You are a senior technical recruiter building a candidate's resume for a specific job.
    Your task is to select the 2 to 4 most relevant projects from the candidate's master list that best match the job description.

    JOB DESCRIPTION:
    {jd_text}

    CANDIDATE'S PROJECTS:
    {project_context}

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
        You are a technical writer tasked with refining a resume project description.
        Given the original bullet points for the project '{title}' and the target job description, rewrite the bullet points.

        Your goals are:
        1. Integrate relevant keywords from the job description naturally.
        2. Quantify achievements where possible (e.g., 'improved performance by 20%').
        3. Use strong action verbs.
        4. Do NOT invent any facts; only rephrase and enhance the information provided.
        5. Return the rewritten bullet points as a single block of text.

        TARGET JOB DESCRIPTION:
        {jd_text}

        ORIGINAL PROJECT DESCRIPTION for '{title}':
        {original_project['description']}
        """
        structured_llm = llm.with_structured_output(ResumeSection)
        response = structured_llm.invoke(prompt)
        rewritten_projects[title] = response.rewritten_text

    return {"generated_resume_projects": rewritten_projects}

# --- Placeholder agents for Cover Letter (to be fully implemented later) ---

def generate_cl_intro_conclusion(state: "GraphState") -> Dict[str, Any]:
    """Generates the introduction and conclusion for the cover letter."""
    print("---AGENT: Generating cover letter intro & conclusion---")
    # This is a placeholder implementation
    return {
        "generated_cl_intro": "This is a placeholder introduction.",
        "generated_cl_conclusion": "This is a placeholder conclusion."
    }

def generate_cl_body(state: "GraphState") -> Dict[str, Any]:
    """Generates the body paragraphs for the cover letter."""
    print("---AGENT: Generating cover letter body---")
    # This is a placeholder implementation
    return {"generated_cl_body": "These are the placeholder body paragraphs."} 