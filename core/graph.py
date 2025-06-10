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
        # --- Resume Length Fields ---
        generated_resume_full_text: str
        resume_line_count: int
        resume_is_too_long: bool
        resume_fix_choice: str # User's choice: 'AGENT_FIX' or 'USER_FIX'
        # --- Cover Letter Fields ---
        generated_cl_intro: The AI-generated introduction for the cover letter.
        generated_cl_conclusion: The AI-generated conclusion.
        generated_cl_body: The AI-generated body paragraphs.
        cl_feedback_history: A list to store user feedback for regeneration.
        user_action: A string to control conditional flows (e.g., 'REGENERATE', 'PROCEED_TO_CL').
    """
    job_description_text: str
    master_resume_structured: Dict[str, Any]
    rag_retrievers: Dict[str, Any]
    selected_project_titles: List[str]
    generated_resume_summary: str
    generated_resume_projects: Dict[str, str]
    # --- Resume Length Fields ---
    generated_resume_full_text: str
    resume_line_count: int
    resume_is_too_long: bool
    resume_fix_choice: str
    # --- Cover Letter Fields ---
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

    # --- New nodes for resume length check ---
    graph.add_node("assemble_and_check_length", agents.assemble_and_check_length)
    graph.add_node("shorten_resume", agents.shorten_resume)
    def prompt_user_for_fix(state: GraphState):
        """A placeholder node to represent the point where we wait for user input."""
        print("---STATE: Resume is too long. Prompting user for action.---")
        # In the real app, the UI would handle this pause.
        # Here, we just pass through. The user's choice will be in the state.
        return {}
    graph.add_node("prompt_user_for_fix", prompt_user_for_fix)

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
        # Add new condition to proceed to Cover Letter generation
        elif user_action == "PROCEED_TO_CL":
            return "proceed"
        else:
            return "complete"

    # --- Wire Nodes Together with Edges ---
    
    # New, stable entry point node
    def entry_point_node(state: GraphState):
        """A dummy node to serve as a stable entry point for the graph."""
        print("---GRAPH: Determining entry route---")
        return {}
    graph.add_node("entry_point", entry_point_node)
    graph.set_entry_point("entry_point")

    # The router function is now only used for conditional logic
    def initial_run_router(state: GraphState):
        """Determines if this is the first run or a user-driven update."""
        if state.get("selected_project_titles"):
            # If projects are already selected by the user, skip AI selection
            return "rewrite_only"
        else:
            # Otherwise, it's the first run
            return "initial_run"

    # Conditional routing from the new stable entry point
    graph.add_conditional_edges(
        "entry_point",
        initial_run_router,
        {
            "initial_run": "project_selector",
            # On user updates, only rewrite projects, don't re-run summary
            "rewrite_only": "project_rewriter" 
        }
    )

    # Resume generation flow
    graph.add_edge("project_selector", "summary_generator")
    graph.add_edge("project_selector", "project_rewriter")

    # The two resume generation branches now feed into our length checker.
    # The original edges to resume_complete are replaced.
    graph.add_edge("summary_generator", "assemble_and_check_length")
    graph.add_edge("project_rewriter", "assemble_and_check_length")

    # After checking the length, decide whether to fix it or continue
    def length_decision_router(state: GraphState):
        """Routes based on whether the resume is too long."""
        if state.get("resume_is_too_long", False):
            # If it's too long, we prompt the user for what to do next
            return "prompt_user"
        else:
            # If length is fine, we consider the resume complete
            return "resume_is_ok"

    graph.add_conditional_edges(
        "assemble_and_check_length",
        length_decision_router,
        {"prompt_user": "prompt_user_for_fix", "resume_is_ok": "resume_complete"},
    )

    # After prompting the user, decide whether the agent should fix it
    def fix_path_router(state: GraphState):
        """Routes based on the user's choice for fixing the resume."""
        if state.get("resume_fix_choice") == "AGENT_FIX":
            return "agent_fix"
        else:
            # If user wants to fix it, or no choice is made, we proceed
            return "user_fix_or_continue"

    graph.add_conditional_edges(
        "prompt_user_for_fix",
        fix_path_router,
        {
            "agent_fix": "shorten_resume",
            "user_fix_or_continue": "resume_complete",
        },
    )

    # The agent shortener loops back to re-check the length
    graph.add_edge("shorten_resume", "assemble_and_check_length")
    
    # --- Defer Cover Letter Generation ---
    # The `resume_complete` node now goes to a new decision point.
    
    # The node's function must return a dictionary.
    def cl_start_decision_node(state: GraphState):
        """A dummy node to act as the decision point for starting the CL."""
        print("---GRAPH: Deciding whether to proceed to Cover Letter---")
        return {}

    # The router function for the conditional edge must return a string.
    def cl_start_router(state: GraphState):
        """Router to decide whether to start CL generation or end."""
        if state.get("user_action") == "PROCEED_TO_CL":
            return "proceed"
        else:
            return "end_resume_phase"

    graph.add_node("cl_start_decision", cl_start_decision_node)
    graph.add_edge("resume_complete", "cl_start_decision")
    
    graph.add_conditional_edges(
        "cl_start_decision",
        cl_start_router,
        {
            "proceed": "cl_intro_conclusion_generator",
            "end_resume_phase": END # Stop here if user hasn't clicked proceed
        }
    )

    # After resume completion, start cover letter generation serially.
    graph.add_edge("cl_intro_conclusion_generator", "cl_body_generator")
    
    # The body generator now feeds into the decision point
    graph.add_edge("cl_body_generator", "cl_decision")
    
    # Conditional edges from decision node
    graph.add_conditional_edges(
        "cl_decision",
        cl_decision_router,
        {
            "regenerate": "cl_regenerator",
            "complete": "cl_complete",
            "proceed": "cl_complete" # If 'PROCEED_TO_CL' is still the action, just complete.
        }
    )
    
    # After regeneration, go back to decision
    graph.add_edge("cl_regenerator", "cl_decision")
    
    # End the graph after cover letter completion
    graph.add_edge("cl_complete", END)

    # Compile the graph into a runnable application
    app = graph.compile()
    return app 