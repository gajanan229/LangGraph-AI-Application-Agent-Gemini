import os
import streamlit as st
import base64
from core.ingestion import parse_master_resume, parse_pdf
from core.rag_setup import setup_rag_pipeline
from core.graph import create_application_graph, GraphState
from core.doc_generator import create_resume_pdf, create_cover_letter_pdf

st.set_page_config(layout="wide", page_title="Automated Application Co-Pilot")

# --- Caching the Graph ---
@st.cache_resource
def get_app_graph():
    """Builds and caches the LangGraph application."""
    return create_application_graph()

# --- Utility Functions ---
def display_pdf_preview(pdf_bytes, height=600):
    """Displays a PDF in an iframe."""
    base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="{height}" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

def reset_workflow():
    """Resets the workflow to start over."""
    keys_to_reset = [
        "ui_stage", "resume_generated", "cover_letter_generated", 
        "generated_summary", "generated_projects", "generated_cl_intro",
        "generated_cl_body", "generated_cl_conclusion", "final_resume_pdf",
        "final_cover_letter_pdf"
    ]
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

# --- Main App Logic ---
st.title("🚀 Automated Application Co-Pilot")
st.markdown("*Generate tailored resumes and cover letters using AI*")

# Initialize session state keys
default_keys = {
    "ui_stage": "upload",  # upload, resume_studio, cover_letter_studio, finalization
    "uploaded_resume_bytes": None,
    "uploaded_jd_bytes": None,
    "structured_resume": None,
    "job_description_text": None,
    "rag_retrievers": None,
    "resume_generated": False,
    "cover_letter_generated": False,
    "generated_summary": "",
    "generated_projects": {},
    "generated_cl_intro": "",
    "generated_cl_body": "",
    "generated_cl_conclusion": "",
    "cl_feedback_history": [],
    "final_resume_pdf": None,
    "final_cover_letter_pdf": None,
}
for key, value in default_keys.items():
    if key not in st.session_state:
        st.session_state[key] = value

# Progress indicator
stage_map = {
    "upload": 1,
    "resume_studio": 2, 
    "cover_letter_studio": 3,
    "finalization": 4
}
current_stage = stage_map.get(st.session_state.ui_stage, 1)
st.progress(current_stage / 4)

# Stage indicator
stages = ["📄 Document Upload", "📝 Resume Studio", "💌 Cover Letter Studio", "📥 Download & Finalize"]
stage_cols = st.columns(4)
for i, (col, stage_name) in enumerate(zip(stage_cols, stages)):
    with col:
        if i + 1 == current_stage:
            st.markdown(f"**🔹 {stage_name}**")
        elif i + 1 < current_stage:
            st.markdown(f"✅ {stage_name}")
        else:
            st.markdown(f"⚪ {stage_name}")

st.divider()

# --- STAGE 1: DOCUMENT UPLOAD ---
if st.session_state.ui_stage == "upload":
    st.header("📄 Step 1: Upload Your Documents")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Master Resume")
        IS_DEV_MODE = True
        if IS_DEV_MODE and not st.session_state.structured_resume:
            st.info("🔧 Dev Mode: Loading sample resume.")
            try:
                resume_path = os.path.join("Input-Documents", "Master_Resume.pdf")
                with open(resume_path, "rb") as f:
                    st.session_state.uploaded_resume_bytes = f.read()
                st.success("Sample resume loaded!")
            except FileNotFoundError:
                st.error(f"Sample resume not found at '{resume_path}'.")
        else:
            uploaded_resume = st.file_uploader("Upload Master Resume (PDF)", type=["pdf"], key="resume_upload")
            if uploaded_resume:
                st.session_state.uploaded_resume_bytes = uploaded_resume.getvalue()
                st.success("Resume uploaded!")

    with col2:
        st.subheader("Job Description")
        if IS_DEV_MODE and not st.session_state.structured_resume:
            st.info("🔧 Dev Mode: Loading sample job description.")
            try:
                jd_path = os.path.join("Input-Documents", "job description.pdf")
                with open(jd_path, "rb") as f:
                    st.session_state.uploaded_jd_bytes = f.read()
                st.success("Sample job description loaded!")
            except FileNotFoundError:
                st.error(f"Sample JD not found at '{jd_path}'.")
        else:
            uploaded_jd = st.file_uploader("Upload Job Description (PDF)", type=["pdf"], key="jd_upload")
            if uploaded_jd:
                st.session_state.uploaded_jd_bytes = uploaded_jd.getvalue()
                st.success("Job description uploaded!")

    if st.session_state.uploaded_resume_bytes and st.session_state.uploaded_jd_bytes:
        st.success("✅ All documents loaded successfully!")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔄 Process Documents & Start AI Analysis", 
                        disabled=st.session_state.rag_retrievers is not None,
                        type="primary"):
                with st.spinner("🧠 Processing documents and building AI pipeline..."):
                    # Parse documents
                    resume_text = parse_pdf(st.session_state.uploaded_resume_bytes)
                    st.session_state.structured_resume = parse_master_resume(resume_text)
                    st.session_state.job_description_text = parse_pdf(st.session_state.uploaded_jd_bytes)
                    
                    # Build RAG pipeline
                    st.session_state.rag_retrievers = setup_rag_pipeline(st.session_state.structured_resume)
                    
                    # Advance to next stage
                    st.session_state.ui_stage = "resume_studio"
                st.rerun()

# --- STAGE 2: RESUME STUDIO ---
elif st.session_state.ui_stage == "resume_studio":
    st.header("📝 Step 2: Resume Studio")
    
    if not st.session_state.resume_generated:
        st.info("🤖 Ready to generate your tailored resume using AI agents!")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("✨ Generate Resume Content", type="primary"):
                with st.spinner("🤖 AI agents are analyzing and generating content..."):
                    app = get_app_graph()
                    initial_state: GraphState = {
                        "job_description_text": st.session_state.job_description_text,
                        "master_resume_structured": st.session_state.structured_resume,
                        "rag_retrievers": st.session_state.rag_retrievers,
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

                    # Store generated content
                    st.session_state.generated_summary = final_state["generated_resume_summary"]
                    st.session_state.generated_projects = final_state["generated_resume_projects"]
                    st.session_state.generated_cl_intro = final_state["generated_cl_intro"]
                    st.session_state.generated_cl_body = final_state["generated_cl_body"]
                    st.session_state.generated_cl_conclusion = final_state["generated_cl_conclusion"]
                    st.session_state.resume_generated = True
                    st.session_state.cover_letter_generated = True
                st.rerun()
    
    if st.session_state.resume_generated:
        col1, col2 = st.columns([0.4, 0.6])
        
        with col1:
            st.subheader("📝 Generated Content")
            
            # Editable summary
            st.session_state.generated_summary = st.text_area(
                "Professional Summary", 
                st.session_state.generated_summary, 
                height=150,
                help="Edit the summary to better match your style"
            )
            
            # Editable projects
            st.subheader("🚀 Tailored Projects")
            for title, text in st.session_state.generated_projects.items():
                st.session_state.generated_projects[title] = st.text_area(
                    f"Project: {title}", 
                    text, 
                    height=150, 
                    key=f"proj_{title}",
                    help="Edit the project description to highlight specific achievements"
                )

            # Action buttons
            col1_1, col1_2 = st.columns(2)
            with col1_1:
                if st.button("🔄 Update Preview"):
                    st.rerun()
            with col1_2:
                if st.button("➡️ Proceed to Cover Letter", type="primary"):
                    st.session_state.ui_stage = "cover_letter_studio"
                    st.rerun()

        with col2:
            st.subheader("📄 Live Resume Preview")
            with st.spinner("📄 Generating PDF preview..."):
                # Prepare project data for the generator function
                project_data_for_pdf = [
                    {"title": title, "rewritten_text": text}
                    for title, text in st.session_state.generated_projects.items()
                ]

                st.session_state.final_resume_pdf = create_resume_pdf(
                    resume_template_path="Templates/resume_template.docx",
                    project_template_path="Templates/Project_template.docx",
                    summary_text=st.session_state.generated_summary,
                    project_data=project_data_for_pdf,
                )
                
                display_pdf_preview(st.session_state.final_resume_pdf, height=700)

# --- STAGE 3: COVER LETTER STUDIO ---
elif st.session_state.ui_stage == "cover_letter_studio":
    st.header("💌 Step 3: Cover Letter Studio")
    
    col1, col2 = st.columns([0.4, 0.6])
    
    with col1:
        st.subheader("✍️ Cover Letter Sections")
        
        # Editable cover letter sections
        st.session_state.generated_cl_intro = st.text_area(
            "Introduction", 
            st.session_state.generated_cl_intro, 
            height=100,
            help="Opening paragraph that grabs attention"
        )
        
        st.session_state.generated_cl_body = st.text_area(
            "Body Paragraphs", 
            st.session_state.generated_cl_body, 
            height=200,
            help="Main content connecting your experience to the role"
        )
        
        st.session_state.generated_cl_conclusion = st.text_area(
            "Conclusion", 
            st.session_state.generated_cl_conclusion, 
            height=100,
            help="Strong closing with call to action"
        )
        
        # Feedback and regeneration
        st.subheader("🔄 Regeneration Options")
        feedback_text = st.text_area(
            "Feedback for AI (Optional)", 
            placeholder="e.g., 'Make it more technical', 'Focus on leadership experience', 'Add more enthusiasm'",
            height=80
        )
        
        # Action buttons
        col1_1, col1_2 = st.columns(2)
        with col1_1:
            if st.button("🔄 Update Preview"):
                st.rerun()
            if st.button("🤖 Regenerate with Feedback") and feedback_text.strip():
                with st.spinner("🤖 Regenerating cover letter..."):
                    # Add feedback to history
                    st.session_state.cl_feedback_history.append(feedback_text.strip())
                    
                    # Create new state for regeneration
                    app = get_app_graph()
                    regen_state: GraphState = {
                        "job_description_text": st.session_state.job_description_text,
                        "master_resume_structured": st.session_state.structured_resume,
                        "rag_retrievers": st.session_state.rag_retrievers,
                        "selected_project_titles": list(st.session_state.generated_projects.keys()),
                        "generated_resume_summary": st.session_state.generated_summary,
                        "generated_resume_projects": st.session_state.generated_projects,
                        "generated_cl_intro": st.session_state.generated_cl_intro,
                        "generated_cl_conclusion": st.session_state.generated_cl_conclusion,
                        "generated_cl_body": st.session_state.generated_cl_body,
                        "cl_feedback_history": st.session_state.cl_feedback_history,
                        "user_action": "REGENERATE_CL",
                    }
                    
                    final_state = app.invoke(regen_state)
                    
                    # Update with regenerated content
                    st.session_state.generated_cl_intro = final_state["generated_cl_intro"]
                    st.session_state.generated_cl_body = final_state["generated_cl_body"]
                    st.session_state.generated_cl_conclusion = final_state["generated_cl_conclusion"]
                st.rerun()
        
        with col1_2:
            if st.button("✅ Finalize Documents", type="primary"):
                st.session_state.ui_stage = "finalization"
                st.rerun()

    with col2:
        st.subheader("📄 Live Cover Letter Preview")
        with st.spinner("📄 Generating cover letter preview..."):
            st.session_state.final_cover_letter_pdf = create_cover_letter_pdf(
                template_path="Templates/cover_letter_template.docx",
                intro=st.session_state.generated_cl_intro,
                body=st.session_state.generated_cl_body,
                conclusion=st.session_state.generated_cl_conclusion,
            )
            
            display_pdf_preview(st.session_state.final_cover_letter_pdf, height=700)

# --- STAGE 4: FINALIZATION ---
elif st.session_state.ui_stage == "finalization":
    st.header("🎉 Step 4: Download & Finalize")
    st.success("🎯 Congratulations! Your tailored application documents are ready!")
    
    # Final previews
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📄 Final Resume")
        if st.session_state.final_resume_pdf:
            display_pdf_preview(st.session_state.final_resume_pdf, height=500)
            st.download_button(
                "📥 Download Resume",
                data=st.session_state.final_resume_pdf,
                file_name="tailored_resume.pdf",
                mime="application/pdf",
                type="primary"
            )
    
    with col2:
        st.subheader("💌 Final Cover Letter")
        if st.session_state.final_cover_letter_pdf:
            display_pdf_preview(st.session_state.final_cover_letter_pdf, height=500)
            st.download_button(
                "📥 Download Cover Letter",
                data=st.session_state.final_cover_letter_pdf,
                file_name="tailored_cover_letter.pdf",
                mime="application/pdf",
                type="primary"
            )
    
    st.divider()
    
    # Start over option
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Start New Application", type="secondary"):
            reset_workflow()

# Sidebar with helpful information
with st.sidebar:
    st.header("ℹ️ How It Works")
    st.markdown("""
    **Step 1: Upload** 📄
    - Upload your master resume and target job description
    
    **Step 2: Resume Studio** 📝  
    - AI selects relevant projects and rewrites content
    - Edit and refine the generated content
    
    **Step 3: Cover Letter Studio** 💌
    - AI generates personalized cover letter
    - Provide feedback for regeneration
    
    **Step 4: Download** 📥
    - Download your polished documents
    """)
    
    if st.session_state.ui_stage != "upload":
        st.divider()
        if st.button("🔄 Start Over", type="secondary"):
            reset_workflow()