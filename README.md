# Automated Application Co-Pilot

## Vision
The Automated Application Co-Pilot is a personal assistant that removes the busy-work from internship and co-op applications.  It automatically scouts new postings, crafts role-specific resumes & cover letters with generative AI, and can even submit the application on your behalf – all from a single web dashboard.

By turning a multi-hour chore into a few button-clicks, the Co-Pilot lets you focus on interview preparation and skill-building instead of formatting documents and filling portals.

---

## Current Status
| Area | Module / Folder | Status |
|------|-----------------|--------|
| Resume & Cover-letter generation | `CV_Agent/` | **✅  Legacy** – fully-functional Streamlit MVP generates tailored PDFs. See `CV_Agent/README.md` for details. |
| University job-board scraper (shortlist) | `Job_Scraper_shortlist/` | **✅ Complete** |
| University portal auto-apply agent | `Portal_Application/` | **✅ Complete** |
| Prompt engineering & Resume/Cover-letter update | `CV_Agent/core/` | **✅ Complete** – Enhanced prompts, improved AI output quality, refined document generation |
| Resume & Cover-letter generation rewrite/refactor | _planned_ | **In Progress** |
| University job-board scraper (full) | `Job_Scraper_full/` | **In Progress** |
| Integration of Scraper & Application Agent | _planned_ | ⏳ Not started |
| External job-board auto-apply agent | _planned_ | ⏳ Not started |
| External job-board scraper | _optional_ | ⏳ Not started |
| React + FastAPI full-stack UI | _planned_ | ⏳ Not started |
| Web search enrichment for CV agent | _optional_ | ⏳ Not started |

---

## Roadmap
1. **Resume & Cover-letter Generation Rewrite/Refactor**
   • Refactor existing resume and cover letter generation for improved modularity and maintainability.
   • Implement new advanced AI models and techniques for generation.
   • Ensure seamless integration with the updated LangGraph workflow.
2. **Integration Stage**
   • Combine completed steps into a unified workflow
   • Ensure smooth data flow between scraper and application agent
3. **External Job-Board Auto-Apply Agent**
   • Implement automated application submission for external job boards
   • Handle diverse application forms and flows
4. **Front-end Rewrite** (React) & **Back-end API** (FastAPI or Django)  
   • Replace Streamlit dashboard  
   • Provide OAuth-protected REST/WS endpoints  
   • Real-time PDF preview via WebSockets
5. **External Integrations**  
   • LinkedIn / Indeed Scraper  
6. **Quality-of-Life**  
   • LLM-powered web search to enrich project bullet points  
   • Cloud deployment scripts (Docker + CI/CD)

---

## Repository Structure
```
├── CV_Agent/               # Streamlit MVP for resume & cover-letters
│   ├── core/               # Business logic (parsing, Gemini calls, etc.)
│   └── tests/              # Pytest suite for CV_Agent
├── Job_Scraper_full/       # University job-board scraper (full listings)
├── Job_Scraper_shortlist/  # University job-board scraper (shortlisted jobs)
├── Portal_Application/     # University portal auto-apply agent
├── jobs/                   # Scraped job details and IDs
├── .github/                # CI workflows (future)
├── requirements.txt        # Python dependencies for all modules
└── README.md               # You are here
```

---

## Tech Stack
* **Python 3.11**  
* **LangGraph, LangChain, Vertex AI Gemini** – language generation & orchestration  
* **Streamlit** – current MVP UI  
* **React + Vite (planned)** – next-gen dashboard  
* **FastAPI / Django (planned)** – REST & WebSocket back-end  

---

## Quick Start
1. **Clone & enter repo**
```bash
git clone <YOUR_FORK_URL>
cd LangGraph-AI-Application-Agent-Gemini
```
2. **Create & activate venv**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```
3. **Install dependencies**
```bash
pip install -r requirements.txt
```
4. **Run the CV Agent MVP**
```bash
cd CV_Agent
streamlit run main_app.py
```
Detailed instructions, template setup, and environment variables are covered in `CV_Agent/README.md`.

---




