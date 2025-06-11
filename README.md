# Automated Application Co-Pilot

## Vision
The Automated Application Co-Pilot is a personal assistant that removes the busy-work from internship and co-op applications.  It automatically scouts new postings, crafts role-specific resumes & cover letters with generative AI, and can even submit the application on your behalf – all from a single web dashboard.

By turning a multi-hour chore into a few button-clicks, the Co-Pilot lets you focus on interview preparation and skill-building instead of formatting documents and filling portals.

---

## Current Status
| Area | Module / Folder | Status |
|------|-----------------|--------|
| Resume & Cover-letter generation | `CV_Agent/` | **✅  Complete** – fully-functional Streamlit MVP generates tailored PDFs.  See `CV_Agent/README.md` for details. |
| University job-board scraper | `Job_Scraper/` | 🛠  In progress |
| University portal auto-apply agent | _planned_ | ⏳ Not started |
| External job-board auto-apply agent | _planned_ | ⏳ Not started |
| External job-board scraper | _optional_ | ⏳ Not started |
| React + FastAPI full-stack UI | _planned_ | ⏳ Not started |
| Web search enrichment for CV agent | _optional_ | ⏳ Not started |

---

## Roadmap
1. **Finish Job_Scraper**  
   • Log-in to university career portal  
   • Persist new postings to `Input-Documents/Job-Descriptions`  
   • Deduplicate previously-saved postings
2. **University Portal Application Agent**  
   • Navigate to posting  
   • Upload AI-generated resume + cover letter  
   • Expose progress/events over API to UI
3. **Front-end Rewrite** (React) & **Back-end API** (FastAPI or Django)  
   • Replace Streamlit dashboard  
   • Provide OAuth-protected REST/WS endpoints  
   • Real-time PDF preview via WebSockets
4. **External Integrations**  
   • LinkedIn / Indeed Scraper  
   • Generic website apply-bot w/ form autofill
5. **Quality-of-Life**  
   • LLM-powered web search to enrich project bullet points  
   • Cloud deployment scripts (Docker + CI/CD)

---

## Repository Structure
```
├── CV_Agent/           # Streamlit MVP for resume & cover-letters
│   ├── core/           # Business logic (parsing, Gemini calls, etc.)
│   └── tests/          # Pytest suite for CV_Agent
├── Job_Scraper/        # (WIP) University job-board crawler
├── .github/            # CI workflows (future)
├── requirements.txt    # Python dependencies for all modules
└── README.md           # You are here
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




