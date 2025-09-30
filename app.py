import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
import time
import json
import sys
import os
from datetime import datetime
import shutil
import zipfile

# Load environment variables safely
from dotenv import load_dotenv
load_dotenv()  # loads .env locally if exists

# Get GROQ API key from environment (local .env or Streamlit secrets)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    st.error("❌ GROQ_API_KEY is missing! Please set it in .env or Streamlit Secrets.")
    st.stop()

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent.graph import agent
from agent.states import Plan, TaskPlan
import threading
import queue

# Import ChatGroq and pass the API key
from langchain_groq.chat_models import ChatGroq

llm = ChatGroq(model="openai/gpt-oss-120b", api_key=GROQ_API_KEY)

# Page configuration
st.set_page_config(
    page_title="APP BUILDER - Intelligent Code Generation Platform",
    page_icon="🧑🏻‍💻",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern UI
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    * { font-family: 'Inter', sans-serif; }

    .stApp { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }

    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        animation: slideDown 0.5s ease-out;
    }

    @keyframes slideDown {
        from { transform: translateY(-20px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }

    .project-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }

    .project-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 40px rgba(0,0,0,0.15);
    }

    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }

    .success-badge { background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%); color: #1a5f3f; }
    .processing-badge { background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%); color: #8b4513; }
    .error-badge { background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%); color: #8b0000; }

    .code-preview {
        background: #1e1e2e;
        color: #cdd6f4;
        padding: 1rem;
        border-radius: 10px;
        overflow-x: auto;
        font-family: 'Monaco', 'Courier New', monospace;
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }

    .feature-card {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        padding: 1rem;
        border-radius: 12px;
        text-align: center;
        transition: all 0.3s ease;
    }

    .feature-card:hover { transform: rotate(2deg) scale(1.05); }

    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 50px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 7px 20px rgba(102, 126, 234, 0.6);
    }

    .loader {
        border: 4px solid #f3f3f3;
        border-top: 4px solid #667eea;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        animation: spin 1s linear infinite;
        margin: 20px auto;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    .glassmorphism {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        padding: 2rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state: st.session_state.messages = []
if 'projects' not in st.session_state: st.session_state.projects = []
if 'current_project' not in st.session_state: st.session_state.current_project = None
if 'generation_status' not in st.session_state: st.session_state.generation_status = None
if 'generated_files' not in st.session_state: st.session_state.generated_files = {}

# --- Helper functions ---
def clean_generated_files():
    project_dir = Path.cwd() / "generated_project"
    if project_dir.exists(): shutil.rmtree(project_dir)
    project_dir.mkdir(exist_ok=True)

def run_agent_async(prompt, result_queue):
    try:
        result = agent.invoke({"user_prompt": prompt}, {"recursion_limit": 50})
        result_queue.put(("success", result))
    except Exception as e:
        result_queue.put(("error", str(e)))

def get_file_content(filepath):
    try:
        project_dir = Path.cwd() / "generated_project"
        file_path = project_dir / filepath
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"
    return "File not found"

def create_preview_html(files):
    if not files: return "<p>No files to preview</p>"
    web_files = {k: v for k, v in files.items() if k.endswith(('.html', '.css', '.js', '.jsx', '.tsx'))}
    if not web_files: return "<p>No web files to preview. Check the file explorer for generated files.</p>"
    html_files = [f for f in web_files.keys() if f.endswith('.html')]
    if html_files:
        main_html = web_files[html_files[0]]
        for filename, content in web_files.items():
            if filename.endswith('.css'): main_html = main_html.replace('</head>', f'<style>{content}</style></head>')
            elif filename.endswith('.js'): main_html = main_html.replace('</body>', f'<script>{content}</script></body>')
        return main_html
    return "<p>Preview not available for this project type</p>"

def export_project():
    project_dir = Path.cwd() / "generated_project"
    if not project_dir.exists(): return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"devstream_project_{timestamp}.zip"
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(project_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(project_dir)
                zipf.write(file_path, arcname)
    return zip_filename

# --- Main App ---
def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; text-align: center; font-size: 3rem; margin-bottom: 0.5rem;">
           📺 App-Builder AI
        </h1>
        <p style="color: rgba(255,255,255,0.9); text-align: center; font-size: 1.2rem;">
            Intelligent Code Generation Platform - Transform Ideas into Production-Ready Applications
        </p>
    </div>
    """, unsafe_allow_html=True)

    # --- Sidebar ---
    with st.sidebar:
        st.markdown("### 🎯 Features")
        features = [("🤖", "AI-Powered", "Advanced LLM Integration"),
                    ("⚡", "Real-time", "Live Code Generation"),
                    ("🎨", "Modern UI", "Beautiful Interfaces"),
                    ("📦", "Export Ready", "Download & Deploy"),
                    ("🔄", "Multi-Agent", "Intelligent Workflow"),
                    ("💻", "Full Stack", "Complete Applications")]
        for icon, title, desc in features:
            st.markdown(f"<div class='feature-card'><div style='font-size:2rem;'>{icon}</div><div style='font-weight:600;margin-top:0.5rem'>{title}</div><div style='font-size:0.85rem;color:#666'>{desc}</div></div>", unsafe_allow_html=True)
            st.markdown("")
        st.markdown("---")
        st.markdown("### 📊 Statistics")
        col1, col2 = st.columns(2)
        with col1: st.metric("Projects", len(st.session_state.projects))
        with col2: st.metric("Files", len(st.session_state.generated_files))
        st.markdown("---")
        st.markdown("### 🛠️ Quick Actions")
        if st.button("🗑️ Clear Workspace", use_container_width=True):
            clean_generated_files()
            st.session_state.generated_files = {}
            st.success("Workspace cleared!")
        if st.session_state.generated_files:
            zip_file = export_project()
            if zip_file:
                with open(zip_file, "rb") as f:
                    st.download_button("📥 Download Project", data=f.read(), file_name=zip_file, mime="application/zip", use_container_width=True)

    # --- Tabs ---
    tab1, tab2, tab3, tab4 = st.tabs(["💬 Chat", "👁️ Live Preview", "📁 File Explorer", "📚 Documentation"])

    # --- Chat tab ---
    with tab1:
        chat_container = st.container()
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        prompt = st.chat_input("Describe your project (e.g., 'Build a modern todo app with React')")
        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.write(prompt)
            with st.chat_message("assistant"):
                status_placeholder = st.empty()
                progress_bar = st.progress(0)
                clean_generated_files()
                status_messages = [("🎯 Analyzing project requirements...", 0.2),
                                   ("🏗️ Creating project architecture...", 0.4),
                                   ("💻 Generating code...", 0.6),
                                   ("🔧 Implementing features...", 0.8),
                                   ("✅ Finalizing project...", 1.0)]
                result_queue = queue.Queue()
                thread = threading.Thread(target=run_agent_async, args=(prompt, result_queue))
                thread.start()
                for msg, progress in status_messages:
                    status_placeholder.markdown(f'<div class="status-badge processing-badge">{msg}</div>', unsafe_allow_html=True)
                    progress_bar.progress(progress)
                    time.sleep(1)
                thread.join(timeout=120)
                if not result_queue.empty():
                    status, result = result_queue.get()
                    if status == "success":
                        project_dir = Path.cwd() / "generated_project"
                        generated_files = {}
                        if project_dir.exists():
                            for file_path in project_dir.rglob("*"):
                                if file_path.is_file():
                                    relative_path = file_path.relative_to(project_dir)
                                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                        generated_files[str(relative_path)] = f.read()
                        st.session_state.generated_files = generated_files
                        plan_info = "Project generated successfully!"
                        if 'plan' in result and result['plan']:
                            plan = result['plan']
                            plan_info = f"### ✅ Project: {plan.name}\n**Description:** {plan.description}\n**Tech Stack:** {plan.techstack}\n**Features:**\n{chr(10).join([f'- {f}' for f in plan.features])}\n**Files Generated:** {len(generated_files)}"
                        status_placeholder.markdown('<div class="status-badge success-badge">✨ Generation Complete!</div>', unsafe_allow_html=True)
                        st.markdown(plan_info)
                        st.session_state.projects.append({"name": plan.name if 'plan' in result else "Project","timestamp": datetime.now(),"files": len(generated_files)})
                        st.session_state.messages.append({"role": "assistant","content": plan_info})
                        st.balloons()
                    else:
                        status_placeholder.markdown(f'<div class="status-badge error-badge">❌ Error: {result}</div>', unsafe_allow_html=True)
                        st.error(f"Generation failed: {result}")
                else:
                    status_placeholder.markdown('<div class="status-badge error-badge">⏱️ Generation timeout</div>', unsafe_allow_html=True)
                    st.error("Generation timed out. Please try with a simpler project.")
                progress_bar.empty()

    # --- Live Preview tab ---
    with tab2:
        st.markdown("### 👁️ Live Preview")
        if st.session_state.generated_files:
            preview_html = create_preview_html(st.session_state.generated_files)
            st.markdown('<div class="glassmorphism"><h4 style="margin-bottom:1rem;">Interactive Preview</h4></div>', unsafe_allow_html=True)
            components.html(preview_html, height=600, scrolling=True)
        else:
            st.info("Generate a project to see the live preview here! 👆")

    # --- File Explorer tab ---
    with tab3:
        st.markdown("### 📁 File Explorer")
        if st.session_state.generated_files:
            selected_file = st.selectbox("Select a file to view:", list(st.session_state.generated_files.keys()))
            if selected_file:
                st.markdown(f"**File:** `{selected_file}`")
                lang_map = {'.py': 'python', '.js': 'javascript', '.jsx': 'javascript', '.ts': 'typescript', '.tsx': 'typescript',
                            '.html': 'html', '.css': 'css', '.json': 'json', '.md': 'markdown', '.yml': 'yaml', '.yaml': 'yaml'}
                file_ext = Path(selected_file).suffix
                language = lang_map.get(file_ext, 'text')
                st.code(st.session_state.generated_files[selected_file], language=language, line_numbers=True)
                st.download_button(f"Download {selected_file}", data=st.session_state.generated_files[selected_file], file_name=selected_file, mime="text/plain")
        else:
            st.info("No files generated yet. Start by describing your project in the Chat tab! 💬")

    # --- Documentation tab ---
    with tab4:
        st.markdown("""
        ### 📚 Documentation
        #### 🚀 Getting Started
        1. Navigate to the **Chat** tab
        2. Describe your project
        3. Watch DevStream AI generate your application
        4. Preview in **Live Preview**
        5. Explore & download files in **File Explorer**
        #### 💡 Example Prompts
        - "Build a modern todo app with React and Tailwind CSS"
        - "Create a Python Flask API with user authentication"
        - "Generate a landing page for a SaaS product"
        #### 🏗️ Architecture
        - **Planner Agent**: Analyzes requirements
        - **Architect Agent**: Designs implementation
        - **Coder Agent**: Generates code files
        #### 🛠️ Tech Stack
        - Frontend: Streamlit with CSS/JS
        - Backend: LangChain + LangGraph
        - LLM: Groq API with GPT models
        #### 📦 Export Options
        - Download individual files
        - Export full project as ZIP
        #### 🤝 Support
        Check the GitHub repo for issues/questions.
        """)

    # Footer
    st.markdown("---")
    st.markdown('<div style="text-align:center;color:#666;padding:1rem;"><p>Built with ❤️ using LangChain, LangGraph, and Streamlit</p><p style="font-size:0.85rem;">DevStream AI © 2024 | Transforming Ideas into Code</p></div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
