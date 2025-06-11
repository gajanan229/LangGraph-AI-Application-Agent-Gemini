import os
import unittest
from unittest.mock import MagicMock, patch

from langchain_core.vectorstores import VectorStoreRetriever

from core.rag_setup import setup_rag_pipeline


class TestRagSetup(unittest.TestCase):
    """Unit tests for the RAG pipeline setup."""

    @patch("core.rag_setup.GoogleGenerativeAIEmbeddings")
    @patch("core.rag_setup.FAISS")
    def test_setup_rag_pipeline_creates_retriever(
        self, mock_faiss, mock_embeddings
    ):
        """
        Tests that setup_rag_pipeline correctly initializes and returns a
        VectorStoreRetriever when provided with valid project data.
        """
        # Set a dummy API key for the check
        os.environ["GOOGLE_API_KEY"] = "test_key"

        # Arrange: Create mock objects for the dependencies
        mock_embeddings_instance = MagicMock()
        mock_embeddings.return_value = mock_embeddings_instance

        mock_vector_store = MagicMock()
        mock_retriever = MagicMock(spec=VectorStoreRetriever)
        mock_vector_store.as_retriever.return_value = mock_retriever
        mock_faiss.from_documents.return_value = mock_vector_store

        # Arrange: Create sample structured resume data
        structured_resume = {
            "projects": [
                {
                    "title": "Test Project 1",
                    "description": "This is the first test project.",
                }
            ]
        }

        # Act: Call the function to be tested
        result = setup_rag_pipeline(structured_resume)

        # Assert: Check that the dependencies were called correctly
        mock_embeddings.assert_called_once_with(model="models/embedding-001")
        mock_faiss.from_documents.assert_called_once()
        mock_vector_store.as_retriever.assert_called_once()

        # Assert: Check that the result is in the expected format
        self.assertIn("projects", result)
        self.assertIsInstance(result["projects"], VectorStoreRetriever)

        # Clean up the dummy environment variable
        del os.environ["GOOGLE_API_KEY"]

    def test_setup_rag_pipeline_no_projects(self):
        """
        Tests that the function handles cases with no projects gracefully.
        """
        os.environ["GOOGLE_API_KEY"] = "test_key"
        structured_resume = {"projects": []}
        result = setup_rag_pipeline(structured_resume)
        self.assertIn("projects", result)
        self.assertIsNone(result["projects"])
        del os.environ["GOOGLE_API_KEY"]


if __name__ == "__main__":
    unittest.main() 