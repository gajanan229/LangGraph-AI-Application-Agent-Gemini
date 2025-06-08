import unittest
from unittest.mock import patch, MagicMock
from docx import Document
from core.doc_generator import create_resume_pdf, create_cover_letter_pdf

# Constants for template paths from the user-provided structure
RESUME_TEMPLATE_PATH = "Templates/resume_template.docx"
PROJECT_TEMPLATE_PATH = "Templates/Project_template.docx"
COVER_LETTER_TEMPLATE_PATH = "Templates/cover_letter_template.docx"


class TestDocGenerator(unittest.TestCase):
    """Unit tests for the final document generation module."""

    @patch("core.doc_generator.convert")
    def test_create_resume_pdf_returns_bytes(self, mock_convert):
        """
        Tests that create_resume_pdf correctly fills templates and returns
        a non-empty byte string, mocking the actual PDF conversion.
        """
        # Arrange
        mock_convert.side_effect = lambda docx_in, pdf_out: pdf_out.write(b"dummy pdf content")
        
        summary = "This is a test summary."
        projects = [
            {"title": "Project Apollo", "rewritten_text": "- Bullet point 1\n- Bullet point 2"}
        ]

        # Act
        pdf_bytes = create_resume_pdf(
            RESUME_TEMPLATE_PATH, PROJECT_TEMPLATE_PATH, summary, projects
        )

        # Assert
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 0)
        self.assertEqual(pdf_bytes, b"dummy pdf content")
        mock_convert.assert_called_once()

    @patch("core.doc_generator.convert")
    def test_create_cover_letter_pdf_returns_bytes(self, mock_convert):
        """
        Tests that create_cover_letter_pdf fills placeholders and returns
        a non-empty byte string, mocking the PDF conversion.
        """
        # Arrange
        mock_convert.side_effect = lambda docx_in, pdf_out: pdf_out.write(b"dummy cl content")

        intro = "Dear Hiring Manager,"
        body = "This is the main body of the cover letter."
        conclusion = "Sincerely, John Doe"

        # Act
        pdf_bytes = create_cover_letter_pdf(
            COVER_LETTER_TEMPLATE_PATH, intro, body, conclusion
        )

        # Assert
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 0)
        self.assertEqual(pdf_bytes, b"dummy cl content")
        mock_convert.assert_called_once()

    def test_placeholder_replacement_in_resume(self):
        """
        Verifies that placeholders are actually replaced in the DOCX object
        before conversion.
        """
        # This test checks the docx content directly, without mocking 'convert'.
        # It's more of an integration test for the docx manipulation logic.
        summary = "UNIQUE_SUMMARY_TEXT_123"
        project_title = "UNIQUE_PROJECT_TITLE_456"
        project_bullets = "UNIQUE_BULLET_POINTS_789"
        
        projects = [
            {"title": project_title, "rewritten_text": project_bullets}
        ]

        # We don't need the output, we need to inspect the docx object
        # that gets passed to the mocked convert function.
        with patch("core.doc_generator.convert") as mock_convert:
            create_resume_pdf(RESUME_TEMPLATE_PATH, PROJECT_TEMPLATE_PATH, summary, projects)
            
            # Get the docx file bytes from the buffer passed to convert
            self.assertTrue(mock_convert.called)
            call_args = mock_convert.call_args[0]
            docx_buffer = call_args[0]
            
            # Re-open the buffer as a Document and inspect its contents
            doc = Document(docx_buffer)
            full_text = "\n".join([p.text for p in doc.paragraphs])
            
            self.assertIn(summary, full_text)
            self.assertIn(project_title, full_text)
            self.assertIn(project_bullets, full_text)
            self.assertNotIn("[SUMMARY]", full_text)
            self.assertNotIn("[PROJECT TITLE]", full_text)
            self.assertNotIn("[PROJECT BULLET POINTS]", full_text)


if __name__ == "__main__":
    unittest.main() 