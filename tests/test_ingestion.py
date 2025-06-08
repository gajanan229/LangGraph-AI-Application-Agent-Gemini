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
        based on the specific hardcoded headers.
        """
        sample_text = """
        John Doe
        john.doe@email.com | 555-1234 | github.com/johndoe

        Summary
        A highly motivated and experienced software engineer.

        Skills and Interests
        Python, JavaScript, SQL, AWS, Docker

        Education
        B.S. in Computer Science - State University (2016 - 2020)

        Work Experience
        Software Engineer at Tech Corp (2020 - Present)
        - Developed and maintained web applications.

        Projects
        Movie Rating and Recommendations Website
        - An app for ranking movies.
        AI Job Application Email Assistant
        - An assistant for writing emails.
        """
        data = parse_master_resume(sample_text)

        # According to the user's logic, this contains everything up to "Skills and Interests"
        self.assertIn("John Doe", data["summary_and_contact"])
        self.assertIn("A highly motivated", data["summary_and_contact"])
        
        # Test other sections based on the rigid parsing
        self.assertTrue(data["skills"].strip().startswith("Python"))
        self.assertTrue(data["education"].strip().startswith("B.S. in Computer Science"))
        self.assertTrue(data["experience"].strip().startswith("Software Engineer"))
        
        # Test that hardcoded project titles are found
        self.assertEqual(len(data["projects"]), 2)
        self.assertEqual(data["projects"][0]["title"], "Movie Rating and Recommendations Website")
        self.assertEqual(data["projects"][1]["title"], "AI Job Application Email Assistant")

    def test_parse_projects_section_handles_hardcoded_titles(self):
        """
        Tests that the project parser can correctly identify and separate
        multiple distinct projects from a text block using its hardcoded titles.
        """
        project_text = """
        Some intro text that should be ignored.
        ASL Flashcard App
        - Developed a Flashcard application for learning American Sign Language.
        Bookstore Project
        - We collaboratively built a user-friendly GUI for an online bookstore.
        Some text after projects that should be ignored.
        """
        
        # We test the parsing logic via the main function
        data = parse_master_resume("Projects\n" + project_text)
        projects = data.get("projects", [])

        self.assertEqual(len(projects), 2)
        self.assertEqual(projects[0]["title"], "ASL Flashcard App")
        self.assertIn("American Sign Language", projects[0]["description"])
        self.assertEqual(projects[1]["title"], "Bookstore Project")
        self.assertIn("online bookstore", projects[1]["description"])

    def test_empty_sections_are_handled_by_rigid_parser(self):
        """
        Tests that the parser returns empty values for sections when their
        bounding headers are missing, according to its logic.
        """
        sample_text = """
        Jane Smith
        jane@email.com

        Education
        M.A. in English
        """
        data = parse_master_resume(sample_text)

        # The user's parser requires specific start and end headers.
        # Without `Skills and Interests` or `Work Experience`, it won't find education.
        # This test now asserts the actual behavior of the hardcoded parser.
        self.assertEqual(data["experience"], "")
        self.assertEqual(data["skills"], "")
        self.assertEqual(data["education"], "")
        self.assertEqual(len(data["projects"]), 0)


if __name__ == "__main__":
    unittest.main() 