# AI-Powered Resume & Cover Letter Generator

An intelligent application that uses **LangGraph**, **Google Gemini AI**, and **Deepseek AI** to automatically generate tailored resumes and cover letters based on job descriptions. Built with a modern Streamlit interface, this tool analyzes your master resume and creates customized application documents that highlight the most relevant skills and experiences for each specific role.

## Key Features

- **AI-Powered Content Generation**: Uses Google Gemini 2.0 Flash and Deepseek Reasoner to intelligently rewrite resume sections and generate cover letters
- **Smart Project Selection**: RAG-powered system automatically selects the most relevant projects from your master resume
- **Interactive Editing**: Real-time content editing with immediate regeneration capabilities and user feedback loops for both resume and cover letter sections
- **Length Optimization**: Automatic resume and cover letter length checking with AI-powered shortening/expansion when needed
- **Professional Formatting**: Generates polished PDF documents using predefined templates
- **Streamlit UI**: Clean, intuitive web interface with step-by-step workflow

## Architecture

The application is built using **LangGraph** to orchestrate a multi-agent workflow for document generation and refinement. Key components include:

- **Document Ingestion**: Processes master resume and job descriptions.
- **Resume Generation Agents**: Selects projects, generates summaries, and rewrites project descriptions.
- **Cover Letter Generation Agents**: Generates compelling introductions, body paragraphs, and conclusions, leveraging different LLMs for specialized tasks.
- **Length Optimization Agents**: Monitors and adjusts document length to fit page constraints.
- **Feedback Loop**: Integrates user feedback for iterative content refinement.

## Tech Stack

- **Framework**: Streamlit for web interface
- **AI/ML**: LangChain, LangGraph, Google Gemini 2.0 Flash, Deepseek Reasoner
- **Document Processing**: PyPDF, python-docx, docx2pdf
- **Vector Store**: FAISS for RAG retrieval
- **Environment**: python-dotenv for configuration

## Setup & Installation

### Prerequisites

- Python 3.8+
- Google Gemini API key
- Deepseek API key

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd LangGraph-AI-Application-Agent-Gemini
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure API Keys**
   Create a `.env` file in the project root:
   ```
   GOOGLE_API_KEY=your_google_gemini_api_key_here
   DEEPSEEK_API_KEY=your_deepseek_api_key_here
   ```

5. **Run the application**
   ```bash
   streamlit run main_app.py
   ```

## Usage

This section describes the current workflow for the **Prompt Engineering & Resume/Cover-letter Generation Update** stage. The original Resume & Cover-letter generation is now considered **Legacy**.

### 1. Document Upload
- Upload your master resume (PDF format)
- Upload the target job description (PDF format)

### 2. Resume Studio
- AI automatically selects relevant projects and generates tailored content
- Review and edit the generated professional summary
- Modify project descriptions with real-time regeneration
- Handle length optimization if resume exceeds recommended limits

### 3. Cover Letter Studio  
- **New Workflow**: AI first generates the introduction and conclusion using Deepseek AI.
- Users can provide feedback to regenerate these sections.
- After satisfaction, proceed to body generation (using Gemini AI).
- The body is length-checked and can be regenerated with feedback.
- PDF previews are available at each stage.

### 4. Download & Finalize
- Download professional PDF documents
- Both resume and cover letter are formatted and ready for submission

## Project Structure

```
├── core/
│   ├── agents.py          # Legacy AI agent implementations for original CL flow
│   ├── resume_agent.py    # AI agents for resume generation and optimization
│   ├── cover_letter_agent.py # New AI agents for enhanced cover letter generation and optimization
│   ├── graph.py           # LangGraph workflow definition  
│   ├── ingestion.py       # PDF parsing and text extraction
│   ├── rag_setup.py       # Vector store and retrieval setup
│   └── doc_generator.py   # PDF generation from templates
├── tests/                 # Comprehensive test suite
├── main_app.py           # Streamlit application entry point
├── requirements.txt      # Python dependencies
└── README.md            # Project documentation
```

## Testing

Run the test suite to ensure everything is working correctly:

```bash
pytest tests/
```

The project includes comprehensive tests covering:
- Document ingestion and parsing
- AI agent functionality
- Graph workflow execution
- PDF generation
- Integration testing

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_API_KEY` | Google Gemini API key for AI operations | Yes |
| `DEEPSEEK_API_KEY` | Deepseek API key for specific AI operations | Yes |

## Important Notes

- **Rate Limiting**: Built-in rate limiter respects API limits (15 RPM for Gemini, check Deepseek limits if applicable)
- **Templates Required**: Ensure you have proper DOCX templates for resume and cover letter formatting
- **Virtual Environment**: Always use the project's virtual environment for dependency isolation

## Contributing

This project follows structured development practices:
- Incremental feature development with planning
- Comprehensive testing after each module
- Clean, documented code with type hints
- PEP 8 compliance and professional naming conventions