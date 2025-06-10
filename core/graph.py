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
    # Resume generation nodes
    graph.add_node("project_selector", agents.select_projects)
    graph.add_node("summary_generator", agents.generate_summary)
    graph.add_node("project_rewriter", agents.rewrite_projects)

    # Resume completion synchronization point
    def resume_complete(state: GraphState):
        print("---STATE: Resume content generation complete.---")
        return {}
    graph.add_node("resume_complete", resume_complete)

    # Cover letter generation nodes
    graph.add_node("cl_intro_conclusion_generator", agents.generate_cl_intro_conclusion)
    graph.add_node("cl_body_generator", agents.generate_cl_body)
    graph.add_node("cl_regenerator", agents.regenerate_cl_with_feedback)

    # Cover letter completion synchronization point
    def cl_complete(state: GraphState):
        print("---STATE: Cover letter generation complete.---")
        return {}
    graph.add_node("cl_complete", cl_complete)

    # Decision node for cover letter regeneration
    def should_regenerate_cl(state: GraphState):
        """Determines if cover letter should be regenerated based on user action."""
        # This function doesn't modify state, just returns empty dict
        return {}
    
    graph.add_node("cl_decision", should_regenerate_cl)
    
    # Helper function for conditional routing
    def cl_decision_router(state: GraphState):
        """Router function that determines the next step based on user action."""
        user_action = state.get("user_action", "")
        if user_action == "REGENERATE_CL":
            return "regenerate"
        else:
            return "complete"

    # --- Wire Nodes Together with Edges ---
    # Resume generation flow
    graph.set_entry_point("project_selector")
    graph.add_edge("project_selector", "summary_generator")
    graph.add_edge("project_selector", "project_rewriter")
    graph.add_edge("summary_generator", "resume_complete")
    graph.add_edge("project_rewriter", "resume_complete")
    
    # After resume completion, start cover letter generation serially.
    # The intro/conclusion are generated first, then the body uses them as context.
    graph.add_edge("resume_complete", "cl_intro_conclusion_generator")
    graph.add_edge("cl_intro_conclusion_generator", "cl_body_generator")
    
    # The body generator now feeds into the decision point
    graph.add_edge("cl_body_generator", "cl_decision")
    
    # Conditional edges from decision node
    graph.add_conditional_edges(
        "cl_decision",
        cl_decision_router,
        {
            "regenerate": "cl_regenerator",
            "complete": "cl_complete"
        }
    )
    
    # After regeneration, go back to decision
    graph.add_edge("cl_regenerator", "cl_decision")
    
    # End the graph after cover letter completion
    graph.add_edge("cl_complete", END)

    # Compile the graph into a runnable application
    app = graph.compile()
    return app 