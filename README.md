# App-Builder AI 🚀

https://app-builder-ai.streamlit.app/
An intelligent code generation platform that transforms natural language descriptions into production-ready applications using multi-agent AI architecture.

## Overview

App-Builder AI leverages advanced Large Language Models (LLMs) and a sophisticated multi-agent system to automatically generate complete, functional applications from simple text prompts. Built with LangChain, LangGraph, and Streamlit, it provides an intuitive interface for developers and non-developers alike to create web applications, APIs, and more.

## Key Features

- **Natural Language to Code**: Describe your project in plain English and watch it come to life
- **Multi-Agent Architecture**: Specialized AI agents for planning, architecture, and code generation
- **Real-Time Preview**: Live preview of generated web applications
- **Complete Project Generation**: Creates full project structures with all necessary files
- **Export Functionality**: Download generated projects as ZIP files
- **Syntax Highlighting**: Built-in code viewer with language-specific highlighting
- **Modern UI**: Sleek, gradient-based interface with glassmorphic design elements

## Tech Stack

- **Backend Framework**: Python 3.11+
- **AI Orchestration**: LangChain & LangGraph
- **LLM Provider**: Groq API (GPT-OSS-120B model)
- **Frontend**: Streamlit with custom CSS
- **File Management**: Python pathlib, zipfile
- **Environment Management**: python-dotenv

## Installation

### Prerequisites

- Python 3.11 or higher
- Groq API key

### Setup Steps

1. **Clone the repository:**
```bash
git clone https://github.com/parvath-reddy/App-Builder-AI.git
cd App-Builder-AI
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables:**
Create a `.env` file in the root directory:
```env
GROQ_API_KEY=your_groq_api_key_here
```

5. **Run the application:**
```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`

## Architecture

### Multi-Agent System

1. **Planner Agent**: Analyzes user requirements and creates a structured project plan
   - Extracts project requirements
   - Identifies necessary tech stack
   - Defines project features and files

2. **Architect Agent**: Transforms the plan into detailed implementation tasks
   - Breaks down the project into specific coding tasks
   - Establishes dependencies between components
   - Orders tasks for optimal implementation

3. **Coder Agent**: Executes the implementation tasks
   - Generates actual code files
   - Maintains consistency across the project
   - Integrates all components

### Project Structure

```
App-Builder-AI/
├── agent/
│   ├── __init__.py
│   ├── graph.py          # LangGraph workflow orchestration
│   ├── prompts.py        # Agent system prompts
│   ├── states.py         # Pydantic models for state management
│   └── tools.py          # File system operations tools
├── generated_project/    # Output directory for generated code
├── app.py               # Streamlit web interface
├── main.py              # CLI interface
├── requirements.txt     # Project dependencies
├── .env                 # Environment variables (not in repo)
└── README.md           # This file
```

## Usage

### Web Interface

1. **Describe Your Project**: Enter a natural language description in the chat interface
   - Example: "Build a modern todo app with React and Tailwind CSS"
   
2. **Generation Process**: Watch real-time progress as the AI:
   - Analyzes requirements
   - Creates architecture
   - Generates code
   - Implements features

3. **Preview & Export**:
   - View live preview for web applications
   - Browse generated files with syntax highlighting
   - Download individual files or complete project as ZIP

### Command Line Interface

```bash
python main.py --recursion-limit 100
```

Enter your project prompt when prompted, and the system will generate the project in the `generated_project/` directory.

## Example Prompts

- "Create a responsive portfolio website with HTML, CSS, and JavaScript"
- "Build a REST API with Flask for a blog application with user authentication"
- "Generate a React dashboard with charts and data visualization"
- "Create a Python script for web scraping with BeautifulSoup"
- "Build a real-time chat application using WebSocket"

## Requirements

```txt
groq>=0.31.0
langchain>=0.3.27
langchain-core>=0.3.72
langchain-groq>=0.3.7
langgraph>=0.6.3
streamlit>=1.32.0
python-dotenv>=1.1.1
pydantic>=2.11.7
```

## Configuration

### Recursion Limit
Adjust the recursion limit for complex projects (default: 50 for web, 100 for CLI):
- Higher values allow more complex projects but may increase generation time
- Lower values provide faster results for simpler projects

### API Configuration
The system uses Groq's API with the `openai/gpt-oss-120b` model. Ensure your API key has sufficient quota for your usage.

## Limitations

- Generated code quality depends on prompt clarity and specificity
- Complex enterprise applications may require manual refinement
- API rate limits may affect generation speed
- Large projects may exceed token limits

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.


## Acknowledgments

- LangChain and LangGraph teams for the excellent AI orchestration framework
- Groq for providing powerful LLM capabilities
- Streamlit for the intuitive web framework
