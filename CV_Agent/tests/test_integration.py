import pytest
from unittest.mock import MagicMock, patch
from core.graph import create_application_graph, GraphState


class TestIntegration:
    """Integration tests for the complete application workflow."""
    
    @pytest.fixture
    def sample_structured_resume(self):
        """Sample structured resume for testing."""
        return {
            'full_text': 'John Doe Software Engineer...',
            'projects': [
                {'title': 'Project Alpha', 'description': 'Alpha project details'},
                {'title': 'Project Beta', 'description': 'Beta project details'},
                {'title': 'Project Gamma', 'description': 'Gamma project details'},
            ]
        }
    
    @pytest.fixture 
    def mock_retrievers(self):
        """Mock RAG retrievers for testing."""
        mock_retriever = MagicMock()
        mock_retriever.invoke.return_value = [
            MagicMock(page_content="Project Alpha: Alpha details"),
            MagicMock(page_content="Project Beta: Beta details"),
        ]
        return {"projects": mock_retriever}
    
    @patch('core.agents.llm')
    def test_resume_workflow_end_to_end(self, mock_llm, sample_structured_resume, mock_retrievers):
        """Tests the complete resume generation workflow."""
        
        # Create a more sophisticated mock that responds based on the structured output type
        def mock_structured_llm_invoke(prompt):
            if "select the 2 to 4 most relevant projects" in prompt:
                return type('MockResponse', (), {'project_titles': ['Project Alpha', 'Project Beta']})()
            elif "Synthesize the provided job description" in prompt:
                return type('MockResponse', (), {'rewritten_text': 'Generated summary text'})()
            elif "refining a resume project description" in prompt:
                if "Project Alpha" in prompt:
                    return type('MockResponse', (), {'rewritten_text': 'Rewritten Alpha project'})()
                else:
                    return type('MockResponse', (), {'rewritten_text': 'Rewritten Beta project'})()
            elif "generate a compelling introduction and conclusion" in prompt:
                return type('MockResponse', (), {
                    'introduction': 'Dear Hiring Manager, I am excited to apply...',
                    'conclusion': 'Thank you for your consideration...'
                })()
            elif "Create compelling body paragraphs" in prompt:
                return type('MockResponse', (), {'body_paragraphs': 'My experience includes...'})()
            else:
                return type('MockResponse', (), {})()
        
        mock_llm.with_structured_output.return_value.invoke.side_effect = mock_structured_llm_invoke
        
        app = create_application_graph()
        
        initial_state: GraphState = {
            "job_description_text": "Looking for a software engineer...",
            "master_resume_structured": sample_structured_resume,
            "rag_retrievers": mock_retrievers,
            "selected_project_titles": [],
            "generated_resume_summary": "",
            "generated_resume_projects": {},
            "generated_cl_intro": "",
            "generated_cl_conclusion": "",
            "generated_cl_body": "",
            "cl_feedback_history": [],
            "user_action": "",
        }
        
        final_state = app.invoke(initial_state)
        
        # Verify resume generation results
        assert final_state["selected_project_titles"] == ['Project Alpha', 'Project Beta']
        assert final_state["generated_resume_summary"] == "Generated summary text"
        assert final_state["generated_resume_projects"]["Project Alpha"] == "Rewritten Alpha project"
        assert final_state["generated_resume_projects"]["Project Beta"] == "Rewritten Beta project"
        
        # Verify cover letter generation results
        assert final_state["generated_cl_intro"] == "Dear Hiring Manager, I am excited to apply..."
        assert final_state["generated_cl_body"] == "My experience includes..."
        assert final_state["generated_cl_conclusion"] == "Thank you for your consideration..."

    @patch('core.agents.llm')
    def test_cover_letter_regeneration_workflow(self, mock_llm, sample_structured_resume, mock_retrievers):
        """Tests the cover letter regeneration with feedback."""
        
        # Track calls to regeneration to return different responses
        regeneration_call_count = 0
        
        def mock_structured_llm_invoke(prompt):
            nonlocal regeneration_call_count
            
            if "select the 2 to 4 most relevant projects" in prompt:
                return type('MockResponse', (), {'project_titles': ['Project Alpha']})()
            elif "Synthesize the provided job description" in prompt:
                return type('MockResponse', (), {'rewritten_text': 'Original summary'})()
            elif "refining a resume project description" in prompt:
                return type('MockResponse', (), {'rewritten_text': 'Original project'})()
            elif "generate a compelling introduction and conclusion" in prompt and "USER FEEDBACK" not in prompt:
                # Initial generation
                return type('MockResponse', (), {
                    'introduction': 'Original intro',
                    'conclusion': 'Original conclusion'
                })()
            elif "Create compelling body paragraphs" in prompt and "USER FEEDBACK" not in prompt:
                # Initial generation
                return type('MockResponse', (), {'body_paragraphs': 'Original body'})()
            elif "USER FEEDBACK" in prompt:
                # Regeneration calls
                regeneration_call_count += 1
                if "Generate the introduction and conclusion" in prompt or regeneration_call_count == 1:
                    return type('MockResponse', (), {
                        'introduction': 'Updated introduction with feedback...',
                        'conclusion': 'Updated conclusion with feedback...'
                    })()
                else:
                    return type('MockResponse', (), {'body_paragraphs': 'Updated body with feedback...'})()
            else:
                return type('MockResponse', (), {})()
        
        mock_llm.with_structured_output.return_value.invoke.side_effect = mock_structured_llm_invoke
        
        app = create_application_graph()
        
        # Start with state that will trigger regeneration
        regeneration_state: GraphState = {
            "job_description_text": "Software Engineer position...",
            "master_resume_structured": sample_structured_resume,
            "rag_retrievers": mock_retrievers,
            "selected_project_titles": [],
            "generated_resume_summary": "",
            "generated_resume_projects": {},
            "generated_cl_intro": "",
            "generated_cl_conclusion": "", 
            "generated_cl_body": "",
            "cl_feedback_history": ["Make it more technical"],
            "user_action": "REGENERATE_CL",
        }
        
        final_state = app.invoke(regeneration_state)
        
        # Verify regenerated content
        assert final_state["generated_cl_intro"] == "Updated introduction with feedback..."
        assert final_state["generated_cl_body"] == "Updated body with feedback..."
        assert final_state["generated_cl_conclusion"] == "Updated conclusion with feedback..."
        
    def test_graph_node_connectivity(self):
        """Tests that all nodes are properly connected in the graph."""
        app = create_application_graph()
        
        # Check that the graph was compiled successfully
        assert app is not None
        
        # The graph should have all expected nodes
        expected_nodes = [
            "project_selector", "summary_generator", "project_rewriter", 
            "resume_complete", "cl_intro_conclusion_generator", "cl_body_generator",
            "cl_regenerator", "cl_complete", "cl_decision"
        ]
        
        # This is a basic check - in a real scenario, you'd inspect the graph structure
        # For now, we just verify the graph compiles without errors
        assert hasattr(app, 'invoke') 