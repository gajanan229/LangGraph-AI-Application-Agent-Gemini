import os
import streamlit as st
import base64
from core.ingestion import parse_master_resume, parse_pdf
from core.rag_setup import setup_rag_pipeline
from core.graph import create_application_graph, GraphState
from core.doc_generator import create_resume_pdf

st.set_page_config(layout="wide")

# --- Caching the Graph ---
@st.cache_resource
def get_app_graph():
    """Builds and caches the LangGraph application."""
    return create_application_graph()

# --- Main App Logic ---
st.title("Automated Application Co-Pilot")

# Initialize session state keys
default_keys = {
    "uploaded_resume_bytes": None,
    "uploaded_jd_bytes": None,
    "structured_resume": None,
    "job_description_text": None,
    "rag_retrievers": None,
    "resume_generated": False,
    "generated_summary": "",
    "generated_projects": {},
}
for key, value in default_keys.items():
    if key not in st.session_state:
        st.session_state[key] = value

# --- UI FOR FILE UPLOAD ---
if not st.session_state.resume_generated:
    st.header("1. Upload Your Documents")
    col1, col2 = st.columns(2)
    with col1:
        IS_DEV_MODE = True
        if IS_DEV_MODE and not st.session_state.structured_resume:
            st.info("Dev Mode: Loading sample resume.")
            try:
                resume_path = os.path.join("Input-Documents", "Master_Resume.pdf")
                with open(resume_path, "rb") as f:
                    st.session_state.uploaded_resume_bytes = f.read()
            except FileNotFoundError:
                st.error(f"Sample resume not found at '{resume_path}'.")
        else:
            uploaded_resume = st.file_uploader("Upload Master Resume (PDF)", type=["pdf"])
            if uploaded_resume:
                st.session_state.uploaded_resume_bytes = uploaded_resume.getvalue()

    with col2:
        if IS_DEV_MODE and not st.session_state.structured_resume:
            st.info("Dev Mode: Loading sample JD.")
            try:
                jd_path = os.path.join("Input-Documents", "job description.pdf")
                with open(jd_path, "rb") as f:
                    st.session_state.uploaded_jd_bytes = f.read()
            except FileNotFoundError:
                st.error(f"Sample JD not found at '{jd_path}'.")
        else:
            uploaded_jd = st.file_uploader("Upload Job Description (PDF)", type=["pdf"])
            if uploaded_jd:
                st.session_state.uploaded_jd_bytes = uploaded_jd.getvalue()

    if st.session_state.uploaded_resume_bytes and st.session_state.uploaded_jd_bytes:
        st.success("Documents Loaded.")
        if st.button("Step 1: Parse Documents & Build RAG", disabled=st.session_state.rag_retrievers is not None):
            with st.spinner("Processing documents..."):
                # Parse
                resume_text = parse_pdf(st.session_state.uploaded_resume_bytes)
                st.session_state.structured_resume = parse_master_resume(resume_text)
                st.session_state.job_description_text = parse_pdf(st.session_state.uploaded_jd_bytes)
                # Build RAG
                st.session_state.rag_retrievers = setup_rag_pipeline(st.session_state.structured_resume)
            st.rerun()

# --- UI FOR RESUME GENERATION ---
if st.session_state.rag_retrievers and not st.session_state.resume_generated:
    st.header("2. Generate Tailored Resume")
    st.info("The backend is ready. Click the button to run the AI agents and generate the first draft of your tailored resume.")

    if st.button("Step 2: Generate Resume Content"):
        with st.spinner("Running AI agents... This may take a moment."):
            app = get_app_graph()
            initial_state: GraphState = {
                "job_description_text": st.session_state.job_description_text,
                "master_resume_structured": st.session_state.structured_resume,
                "rag_retrievers": st.session_state.rag_retrievers,
                "selected_project_titles": [],
                "generated_resume_summary": "",
                "generated_resume_projects": {},
                # Default empty values for cover letter state
                "generated_cl_intro": "",
                "generated_cl_conclusion": "",
                "generated_cl_body": "",
                "cl_feedback_history": [],
                "user_action": "",
            }
            final_state = app.invoke(initial_state)

            # Store generated content
            st.session_state.generated_summary = final_state["generated_resume_summary"]
            st.session_state.generated_projects = final_state["generated_resume_projects"]
            st.session_state.resume_generated = True
            st.rerun()

# --- UI FOR REVIEW AND EDIT ---
if st.session_state.resume_generated:
    st.header("3. Review and Finalize Your Tailored Resume")
    
    col1, col2 = st.columns([0.4, 0.6]) # Left column for controls, right for preview

    with col1:
        st.subheader("Generated Content")
        st.session_state.generated_summary = st.text_area(
            "Professional Summary", st.session_state.generated_summary, height=150
        )
        
        st.subheader("Tailored Projects")
        for title, text in st.session_state.generated_projects.items():
            st.session_state.generated_projects[title] = st.text_area(
                f"Project: {title}", text, height=150, key=f"proj_{title}"
            )

        if st.button("Update Preview"):
            st.rerun() # Just rerun to trigger the PDF regeneration

    with col2:
        st.subheader("Live PDF Preview")
        with st.spinner("Generating PDF preview..."):
            # Prepare project data for the generator function
            project_data_for_pdf = [
                {"title": title, "rewritten_text": text}
                for title, text in st.session_state.generated_projects.items()
            ]

            pdf_bytes = create_resume_pdf(
                resume_template_path="Templates/resume_template.docx",
                project_template_path="Templates/Project_template.docx",
                summary_text=st.session_state.generated_summary,
                project_data=project_data_for_pdf,
            )
            
            # Display the PDF
            base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)