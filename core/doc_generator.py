import io
import os
import tempfile
from typing import Dict, List, Optional
import pythoncom
from docx import Document
from docx.document import Document as DocxDocument
from docx.text.paragraph import Paragraph
from docx2pdf import convert


def _delete_paragraph(paragraph: Paragraph):
    """Safely removes a paragraph from a document."""
    p_element = paragraph._element
    if p_element.getparent() is not None:
        p_element.getparent().remove(p_element)


def _find_first_paragraph_with_text(doc: DocxDocument, text: str) -> Optional[Paragraph]:
    """Finds the first paragraph containing the given text."""
    for p in doc.paragraphs:
        if text in p.text:
            return p
    return None


def _replace_text_in_paragraph(p: Paragraph, placeholder: str, value: str):
    """
    Replaces placeholder text in a paragraph while preserving formatting.
    Assumes the placeholder exists entirely within a single run.
    """
    for run in p.runs:
        if placeholder in run.text:
            run.text = run.text.replace(placeholder, value)
            break  # Assume placeholder appears only once per paragraph


def create_resume_pdf(
    resume_template_path: str,
    project_template_path: str, # This will be ignored but kept for compatibility
    summary_text: str,
    project_data: List[Dict[str, str]],
) -> bytes:
    """
    Builds a resume by populating a DOCX template to preserve formatting,
    then converts it to PDF.
    """
    doc = Document(resume_template_path)

    # 1. Replace Summary
    for p in doc.paragraphs:
        if "[SUMMARY]" in p.text:
            _replace_text_in_paragraph(p, "[SUMMARY]", summary_text)

    # 2. Inject Projects
    # Find the style templates and the anchor point for insertion
    title_anchor = _find_first_paragraph_with_text(doc, "[PROJECT TITLE]")
    bullets_anchor = _find_first_paragraph_with_text(doc, "[PROJECT BULLET POINTS]")

    if title_anchor and bullets_anchor:
        title_style = title_anchor.style
        bullet_style = bullets_anchor.style

        # Insert projects before the title anchor
        for project in reversed(project_data):
            # Split rewritten text into bullet points, filtering out empty lines
            bullet_points = [b.strip() for b in project.get("rewritten_text", "").split('\n') if b.strip()]
            
            # Insert bullet points in reverse order to maintain correct sequence
            for point in reversed(bullet_points):
                title_anchor.insert_paragraph_before(point, style=bullet_style)
            
            # Insert the project title
            title_anchor.insert_paragraph_before(project.get("title", ""), style=title_style)
        
        # 3. Cleanup placeholders
        _delete_paragraph(title_anchor)
        _delete_paragraph(bullets_anchor)

    # 4. Save and Convert to PDF
    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = os.path.join(tmpdir, "final_resume.docx")
        pdf_path = os.path.join(tmpdir, "final_resume.pdf")
        doc.save(docx_path)
        try:
            pythoncom.CoInitialize()
            convert(docx_path, pdf_path)
        finally:
            pythoncom.CoUninitialize()  # Ensure COM is uninitialized
            
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

    return pdf_bytes


def create_cover_letter_pdf(
    template_path: str, intro: str, body: str, conclusion: str
) -> bytes:
    """
    Builds a cover letter by populating a DOCX template, then converts to PDF.
    """
    doc = Document(template_path)
    
    # Replace simple placeholders
    for p in doc.paragraphs:
        if "[INTRODUCTION]" in p.text:
            _replace_text_in_paragraph(p, "[INTRODUCTION]", intro)
        if "[CONCLUSION]" in p.text:
            _replace_text_in_paragraph(p, "[CONCLUSION]", conclusion)

    # Handle the multi-line body
    body_anchor = _find_first_paragraph_with_text(doc, "[BODY]")
    if body_anchor:
        body_lines = [line.strip() for line in body.split('\n') if line.strip()]
        if body_lines:
            # Set the first line in the anchor paragraph
            body_anchor.text = body_lines[0]
            # Insert subsequent lines after the anchor
            cursor = body_anchor
            for line in body_lines[1:]:
                new_p = cursor.insert_paragraph_before(line, style=body_anchor.style)
                # This inserts before, so we don't need to manage the cursor manually.
                # To keep order, insert all before the *next* paragraph, or just
                # insert them all before the original anchor and they will be in order.
            
            # Let's use the same reverse-insertion logic as the resume for simplicity
            for line in reversed(body_lines[1:]):
                body_anchor.insert_paragraph_before(line, style=body_anchor.style)
            body_anchor.text = body_lines[0] # set first line last

        else:
            # If body is empty, remove the placeholder
            _delete_paragraph(body_anchor)
    
    # Save and Convert to PDF
    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = os.path.join(tmpdir, "final_cl.docx")
        pdf_path = os.path.join(tmpdir, "final_cl.pdf")
        doc.save(docx_path)
        try:
            pythoncom.CoInitialize()
            convert(docx_path, pdf_path)
        finally:
            pythoncom.CoUninitialize()  # Ensure COM is uninitialized

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

    return pdf_bytes 