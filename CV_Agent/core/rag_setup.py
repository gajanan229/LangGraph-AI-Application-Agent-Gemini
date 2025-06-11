import os
from dotenv import load_dotenv
from typing import Any, Dict

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()


def setup_rag_pipeline(structured_master_resume: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sets up the RAG pipeline by creating a vector store for resume projects.

    This function focuses exclusively on creating a retriever for the projects
    listed in the master resume. The job description is handled separately.

    Args:
        structured_master_resume: The structured dictionary of the master resume,
                                  which must contain a 'projects' key.

    Returns:
        A dictionary containing the initialized project retriever.
    """
    # Ensure there's an API key before proceeding
    if not os.getenv("GOOGLE_API_KEY"):
        raise ValueError(
            "GOOGLE_API_KEY environment variable not found. "
            "Please ensure it is set in the .env file."
        )

    # Initialize the embedding model
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    # --- Project Retriever Setup ---
    projects = structured_master_resume.get("projects", [])
    if not projects:
        # Return an empty retriever if there are no projects to process
        return {"projects": None}
    
    # Create LangChain Document objects for each project
    project_docs = []
    for project in projects:
        # The page_content should be a comprehensive string for embedding
        page_content = f"Project Title: {project['title']}\n{project['description']}"
        # The metadata can store the original data for easy access later
        metadata = {"title": project["title"], "original_text": project["description"]}
        doc = Document(page_content=page_content, metadata=metadata)
        project_docs.append(doc)

    # Create a FAISS vector store from the project documents
    project_vector_store = FAISS.from_documents(project_docs, embeddings)

    # Create a retriever from the vector store
    project_retriever = project_vector_store.as_retriever(search_kwargs={"k": 5})

    return {"projects": projects} 