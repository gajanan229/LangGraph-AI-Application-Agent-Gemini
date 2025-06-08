import os
import unittest
from core.ingestion import parse_master_resume, parse_pdf


class TestIngestion(unittest.TestCase):
    """Unit tests for the document ingestion and parsing module."""

    def test_parse_pdf_returns_non_empty_text(self):
        """
        Tests that parse_pdf successfully extracts a non-empty string from
        the sample PDF file.
        """
        pdf_path = os.path.join("Input-Documents", "Master_Resume.pdf")
        self.assertTrue(os.path.exists(pdf_path), f"Sample file not found: {pdf_path}")

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        text = parse_pdf(pdf_bytes)
        self.assertIsInstance(text, str)
        self.assertGreater(
            len(text), 500, "Parsed text from sample resume seems too short."
        )

    def test_parse_master_resume_identifies_all_sections(self):
        """
        Tests that the resume parser correctly identifies all major sections
        from a sample text block, regardless of header case.
        """
        sample_text = """
        John Doe
        john.doe@email.com | 555-1234 | github.com/johndoe

        SUMMARY
        A highly motivated and experienced software engineer.

        Work Experience
        Software Engineer at Tech Corp (2020 - Present)
        - Developed and maintained web applications.

        EDUCATION
        B.S. in Computer Science - State University (2016 - 2020)

        sKiLlS
        Python, JavaScript, SQL, AWS, Docker

        PrOjEcTs
        AI-Powered Chatbot
        - Created a customer service chatbot using TensorFlow.
        """
        data = parse_master_resume(sample_text)

        self.assertIn("John Doe", data["summary_and_contact"])
        self.assertTrue(data["experience"].strip().startswith("Software Engineer"))
        self.assertTrue(data["education"].strip().startswith("B.S. in Computer Science"))
        self.assertTrue(data["skills"].strip().startswith("Python"))
        self.assertEqual(len(data["projects"]), 1)
        self.assertEqual(data["projects"][0]["title"], "AI-Powered Chatbot")

    def test_parse_projects_section_handles_multiple_projects(self):
        """
        Tests that the project parser can correctly identify and separate
        multiple distinct projects from a text block.
        """
        project_text = """
        Project Alpha
        - Built a cool web app using Python and Flask.
        - Deployed it on AWS infrastructure.

        Another Project (Beta)
        - Developed a cross-platform mobile app with React Native.
        - Integrated with a RESTful API for data fetching.
        """
        
        # We test the parsing logic via the main function
        data = parse_master_resume("PROJECTS\n" + project_text)
        projects = data.get("projects", [])

        self.assertEqual(len(projects), 2)
        self.assertEqual(projects[0]["title"], "Project Alpha")
        self.assertIn("Flask", projects[0]["description"])
        self.assertEqual(projects[1]["title"], "Another Project (Beta)")
        self.assertIn("React Native", projects[1]["description"])

    def test_empty_sections_are_handled_gracefully(self):
        """
        Tests that the parser does not fail and returns empty values for
        sections that are missing from the resume text.
        """
        sample_text = """
        Jane Smith
        jane@email.com

        Education
        M.A. in English
        """
        data = parse_master_resume(sample_text)

        self.assertEqual(data["experience"], "")
        self.assertEqual(data["skills"], "")
        self.assertEqual(len(data["projects"]), 0)
        self.assertTrue(data["education"].strip().startswith("M.A. in English"))

if __name__ == "__main__":
    unittest.main() 