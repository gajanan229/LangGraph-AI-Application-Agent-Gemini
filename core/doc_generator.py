import io
from typing import Dict, List
from docx.document import Document as DocxDocument
from docx.oxml.text.paragraph import CT_P
from docx import Document
from docx2pdf import convert


def _append_project_to_document(main_doc: DocxDocument, project_doc: DocxDocument):
    """
    Appends the content of a project document to the main document.

    This function iterates through the elements (paragraphs, tables) of the
    project document and adds them to the end of the main document's body.
    """
    for element in project_doc.element.body:
        # To avoid issues with shared elements, create a deep copy for paragraphs
        if isinstance(element, CT_P):
            new_element = main_doc.add_paragraph()._p
            new_element.getparent().replace(new_element, element)
        else:
            # For other elements like tables, a shallow copy might suffice,
            # but direct appending is often problematic. This is a simplification.
            # A more robust solution might require deep copying other element types.
            main_doc.element.body.append(element)


def create_resume_pdf(
    resume_template_path: str,
    project_template_path: str,
    summary_text: str,
    project_data: List[Dict[str, str]],
) -> bytes:
    """
    Fills DOCX templates with generated text and converts to a PDF.

    Args:
        resume_template_path: Path to the main resume .docx template.
        project_template_path: Path to the project section .docx template.
        summary_text: The generated professional summary text.
        project_data: A list of dicts, each with 'title' and 'rewritten_text'.

    Returns:
        The generated PDF file as a byte string.
    """
    main_doc = Document(resume_template_path)

    # Replace summary placeholder
    for p in main_doc.paragraphs:
        if "[SUMMARY]" in p.text:
            p.text = p.text.replace("[SUMMARY]", summary_text)

    # Fill and append project templates
    for project in project_data:
        project_doc = Document(project_template_path)
        for p in project_doc.paragraphs:
            if "[PROJECT TITLE]" in p.text:
                p.text = p.text.replace("[PROJECT TITLE]", project["title"])
            if "[PROJECT BULLET POINTS]" in p.text:
                p.text = p.text.replace("[PROJECT BULLET POINTS]", project["rewritten_text"])
        
        # Add a paragraph break before appending the next project
        main_doc.add_paragraph()
        _append_project_to_document(main_doc, project_doc)

    # Save to an in-memory buffer and convert to PDF
    docx_buffer = io.BytesIO()
    main_doc.save(docx_buffer)
    docx_buffer.seek(0)

    pdf_buffer = io.BytesIO()
    convert(docx_buffer, pdf_buffer)
    pdf_buffer.seek(0)
    
    return pdf_buffer.read()


def create_cover_letter_pdf(
    template_path: str, intro: str, body: str, conclusion: str
) -> bytes:
    """
    Fills the cover letter template with generated text and converts to PDF.

    Args:
        template_path: Path to the cover letter .docx template.
        intro: The generated introduction text.
        body: The generated body paragraphs.
        conclusion: The generated conclusion text.

    Returns:
        The generated PDF file as a byte string.
    """
    doc = Document(template_path)
    
    placeholders = {
        "[INTRODUCTION]": intro,
        "[BODY]": body,
        "[CONCLUSION]": conclusion,
    }

    for p in doc.paragraphs:
        for placeholder, text in placeholders.items():
            if placeholder in p.text:
                p.text = p.text.replace(placeholder, text)

    # Save to an in-memory buffer and convert to PDF
    docx_buffer = io.BytesIO()
    doc.save(docx_buffer)
    docx_buffer.seek(0)

    pdf_buffer = io.BytesIO()
    convert(docx_buffer, pdf_buffer)
    pdf_buffer.seek(0)
    
    return pdf_buffer.read() 