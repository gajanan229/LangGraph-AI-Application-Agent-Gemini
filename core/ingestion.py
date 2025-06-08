import io
import re
from typing import Any, Dict, List

import pypdf


def parse_pdf(file_bytes: bytes) -> str:
    """Extracts text from a PDF file's bytes.

    Args:
        file_bytes: The byte content of the PDF file.

    Returns:
        A single string containing the document's full text.
    """
    pdf_file = io.BytesIO(file_bytes)
    reader = pypdf.PdfReader(pdf_file)
    full_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"
    return full_text


def _parse_projects_section(project_text: str) -> List[Dict[str, str]]:
    """Parses the text of a projects section into a list of structured projects."""
    projects = []
    
    # Clean up the text first - remove extra spaces between words
    cleaned_text = re.sub(r'\s+', ' ', project_text.strip())
    
    # Define project title patterns - these are the actual project titles from the resume
    project_titles = [
        "Movie Rating and Recommendations Website",
        "Digit Recognition App", 
        "Image Watermarking Desktop App",
        "ASL Flashcard App",
        "AI Job Application Email Assistant",
        "Bookstore Project",
        "Family Travel Map Tracker",
        "RESTful Blog API & Client with Authentication",
        "Notes App with the PERN stack",
        "Portfolio Blog with AI Chatbot Integration, gajanan.live"
    ]
    
    # Split the text based on project titles
    remaining_text = cleaned_text
    
    for i, title in enumerate(project_titles):
        # Find the current project title in the text
        title_match = re.search(re.escape(title), remaining_text, re.IGNORECASE)
        if not title_match:
            continue
            
        # Find the start of the next project (or end of text)
        next_title_start = len(remaining_text)  # Default to end of text
        
        # Look for the next project title
        for next_title in project_titles[i+1:]:
            next_match = re.search(re.escape(next_title), remaining_text, re.IGNORECASE)
            if next_match and next_match.start() > title_match.end():
                next_title_start = next_match.start()
                break
        
        # Extract the project content (from current title to next title)
        project_content = remaining_text[title_match.start():next_title_start].strip()
        
        # Remove the title from the content to get just the description
        description = project_content[len(title):].strip()
        
        # Clean up the description by removing bullet points and extra spaces
        description_lines = []
        # Split by bullet points to get individual bullet items
        bullet_items = re.split(r'●', description)
        
        for item in bullet_items:
            item = item.strip()
            if item:  # Skip empty items
                description_lines.append(item)
        
        # Join the cleaned description
        final_description = '\n'.join(description_lines)
        
        projects.append({
            'title': title,
            'description': final_description
        })
    
    return projects


def parse_master_resume(resume_text: str) -> Dict[str, Any]:
    """Parses a master resume text into a structured dictionary.

    Uses regular expressions to identify and separate distinct sections like
    Projects, Work Experience, Education, and Skills based on common headers.

    Args:
        resume_text: The full text of the resume.

    Returns:
        A dictionary with structured resume data.
    """
    
    # Initialize the structured data
    structured_data: Dict[str, Any] = {
        "full_text": resume_text,
        "summary_and_contact": "",
        "projects": [],
        "experience": "",
        "skills": "",
        "education": "",
    }
    
    # Clean up spacing in the text for better processing
    cleaned_text = re.sub(r'\s+', ' ', resume_text)
    
    # Define section boundaries more precisely
    # Look for the actual section headers in the text
    summary_match = re.search(r'Summary\s', cleaned_text, re.IGNORECASE)
    skills_match = re.search(r'Skills\s+and\s+Interests', cleaned_text, re.IGNORECASE)
    education_match = re.search(r'Education\s', cleaned_text, re.IGNORECASE)
    work_match = re.search(r'Work\s+Experience', cleaned_text, re.IGNORECASE)
    projects_match = re.search(r'Projects\s', cleaned_text, re.IGNORECASE)
    
    # Extract summary and contact info (everything before Skills section)
    if skills_match:
        structured_data["summary_and_contact"] = cleaned_text[:skills_match.start()].strip()
    
    # Extract Skills section (from Skills to Education)
    if skills_match and education_match:
        skills_text = cleaned_text[skills_match.start():education_match.start()].strip()
        # Remove the header
        skills_text = re.sub(r'^Skills\s+and\s+Interests\s*', '', skills_text, flags=re.IGNORECASE)
        structured_data["skills"] = skills_text.strip()
    
    # Extract Education section (from Education to Work Experience)
    if education_match and work_match:
        education_text = cleaned_text[education_match.start():work_match.start()].strip()
        # Remove the header
        education_text = re.sub(r'^Education\s*', '', education_text, flags=re.IGNORECASE)
        structured_data["education"] = education_text.strip()
    
    # Extract Work Experience section (from Work Experience to Projects)
    if work_match and projects_match:
        experience_text = cleaned_text[work_match.start():projects_match.start()].strip()
        # Remove the header
        experience_text = re.sub(r'^Work\s+Experience\s*', '', experience_text, flags=re.IGNORECASE)
        structured_data["experience"] = experience_text.strip()
    
    # Extract Projects section (from Projects to end)
    if projects_match:
        projects_text = cleaned_text[projects_match.start():].strip()
        # Remove the header
        projects_text = re.sub(r'^Projects\s*', '', projects_text, flags=re.IGNORECASE)
        structured_data["projects"] = _parse_projects_section(projects_text)
    
    return structured_data