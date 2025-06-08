import os
import streamlit as st
from core.ingestion import parse_master_resume, parse_pdf
from core.rag_setup import setup_rag_pipeline

st.set_page_config(layout="wide")

st.title("Automated Application Co-Pilot")

# Use session state to prevent file from being re-uploaded on every interaction
if "uploaded_resume_bytes" not in st.session_state:
    st.session_state.uploaded_resume_bytes = None
if "uploaded_jd_bytes" not in st.session_state:
    st.session_state.uploaded_jd_bytes = None

# In development mode, we can auto-load the sample files.
# Set this to False to use the manual uploader.
IS_DEV_MODE = True

# --- UI FOR FILE UPLOAD ---
st.header("1. Upload Your Documents")

col1, col2 = st.columns(2)
with col1:
    if IS_DEV_MODE and not st.session_state.get("resume_parsed"):
        st.info("Dev Mode: Loading sample resume.")
        try:
            resume_path = os.path.join("Input-Documents", "Master_Resume.pdf")
            with open(resume_path, "rb") as f:
                st.session_state.uploaded_resume_bytes = f.read()
        except FileNotFoundError:
            st.error(f"Sample resume not found at '{resume_path}'.")
    else:
        uploaded_resume = st.file_uploader("Upload Your Master Resume (PDF)", type=["pdf"])
        if uploaded_resume:
            st.session_state.uploaded_resume_bytes = uploaded_resume.getvalue()

with col2:
    if IS_DEV_MODE and not st.session_state.get("resume_parsed"):
        st.info("Dev Mode: Loading sample job description.")
        try:
            jd_path = os.path.join("Input-Documents", "job description.pdf")
            with open(jd_path, "rb") as f:
                st.session_state.uploaded_jd_bytes = f.read()
        except FileNotFoundError:
            st.error(f"Sample job description not found at '{jd_path}'.")
    else:
        uploaded_jd = st.file_uploader("Upload Job Description (PDF)", type=["pdf"])
        if uploaded_jd:
            st.session_state.uploaded_jd_bytes = uploaded_jd.getvalue()

# --- UI FOR PARSING AND DISPLAYING RESULTS ---
if st.session_state.uploaded_resume_bytes and st.session_state.uploaded_jd_bytes:
    st.success("Master Resume and Job Description are loaded.")
    
    if "structured_resume" not in st.session_state:
        if st.button("Parse and Analyze Resume"):
            with st.spinner("Parsing PDF and analyzing resume structure..."):
                resume_text = parse_pdf(st.session_state.uploaded_resume_bytes)
                st.session_state.structured_resume = parse_master_resume(resume_text)
                
                jd_text = parse_pdf(st.session_state.uploaded_jd_bytes)
                st.session_state.job_description_text = jd_text
                
                st.session_state.resume_parsed = True
                st.rerun()

# Once parsed, show the structured data and the option to build the RAG pipeline
if "structured_resume" in st.session_state:
    st.header("2. Review Your Parsed Resume")
    st.write("Verify the extracted data below.")
    
    data = st.session_state.structured_resume
    
    with st.expander("View Parsed Resume Data", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Summary & Contact")
            st.text_area("Summary", data.get("summary_and_contact"), height=150)
            st.subheader("Work Experience")
            st.text_area("Experience", data.get("experience"), height=200)
        with col2:
            st.subheader("Skills")
            st.text_area("Skills", data.get("skills"), height=150)
            st.subheader("Education")
            st.text_area("Education", data.get("education"), height=150)
        
        st.subheader("Parsed Projects")
        if data.get("projects"):
            for i, project in enumerate(data.get("projects")):
                st.text_area(f"Project: {project.get('title')}", project.get('description'), height=100, key=f"proj_{i}")
        else:
            st.warning("No projects were parsed from the resume.")

    st.header("3. Build RAG Vector Store")
    if "rag_retrievers" not in st.session_state:
        if st.button("Build Project Vector Store"):
            with st.spinner("Initializing embeddings and building FAISS vector store for projects..."):
                try:
                    rag_retrievers = setup_rag_pipeline(st.session_state.structured_resume)
                    st.session_state.rag_retrievers = rag_retrievers
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to build RAG pipeline: {e}")
    else:
        st.success("Project vector store is ready!")
        st.write("The RAG pipeline has been successfully built. We can now proceed to the agentic generation phase.") 