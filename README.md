# AI-Powered Resume & Cover Letter Generator

An intelligent application that uses **LangGraph** and **Google Gemini AI** to automatically generate tailored resumes and cover letters based on job descriptions. Built with a modern Streamlit interface, this tool analyzes your master resume and creates customized application documents that highlight the most relevant skills and experiences for each specific role.

## Key Features

- **AI-Powered Content Generation**: Uses Google Gemini 2.0 Flash to intelligently rewrite resume sections and generate cover letters
- **Smart Project Selection**: RAG-powered system automatically selects the most relevant projects from your master resume
- **Interactive Editing**: Real-time content editing with immediate regeneration capabilities
- **Length Optimization**: Automatic resume length checking with AI-powered shortening when needed
- **Professional Formatting**: Generates polished PDF documents using predefined templates
- **Streamlit UI**: Clean, intuitive web interface with step-by-step workflow

## Architecture

The application is built using **LangGraph** to orchestrate a multi-agent workflow:

- **Project Selector Agent**: Identifies most relevant projects using vector similarity search
- **Summary Generator Agent**: Creates tailored professional summaries
- **Project Rewriter Agent**: Rewrites project descriptions with job-specific keywords
- **Cover Letter Agents**: Generate introduction, body, and conclusion sections
- **Length Monitor Agent**: Ensures resume fits within optimal length constraints

## Tech Stack

- **Framework**: Streamlit for web interface
- **AI/ML**: LangChain, LangGraph, Google Gemini 2.0 Flash
- **Document Processing**: PyPDF, python-docx, docx2pdf
- **Vector Store**: FAISS for RAG retrieval
- **Environment**: python-dotenv for configuration

## Setup & Installation

### Prerequisites

- Python 3.8+
- Google Gemini API key

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

4. **Configure API Key**
   Create a `.env` file in the project root:
   ```
   GOOGLE_API_KEY=your_google_gemini_api_key_here
   ```

5. **Run the application**
   ```bash
   streamlit run main_app.py
   ```

## Usage

### 1. Document Upload
- Upload your master resume (PDF format)
- Upload the target job description (PDF format)

### 2. Resume Studio
- AI automatically selects relevant projects and generates tailored content
- Review and edit the generated professional summary
- Modify project descriptions with real-time regeneration
- Handle length optimization if resume exceeds recommended limits

### 3. Cover Letter Studio  
- Review AI-generated introduction and conclusion
- Edit and regenerate cover letter body paragraphs
- Provide feedback for content refinement

### 4. Download & Finalize
- Download professional PDF documents
- Both resume and cover letter are formatted and ready for submission

## Project Structure

```
├── core/
│   ├── agents.py          # AI agent implementations
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

## Important Notes

- **Rate Limiting**: Built-in rate limiter respects Google Gemini API limits (15 RPM)
- **Templates Required**: Ensure you have proper DOCX templates for resume and cover letter formatting
- **Virtual Environment**: Always use the project's virtual environment for dependency isolation

## Contributing

This project follows structured development practices:
- Incremental feature development with planning
- Comprehensive testing after each module
- Clean, documented code with type hints
- PEP 8 compliance and professional naming conventions