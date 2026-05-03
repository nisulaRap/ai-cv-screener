# AI CV Screener - Multi-Agent System

An intelligent CV screening system powered by AI agents that automates the process of parsing, matching, ranking, and generating reports for job candidates.

## Features

- **Automated CV Parsing**: Extract key information from PDF, DOCX, and TXT CVs
- **Job Matching**: AI-powered matching of candidate skills against job requirements
- **Intelligent Ranking**: Automatic ranking and shortlisting of candidates
- **Report Generation**: Professional HTML reports with executive summaries
- **Web Dashboard**: Modern, responsive frontend for easy interaction
- **Multi-Agent Architecture**: Built with LangGraph for robust, sequential processing

## Architecture

The system uses a 4-agent pipeline built with LangGraph:

1. **Parser Agent**: Reads and extracts information from CV files
2. **Job Matcher Agent**: Scores candidates based on job requirements
3. **Candidate Ranker Agent**: Sorts and labels candidates (Shortlisted/Rejected)
4. **Report Generator Agent**: Creates professional HTML reports

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Parser    │ →  │   Job       │ →  │  Candidate  │ →  │   Report    │
│   Agent     │    │   Matcher   │    │  Ranker     │    │  Generator  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

## Prerequisites

- Python 3.9 or higher
- Node.js (optional, for development)
- Ollama (for local LLM inference)

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/nisulaRap/ai-cv-screener.git
   cd ai-cv-screener
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```env
   # Ollama configuration (if using local LLM)
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama2
   
   # Or use OpenAI
   OPENAI_API_KEY=your_api_key_here
   ```

## Quick Start

### Running the Backend Server

Start the FastAPI server:
```bash
python server.py
```

The application will be available at `http://localhost:8000`

### Using the Web Interface

1. Open your browser and navigate to `http://localhost:8000`
2. Navigate to the **Job Description** page to configure the position
3. Go to the **Upload CVs** page to upload candidate CVs (PDF, DOCX, or TXT)
4. Click **Run Pipeline** to start the screening process
5. View results in the **Results** or **Dashboard** pages

### Running the Pipeline via CLI

You can also run the pipeline directly from the command line:

```bash
python main.py --job data/job_description.json --cvs data/cvs
```

## Project Structure

```
ai-cv-screener/
├── agents/                 # AI agent implementations
│   ├── parser_agent.py     # CV parsing agent
│   ├── job_matcher_agent.py # Job matching agent
│   ├── ranker_agent.py     # Candidate ranking agent
│   └── report_generator.py # Report generation agent
├── frontend/               # Web interface
│   ├── index.html          # Main HTML page
│   └── static/             # CSS and JavaScript files
├── data/                   # Data directory
│   ├── job_description.json # Default job description
│   ├── cvs/                # CV files directory
│   └── uploads/            # Uploaded files
├── tools/                  # Utility tools
├── utils/                  # Helper utilities
├── tests/                  # Unit tests
├── server.py               # FastAPI server
├── main.py                 # CLI entry point
└── requirements.txt        # Python dependencies
```

## API Endpoints

The application provides the following REST API endpoints:

### Job Description
- `POST /api/job-description` - Create/save a job description
- `GET /api/job-description/{job_id}` - Retrieve a job description

### CV Upload
- `POST /api/upload-cv` - Upload a single CV file
- `POST /api/upload-cvs/batch` - Upload multiple CVs
- `DELETE /api/clear-uploads` - Clear all uploaded files

### Pipeline
- `POST /api/run-pipeline` - Start the screening pipeline
- `GET /api/run-status/{run_id}` - Get pipeline run status
- `GET /api/runs` - List all pipeline runs

### Results
- `GET /api/candidates/{run_id}` - Get ranked candidates for a run
- `GET /api/report/{run_id}` - Get generated HTML report

## Configuration

### Job Description Format

Create a `data/job_description.json` file with the following structure:

```json
{
  "job_id": "job_001",
  "title": "Senior Python Developer",
  "required_skills": ["Python", "REST APIs", "SQL", "Git"],
  "preferred_skills": ["FastAPI", "Docker", "PostgreSQL"],
  "min_experience_years": 3.0,
  "education_requirement": "Bachelor's degree in Computer Science",
  "description": "We are looking for a Senior Python Developer..."
}
```

### Supported CV Formats

- PDF (.pdf)
- Microsoft Word (.docx)
- Plain Text (.txt)

## Testing

Run the test suite:

```bash
python -m pytest tests/ -v
```


