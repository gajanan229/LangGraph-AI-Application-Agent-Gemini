from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, StateGraph

from core import agents

# --- Graph State Definition ---
# TypedDict is used to define the schema of the state object that will be
# passed between nodes in the graph. This provides type-checking and clarity.


class GraphState(TypedDict):
    """
    Represents the state of our application graph.

    Attributes:
        job_description_text: The full text of the target job description.
        master_resume_structured: The parsed and structured master resume.
        rag_retrievers: A dictionary containing the initialized RAG retrievers.
        selected_project_titles: A list of project titles selected by the AI.
        generated_resume_summary: The AI-generated professional summary.
        generated_resume_projects: A dictionary mapping project titles to their
                                   AI-rewritten descriptions.
        # --- Cover Letter Fields ---
        generated_cl_intro: The AI-generated introduction for the cover letter.
        generated_cl_conclusion: The AI-generated conclusion.
        generated_cl_body: The AI-generated body paragraphs.
        cl_feedback_history: A list to store user feedback for regeneration.
        user_action: A string to control conditional flows (e.g., 'REGENERATE').
    """
    job_description_text: str
    master_resume_structured: Dict[str, Any]
    rag_retrievers: Dict[str, Any]
    selected_project_titles: List[str]
    generated_resume_summary: str
    generated_resume_projects: Dict[str, str]
    generated_cl_intro: str
    generated_cl_conclusion: str
    generated_cl_body: str
    cl_feedback_history: List[str]
    user_action: str


def create_application_graph():
    """
    Creates and compiles the LangGraph for the application workflow.
    """
    graph = StateGraph(GraphState)

    # --- Add Nodes to the Graph ---
    # Each node corresponds to a function in agents.py
    graph.add_node("project_selector", agents.select_projects)
    graph.add_node("summary_generator", agents.generate_summary)
    graph.add_node("project_rewriter", agents.rewrite_projects)

    # This node acts as a synchronization point after parallel resume generation
    def resume_complete(state: GraphState):
        print("---STATE: Resume content generation complete.---")
        return {}
    graph.add_node("resume_complete", resume_complete)

    # --- Wire Nodes Together with Edges ---
    # The graph starts with the project selector
    graph.set_entry_point("project_selector")

    # After selecting projects, run summary generation and project rewriting in parallel
    graph.add_edge("project_selector", "summary_generator")
    graph.add_edge("project_selector", "project_rewriter")

    # Once both parallel tasks are complete, they proceed to the sync node
    graph.add_edge("summary_generator", "resume_complete")
    graph.add_edge("project_rewriter", "resume_complete")
    
    # For now, the resume generation process ends here.
    # The cover letter flow will be added later.
    graph.add_edge("resume_complete", END)


    # Compile the graph into a runnable application
    app = graph.compile()
    return app 