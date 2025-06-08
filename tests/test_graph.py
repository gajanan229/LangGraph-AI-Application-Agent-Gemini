import unittest
from unittest.mock import patch, MagicMock
from core.graph import create_application_graph, GraphState
from core.agents import (
    SelectedProjects,
    ResumeSection,
)


class TestApplicationGraph(unittest.TestCase):
    """Integration tests for the main application graph."""

    def test_graph_executes_resume_flow_end_to_end(self):
        """
        Tests the complete resume generation flow of the graph, from project
        selection to final state, with mocked LLM calls.
        """
        # 1. Mock the LLM and its structured outputs
        mock_llm = MagicMock()

        select_projects_response = SelectedProjects(project_titles=["Project A", "Project B"])
        generate_summary_response = ResumeSection(rewritten_text="This is a test summary.")
        rewrite_projects_response = ResumeSection(rewritten_text="Rewritten project text.")

        # This mock function inspects the prompt to return the correct response,
        # making the test deterministic even with parallel execution.
        def mock_invoke_logic(prompt, *args, **kwargs):
            if "select the 2 to 4 most relevant projects" in prompt:
                return select_projects_response
            elif "Synthesize the provided job description" in prompt:
                return generate_summary_response
            elif "refining a resume project description" in prompt:
                return rewrite_projects_response
            return MagicMock()

        # Configure the mock to use this logic
        # The inner mock structure (.with_structured_output.return_value.invoke)
        # matches the actual call chain in the agents.
        structured_mock = MagicMock()
        structured_mock.invoke.side_effect = mock_invoke_logic
        mock_llm.with_structured_output.return_value = structured_mock
        
        # 2. Patch the LLM instance in the agents module
        with patch("core.agents.llm", mock_llm):
            # 3. Create the graph and initial state
            app = create_application_graph()
            initial_state: GraphState = {
                "job_description_text": "A test job description.",
                "master_resume_structured": {
                    "full_text": "Full resume text.",
                    "projects": [
                        {"title": "Project A", "description": "Desc A"},
                        {"title": "Project B", "description": "Desc B"},
                    ],
                },
                "rag_retrievers": {
                    "projects": MagicMock(invoke=MagicMock(return_value=[]))
                },
                "selected_project_titles": [],
                "generated_resume_summary": "",
                "generated_resume_projects": {},
                "generated_cl_intro": "",
                "generated_cl_conclusion": "",
                "generated_cl_body": "",
                "cl_feedback_history": [],
                "user_action": "",
            }

            # 4. Invoke the graph
            final_state = app.invoke(initial_state)

            # 5. Assert the final state is as expected
            self.assertEqual(final_state["generated_resume_summary"], "This is a test summary.")
            self.assertIn("Project A", final_state["generated_resume_projects"])
            self.assertEqual(
                final_state["generated_resume_projects"]["Project B"],
                "Rewritten project text.",
            )
            self.assertEqual(len(final_state["selected_project_titles"]), 2)
            self.assertEqual(final_state["selected_project_titles"][0], "Project A")


if __name__ == "__main__":
    unittest.main() 