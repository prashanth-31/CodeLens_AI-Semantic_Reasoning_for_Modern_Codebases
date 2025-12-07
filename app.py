import streamlit as st
import requests
from pathlib import Path

from ai_doc_layer.code_parser import find_python_files, extract_functions_from_file
from ai_doc_layer.doc_generator import DocGenerator
from ai_doc_layer.visualizer import UMLGenerator
from ai_doc_layer.ask_cli import CodebaseAssistant
from ai_doc_layer.impact_analyzer import ImpactAnalyzer, generate_impact_report_markdown
from ai_doc_layer.validation import (
    validate_directory_path,
    check_ollama_connection,
    validate_git_repository
)

# =============================================================================
# PAGE CONFIG & STYLING
# =============================================================================
st.set_page_config(
    page_title="CodeLens AI",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize dark mode state
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

# Get current theme
is_dark = st.session_state.get("dark_mode", False)

# Theme-based CSS variables
if is_dark:
    theme_css = """
    :root {
        --bg-primary: #0d1117;
        --bg-secondary: #161b22;
        --bg-tertiary: #21262d;
        --text-primary: #f0f6fc;
        --text-secondary: #8b949e;
        --accent-primary: #58a6ff;
        --accent-secondary: #a371f7;
        --border-color: #30363d;
        --card-bg: #161b22;
        --header-gradient: linear-gradient(135deg, #238636 0%, #1f6feb 100%);
        --success-bg: #1a4d2e;
        --success-text: #3fb950;
        --info-bg: #0c2d6b;
        --info-text: #58a6ff;
        --warning-bg: #5a4a00;
        --warning-text: #d29922;
        --error-bg: #5a1a1a;
        --error-text: #f85149;
    }
    """
else:
    theme_css = """
    :root {
        --bg-primary: #ffffff;
        --bg-secondary: #f8fafc;
        --bg-tertiary: #f1f5f9;
        --text-primary: #1e293b;
        --text-secondary: #64748b;
        --accent-primary: #667eea;
        --accent-secondary: #764ba2;
        --border-color: #e2e8f0;
        --card-bg: #ffffff;
        --header-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --success-bg: #d4edda;
        --success-text: #155724;
        --info-bg: #cce5ff;
        --info-text: #004085;
        --warning-bg: #fff3cd;
        --warning-text: #856404;
        --error-bg: #f8d7da;
        --error-text: #721c24;
    }
    """

# Custom CSS for elegant appearance
st.markdown(f"""
<style>
    {theme_css}
    
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Global font and background */
    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
    }}
    
    .stApp {{
        background-color: var(--bg-primary);
    }}
    
    /* Main container */
    .main > div {{
        padding-top: 1.5rem;
    }}
    
    /* Header styling */
    .main-header {{
        background: var(--header-gradient);
        padding: 2.5rem 2rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
        box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
    }}
    
    .main-header h1 {{
        margin: 0;
        font-size: 2.8rem;
        font-weight: 700;
        letter-spacing: -0.02em;
    }}
    
    .main-header p {{
        margin: 0.75rem 0 0 0;
        opacity: 0.9;
        font-size: 1.15rem;
        font-weight: 400;
    }}
    
    /* Card styling */
    .metric-card {{
        background: var(--bg-tertiary);
        padding: 1.5rem;
        border-radius: 16px;
        border-left: 4px solid var(--accent-primary);
        margin: 0.5rem 0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }}
    
    /* Status badges */
    .status-badge {{
        display: inline-block;
        padding: 0.35rem 1rem;
        border-radius: 24px;
        font-size: 0.85rem;
        font-weight: 600;
    }}
    
    .status-success {{
        background: var(--success-bg);
        color: var(--success-text);
    }}
    
    .status-warning {{
        background: var(--warning-bg);
        color: var(--warning-text);
    }}
    
    .status-info {{
        background: var(--info-bg);
        color: var(--info-text);
    }}
    
    /* Feature cards */
    .feature-card {{
        background: var(--card-bg);
        padding: 1.75rem;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid var(--border-color);
        height: 100%;
        transition: all 0.3s ease;
    }}
    
    .feature-card:hover {{
        transform: translateY(-4px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.12);
    }}
    
    .feature-card h3 {{
        margin-top: 0;
        margin-bottom: 0.75rem;
        color: var(--text-primary);
        font-weight: 600;
    }}
    
    .feature-card p {{
        color: var(--text-secondary);
        margin: 0;
        line-height: 1.5;
    }}
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background: var(--bg-secondary);
        padding: 8px;
        border-radius: 12px;
    }}
    
    .stTabs [data-baseweb="tab"] {{
        padding: 12px 24px;
        border-radius: 10px;
        font-weight: 500;
        color: var(--text-primary);
    }}
    
    .stTabs [aria-selected="true"] {{
        background: var(--card-bg) !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }}
    
    /* Button styling */
    .stButton > button {{
        border-radius: 10px;
        padding: 0.6rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
        border: none;
        background: var(--header-gradient);
    }}
    
    .stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }}
    
    /* Code blocks */
    .stCodeBlock {{
        border-radius: 12px;
        border: 1px solid var(--border-color);
    }}
    
    /* Expander styling */
    .streamlit-expanderHeader {{
        font-weight: 600;
        border-radius: 10px;
        background: var(--bg-secondary);
    }}
    
    /* Input fields */
    .stTextInput > div > div > input {{
        border-radius: 10px;
        border: 2px solid var(--border-color);
        padding: 0.75rem 1rem;
        transition: all 0.2s ease;
        background: var(--bg-secondary);
        color: var(--text-primary);
    }}
    
    .stTextInput > div > div > input:focus {{
        border-color: var(--accent-primary);
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }}
    
    /* Progress bar */
    .stProgress > div > div > div > div {{
        background: var(--header-gradient);
        border-radius: 10px;
    }}
    
    /* Metric styling */
    [data-testid="stMetric"] {{
        background: var(--bg-tertiary);
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }}
    
    [data-testid="stMetricValue"] {{
        font-weight: 700;
        color: var(--accent-primary);
    }}
    
    [data-testid="stMetricLabel"] {{
        color: var(--text-secondary);
    }}
    
    /* Image container */
    [data-testid="stImage"] {{
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }}
    
    /* Download button */
    .stDownloadButton > button {{
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        border-radius: 10px;
        font-weight: 600;
    }}
    
    .stDownloadButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4);
    }}
    
    /* Chat messages */
    .stChatMessage {{
        border-radius: 12px;
        margin: 0.5rem 0;
        background: var(--bg-secondary);
    }}
    
    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background: var(--bg-secondary);
    }}
    
    section[data-testid="stSidebar"] .block-container {{
        padding-top: 2rem;
    }}
    
    /* Success/Info/Warning/Error messages */
    .stSuccess, .stInfo, .stWarning, .stError {{
        border-radius: 10px;
        padding: 1rem;
    }}
    
    /* Text colors for dark mode */
    .stMarkdown, .stText, p, h1, h2, h3, h4, h5, h6, span, label {{
        color: var(--text-primary) !important;
    }}
    
    /* Selectbox and other inputs */
    .stSelectbox > div > div {{
        background: var(--bg-secondary);
        color: var(--text-primary);
    }}
    
    /* Slider */
    .stSlider > div > div > div {{
        color: var(--text-primary);
    }}
    
    /* Checkbox and toggle */
    .stCheckbox label, .stToggle label {{
        color: var(--text-primary) !important;
    }}
    
    /* Expander content */
    .streamlit-expanderContent {{
        background: var(--bg-secondary);
        border-color: var(--border-color);
    }}
    
    /* Hide Streamlit branding */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.markdown("### 🔬 CodeLens AI")
    st.markdown("---")
    
    # Theme Toggle
    st.markdown("#### 🎨 Theme")
    dark_mode = st.toggle("🌙 Dark Mode", value=st.session_state.get("dark_mode", False), key="dark_mode_toggle")
    if dark_mode != st.session_state.get("dark_mode", False):
        st.session_state.dark_mode = dark_mode
        st.rerun()
    
    st.markdown("---")
    
    st.markdown("#### 🚀 Quick Start")
    st.code("ollama serve", language="bash")
    st.code("ollama pull deepseek-coder:6.7b", language="bash")
    
    st.markdown("---")
    st.markdown("#### 📊 CLI Commands")
    st.code("""# Impact Analysis
python -m ai_doc_layer analyze-impact .

# Build Call Graph  
python -m ai_doc_layer build-call-graph .

# Generate Docs
python -m ai_doc_layer generate .""", language="bash")
    
    st.markdown("---")
    st.markdown("#### ℹ️ About")
    st.markdown("""
    **CodeLens AI** detects semantic risks 
    when you change code using:
    - 📊 Call-graph analysis
    - 🧠 LLM reasoning
    - 🎯 Risk scoring
    """)
    
    st.markdown("---")
    st.caption("v1.0.0 • Made with ❤️")

# =============================================================================
# MAIN HEADER
# =============================================================================
st.markdown("""
<div class="main-header">
    <h1>🔬 CodeLens AI</h1>
    <p>Semantic Code Impact Analyzer • Documentation Generator • Codebase Q&A</p>
</div>
""", unsafe_allow_html=True)

# Feature highlights
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("""
    <div class="feature-card">
        <h3>🔍 Impact Analysis</h3>
        <p>Detect downstream semantic risks when code changes. Uses call-graph + LLM reasoning.</p>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown("""
    <div class="feature-card">
        <h3>📝 Auto Documentation</h3>
        <p>Generate intelligent docstrings and module overviews with deepseek-coder.</p>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown("""
    <div class="feature-card">
        <h3>💬 Code Chat</h3>
        <p>Ask questions about your codebase using semantic search + LLM context.</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# =============================================================================
# TABS
# =============================================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📝 Docstring Generator", 
    "📊 UML Visualizer", 
    "💬 Code Chat",
    "🔬 Impact Analysis"
])

# ---------------------------------------------------------
# TAB 1 — DOCSTRING GENERATOR
# ---------------------------------------------------------
with tab1:
    st.markdown("### 📝 Auto-Generate Docstrings")
    st.markdown("Generate intelligent docstrings for all functions in your Python project.")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        repo_path = st.text_input(
            "📁 Project Path",
            placeholder="Enter path to your Python project...",
            help="Full path to your Python repository",
            key="docstring_path"
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        run_btn = st.button("🚀 Generate", type="primary", use_container_width=True)
    
    if repo_path and run_btn:
        # Validate path
        try:
            repo = validate_directory_path(repo_path)
        except (ValueError, FileNotFoundError) as e:
            st.error(f"❌ Invalid path: {e}")
        else:
            # Check Ollama connection before processing
            is_connected, error_msg = check_ollama_connection()
            if not is_connected:
                st.error(f"❌ {error_msg}")
                st.info("💡 Start Ollama with: `ollama serve`")
            else:
                files = find_python_files(repo)
                total_files = len(files)
                
                if total_files == 0:
                    st.warning("⚠️ No Python files found in the specified directory.")
                else:
                    # Stats row
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("📄 Python Files", total_files)
                    with col2:
                        st.metric("📁 Project", repo.name)
                    with col3:
                        st.metric("🔄 Status", "Processing...")
                    
                    st.markdown("---")
                    
                    # Initialize generator
                    doc_gen = DocGenerator()
                    
                    # Progress tracking
                    progress_bar = st.progress(0, text="Initializing...")
                    status_container = st.empty()
                    results_container = st.container()
                    
                    total_functions = 0
                    processed_functions = 0
                    
                    # Store all generated docstrings for export
                    all_docstrings = []  # List of dicts: {file, function, args, lineno, docstring}
                    
                    for file_index, file_path in enumerate(files, start=1):
                        progress_bar.progress(
                            file_index / total_files,
                            text=f"📄 Processing: {file_path.name} ({file_index}/{total_files})"
                        )
                        
                        with results_container.expander(
                            f"📂 {file_path.name}", 
                            expanded=(file_index == 1)
                        ):
                            functions = extract_functions_from_file(file_path)
                            total_funcs = len(functions)
                            total_functions += total_funcs
                            
                            if total_funcs == 0:
                                st.info("No functions found in this file.")
                                continue
                            
                            st.markdown(f"**Found {total_funcs} function(s)**")
                            
                            func_progress = st.progress(0)
                            
                            for idx, func in enumerate(functions, start=1):
                                status_container.info(f"🔧 Generating docstring for `{func.name}`...")
                                func_progress.progress(idx / total_funcs)
                                
                                try:
                                    doc = doc_gen.generate_docstring(func, file_path)
                                    processed_functions += 1
                                    
                                    # Store for export (don't inject)
                                    all_docstrings.append({
                                        "file": str(file_path.relative_to(repo)),
                                        "function": func.name,
                                        "args": func.args,
                                        "lineno": func.lineno,
                                        "docstring": doc
                                    })
                                    
                                    # Display result
                                    col1, col2 = st.columns([1, 3])
                                    with col1:
                                        st.success(f"✅ `{func.name}`")
                                    with col2:
                                        st.code(doc, language="python")
                                except (ValueError, OSError, RuntimeError) as e:
                                    st.error(f"❌ Error on `{func.name}`: {e}")
                    
                    # Completion
                    progress_bar.progress(1.0, text="✅ Complete!")
                    status_container.empty()
                    
                    st.markdown("---")
                    st.success(f"""
                    ### 🎉 Docstrings Generated Successfully!
                    
                    - **Files processed:** {total_files}
                    - **Functions documented:** {processed_functions}
                    - **Mode:** Preview only (source files not modified)
                    """)
                    
                    # Export section
                    if all_docstrings:
                        st.markdown("### 📥 Export Generated Docstrings")
                        st.info("💡 Docstrings are **not injected** into source files. Use the export options below to save them.")
                        
                        col1, col2, col3 = st.columns(3)
                        
                        # Generate export content
                        # JSON export
                        import json
                        json_content = json.dumps(all_docstrings, indent=2)
                        
                        # Markdown export
                        md_lines = ["# Generated Docstrings\n"]
                        current_file = None
                        for item in all_docstrings:
                            if item["file"] != current_file:
                                current_file = item["file"]
                                md_lines.append(f"\n## 📄 `{current_file}`\n")
                            md_lines.append(f"### `{item['function']}({', '.join(item['args'])})`")
                            md_lines.append(f"*Line {item['lineno']}*\n")
                            md_lines.append("```python")
                            md_lines.append(item['docstring'])
                            md_lines.append("```\n")
                        md_content = "\n".join(md_lines)
                        
                        # Python stub export
                        py_lines = ['"""Auto-generated docstrings for code review."""\n']
                        current_file = None
                        for item in all_docstrings:
                            if item["file"] != current_file:
                                current_file = item["file"]
                                py_lines.append(f"\n# {'=' * 60}")
                                py_lines.append(f"# File: {current_file}")
                                py_lines.append(f"# {'=' * 60}\n")
                            args_str = ", ".join(item['args'])
                            py_lines.append(f"def {item['function']}({args_str}):")
                            py_lines.append(f"    {item['docstring']}")
                            py_lines.append("    pass\n")
                        py_content = "\n".join(py_lines)
                        
                        with col1:
                            st.download_button(
                                label="📄 Download JSON",
                                data=json_content,
                                file_name="docstrings.json",
                                mime="application/json",
                                use_container_width=True
                            )
                        
                        with col2:
                            st.download_button(
                                label="📝 Download Markdown",
                                data=md_content,
                                file_name="docstrings.md",
                                mime="text/markdown",
                                use_container_width=True
                            )
                        
                        with col3:
                            st.download_button(
                                label="🐍 Download Python Stubs",
                                data=py_content,
                                file_name="docstrings_stubs.py",
                                mime="text/x-python",
                                use_container_width=True
                            )

# ---------------------------------------------------------
# TAB 2 — UML VISUALIZER
# ---------------------------------------------------------
with tab2:
    st.markdown("### 📊 UML Class Diagram Generator")
    st.markdown("Visualize your codebase structure with auto-generated UML diagrams showing **classes, methods, inheritance, and dependencies**.")
    
    # Legend
    st.markdown("""
    <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
        <strong>📖 Legend:</strong>
        <span style="color: #4CAF50; margin-left: 1rem;">━━▷ Inheritance (extends)</span>
        <span style="color: #FF9800; margin-left: 1rem;">┄┄▷ Dependency (uses)</span>
        <span style="color: #3F51B5; margin-left: 1rem;">█ Classes</span>
        <span style="color: #FF9800; margin-left: 1rem;">█ Module Functions</span>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        repo_path_uml = st.text_input(
            "📁 Project Path",
            placeholder="Enter path to your Python project...",
            help="Full path to your Python repository",
            key="uml_path"
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        uml_btn = st.button("📊 Generate UML", type="primary", use_container_width=True)
    
    if repo_path_uml and uml_btn:
        # Validate path
        try:
            repo = validate_directory_path(repo_path_uml)
        except (ValueError, FileNotFoundError) as e:
            st.error(f"❌ Invalid path: {e}")
        else:
            out_file = repo / "ai_docs" / "uml.png"
            out_file.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                uml = UMLGenerator()
                
                with st.spinner("🎨 Analyzing codebase and generating UML diagram..."):
                    uml.generate(repo, out_file)
                
                st.success("✅ UML diagram generated successfully!")
                
                # Statistics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("📦 Classes", len(uml.class_map))
                with col2:
                    total_methods = sum(len(info.get("methods", [])) for info in uml.class_map.values())
                    st.metric("🔧 Methods", total_methods)
                with col3:
                    inheritance_count = sum(len(info.get("bases", [])) for info in uml.class_map.values())
                    st.metric("🔗 Inheritance", inheritance_count)
                with col4:
                    dep_count = sum(len(deps) for deps in uml.dependencies.values())
                    st.metric("📡 Dependencies", dep_count)
                
                st.markdown("---")
                
                # Display diagram
                st.image(str(out_file), caption="Generated UML Class Diagram")
                
                # Download option
                with open(out_file, "rb") as f:
                    st.download_button(
                        "📥 Download UML Diagram",
                        data=f.read(),
                        file_name="uml_diagram.png",
                        mime="image/png",
                        use_container_width=True
                    )
                
                # Show class details in expander
                if uml.class_map:
                    st.markdown("---")
                    st.markdown("#### 📋 Class Details")
                    
                    for cname, info in uml.class_map.items():
                        with st.expander(f"📦 {cname}", expanded=False):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"**File:** `{Path(info['file']).name}`")
                                if info.get("bases"):
                                    st.markdown(f"**Extends:** `{', '.join(info['bases'])}`")
                            with col2:
                                if info.get("methods"):
                                    public = [m for m in info["methods"] if not m.startswith("_")]
                                    private = [m for m in info["methods"] if m.startswith("_")]
                                    st.markdown(f"**Methods:** {len(public)} public, {len(private)} private")
                    
            except (OSError, RuntimeError, ValueError) as e:
                st.error(f"❌ Error: {e}")
                st.info("💡 Make sure Graphviz is installed and on PATH. Run: `winget install graphviz`")

# ---------------------------------------------------------
# TAB 3 — CHAT WITH CODEBASE
# ---------------------------------------------------------
with tab3:
    st.markdown("### 💬 Chat with Your Codebase")
    st.markdown("Ask questions about your code using **semantic search** and **LLM reasoning**.")
    
    # Project path input with better styling
    col1, col2 = st.columns([3, 1])
    with col1:
        repo_c = st.text_input(
            "📁 Project Path",
            placeholder="Enter path to your Python project...",
            help="Full path to your Python repository",
            key="chat_path"
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Reset Chat", use_container_width=True):
            st.session_state.messages = []
            if "chat_assistant" in st.session_state:
                del st.session_state["chat_assistant"]
            st.rerun()
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if repo_c:
        # Suggested questions section
        st.markdown("---")
        st.markdown("#### 💡 Suggested Questions")
        
        suggested = [
            "What are the main classes in this project?",
            "How does the code parsing work?",
            "Explain the entry points of this app",
            "What LLM integration is used?",
        ]
        
        cols = st.columns(len(suggested))
        for i, q in enumerate(suggested):
            with cols[i]:
                if st.button(q, key=f"suggest_{i}", use_container_width=True):
                    st.session_state.pending_question = q
                    st.rerun()
        
        st.markdown("---")
    
    # Chat container with custom styling
    st.markdown("""
    <style>
    .chat-container {
        max-height: 500px;
        overflow-y: auto;
        padding: 1rem;
        background: #fafafa;
        border-radius: 12px;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Display chat history
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"], avatar="🧑‍💻" if message["role"] == "user" else "🤖"):
                st.markdown(message["content"])
                
                # Show sources if available
                if message["role"] == "assistant" and "sources" in message and message["sources"]:
                    with st.expander("📚 Sources", expanded=False):
                        for src in message["sources"][:3]:
                            st.markdown(f"- `{src['file']}` → `{src['function']}()` (line {src['line']})")
    
    # Handle pending question from suggested buttons
    pending_q = st.session_state.get("pending_question", None)
    if pending_q:
        del st.session_state["pending_question"]
        prompt = pending_q
    else:
        prompt = st.chat_input("Ask a question about your code...", key="chat_input")
    
    # Process chat input
    if prompt:
        if not repo_c:
            st.error("⚠️ Please enter a project path first.")
        else:
            # Validate path
            try:
                repo_path = validate_directory_path(repo_c)
            except (ValueError, FileNotFoundError) as e:
                st.error(f"❌ Invalid path: {e}")
            else:
                # Check Ollama connection
                is_connected, error_msg = check_ollama_connection()
                if not is_connected:
                    st.error(f"❌ {error_msg}")
                    st.info("💡 Start Ollama with: `ollama serve`")
                else:
                    # Add user message
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    with st.chat_message("user", avatar="🧑‍💻"):
                        st.markdown(prompt)
                    
                    # Generate response
                    with st.chat_message("assistant", avatar="🤖"):
                        # Status indicators
                        status = st.status("🔍 Analyzing your codebase...", expanded=True)
                        
                        try:
                            # Initialize or reuse assistant
                            if "chat_assistant" not in st.session_state or st.session_state.get("chat_repo") != repo_c:
                                status.write("📂 Indexing codebase...")
                                st.session_state.chat_assistant = CodebaseAssistant(repo_path)
                                st.session_state.chat_repo = repo_c
                            
                            assistant = st.session_state.chat_assistant
                            
                            status.write("🔎 Searching for relevant code...")
                            status.write("🧠 Generating response with LLM...")
                            
                            response, sources = assistant.ask(prompt)
                            
                            status.update(label="✅ Response generated!", state="complete", expanded=False)
                            
                            # Display response
                            st.markdown(response)
                            
                            # Show sources
                            if sources:
                                with st.expander("📚 Sources Referenced", expanded=False):
                                    for src in sources[:5]:
                                        col1, col2, col3 = st.columns([2, 2, 1])
                                        with col1:
                                            st.markdown(f"📄 `{src['file']}`")
                                        with col2:
                                            st.markdown(f"`{src['function']}()`")
                                        with col3:
                                            st.markdown(f"Line {src['line']}")
                            
                            # Store in history
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": response,
                                "sources": sources
                            })
                            
                        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                            status.update(label="❌ Connection Error", state="error", expanded=True)
                            error_msg = f"Connection Error: {str(e)}"
                            st.error(error_msg)
                            st.info("💡 Make sure Ollama is running: `ollama serve`")
                            st.session_state.messages.append({"role": "assistant", "content": error_msg, "sources": []})
                        except (ValueError, RuntimeError, OSError) as e:
                            status.update(label="❌ Error occurred", state="error", expanded=True)
                            error_msg = f"Error: {str(e)}"
                            st.error(error_msg)
                            st.session_state.messages.append({"role": "assistant", "content": error_msg, "sources": []})
    
    # Empty state
    if not st.session_state.messages and repo_c:
        st.markdown("""
        <div style="text-align: center; padding: 3rem; color: #888;">
            <h3>🤖 Ready to help!</h3>
            <p>Ask any question about your codebase, or try one of the suggested questions above.</p>
        </div>
        """, unsafe_allow_html=True)

# ---------------------------------------------------------
# TAB 4 — IMPACT ANALYSIS (INTERACTIVE)
# ---------------------------------------------------------
with tab4:
    st.markdown("### 🔬 Semantic Impact Analysis")
    st.markdown("Detect downstream risks when you change code — the **novel feature** of this tool.")
    
    st.markdown("---")
    
    # Configuration Section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        impact_repo_path = st.text_input(
            "📁 Repository Path",
            placeholder="Enter path to your git repository...",
            help="Must be a git repository with commit history",
            key="impact_repo_path"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        analysis_mode = st.selectbox(
            "🔧 Analysis Mode",
            options=["Commit Analysis", "File Analysis", "Build Call Graph Only"],
            help="Choose the type of analysis to perform"
        )
    
    # Mode-specific options
    st.markdown("#### ⚙️ Options")
    
    # Initialize use_llm with default value (will be overridden in specific modes)
    use_llm = False
    
    if analysis_mode == "Commit Analysis":
        col1, col2, col3 = st.columns(3)
        with col1:
            base_commit = st.text_input(
                "Base Commit",
                value="HEAD~1",
                help="The starting point for comparison (e.g., HEAD~1, main, abc123)"
            )
        with col2:
            target_commit = st.text_input(
                "Target Commit", 
                value="HEAD",
                help="The ending point for comparison (e.g., HEAD, feature-branch)"
            )
        with col3:
            max_depth = st.slider(
                "Max Dependency Depth",
                min_value=1,
                max_value=5,
                value=3,
                help="How deep to trace downstream dependencies"
            )
        
        use_llm = st.checkbox("🧠 Use LLM for semantic analysis", value=True, help="Disable for faster but less detailed analysis")
        
    elif analysis_mode == "File Analysis":
        col1, col2 = st.columns([2, 1])
        with col1:
            target_file = st.text_input(
                "Target File",
                placeholder="e.g., src/utils.py",
                help="Relative path to the file to analyze"
            )
        with col2:
            max_depth = st.slider(
                "Max Dependency Depth",
                min_value=1,
                max_value=5,
                value=3,
                help="How deep to trace downstream dependencies"
            )
        use_llm = st.checkbox("🧠 Use LLM for semantic analysis", value=False, help="Enable for detailed risk analysis")
        
    else:  # Build Call Graph Only
        output_format = st.selectbox(
            "Output Format",
            options=["JSON", "Summary"],
            help="Format for the call graph output"
        )
    
    st.markdown("---")
    
    # Run Analysis Button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        run_analysis = st.button("🚀 Run Impact Analysis", type="primary", use_container_width=True)
    
    # Results Section
    if run_analysis and impact_repo_path:
        # Validate path
        try:
            repo = validate_directory_path(impact_repo_path)
            validate_git_repository(repo)
        except ValueError as e:
            st.error(f"❌ {e}")
        except FileNotFoundError as e:
            st.error(f"❌ {e}")
        else:
            # Check Ollama connection if LLM is enabled
            if use_llm:
                is_connected, error_msg = check_ollama_connection()
                if not is_connected:
                    st.warning(f"⚠️ {error_msg}")
                    st.info("💡 Continuing without LLM analysis. Start Ollama for full semantic analysis: `ollama serve`")
                    use_llm = False
            
            try:
                # Create analyzer
                analyzer = ImpactAnalyzer(repo)
                
                if analysis_mode == "Build Call Graph Only":
                    with st.spinner("🔨 Building call graph..."):
                        analyzer.build_graph()
                    
                    st.success(f"✅ Call graph built with {len(analyzer.call_graph)} functions!")
                    
                    # Display stats
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("📦 Functions Indexed", len(analyzer.call_graph))
                    with col2:
                        total_calls = sum(len(node.calls) for node in analyzer.call_graph.values())
                        st.metric("🔗 Call Relationships", total_calls)
                    with col3:
                        files = set(node.file_path for node in analyzer.call_graph.values() if node.file_path)
                        st.metric("📄 Files Analyzed", len(files))
                    
                    # Show graph details
                    with st.expander("📊 Call Graph Details", expanded=False):
                        for qn, node in list(analyzer.call_graph.items())[:20]:
                            st.markdown(f"**`{node.name}`** in `{Path(node.file_path).name if node.file_path else 'unknown'}`")
                            if node.calls:
                                calls_list = list(node.calls)[:5]
                                st.markdown(f"  → Calls: {', '.join(calls_list)}")
                            if node.called_by:
                                called_by_list = list(node.called_by)[:5]
                                st.markdown(f"  ← Called by: {', '.join(called_by_list)}")
                        
                        if len(analyzer.call_graph) > 20:
                            st.info(f"... and {len(analyzer.call_graph) - 20} more functions")
                    
                    # Export option
                    if output_format == "JSON":
                        graph_json = {
                            qn: {
                                "name": node.name,
                                "file": str(node.file_path) if node.file_path else None,
                                "lineno": node.lineno,
                                "calls": list(node.calls),
                                "called_by": list(node.called_by)
                            }
                            for qn, node in analyzer.call_graph.items()
                        }
                        import json
                        st.download_button(
                            "📥 Download Call Graph JSON",
                            data=json.dumps(graph_json, indent=2),
                            file_name="call_graph.json",
                            mime="application/json",
                            use_container_width=True
                        )
                
                elif analysis_mode == "Commit Analysis":
                    status = st.status("🔬 Running impact analysis...", expanded=True)
                    
                    status.write("📊 Building call graph...")
                    analyzer.build_graph()
                    
                    status.write(f"🔍 Analyzing changes from {base_commit} to {target_commit}...")
                    
                    if not use_llm:
                        # Disable LLM for faster analysis
                        analyzer.llm = None
                    
                    report = analyzer.analyze_commit(
                        base=base_commit,
                        target=target_commit,
                        max_downstream_depth=max_depth
                    )
                    
                    status.update(label="✅ Analysis complete!", state="complete", expanded=False)
                    
                    # Display results
                    st.markdown("---")
                    st.markdown("### 📊 Impact Analysis Results")
                    
                    # Summary metrics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("📄 Files Changed", len(report.changed_files))
                    with col2:
                        st.metric("🔧 Functions Affected", len(report.function_reports))
                    with col3:
                        st.metric("📡 Downstream Impact", report.total_downstream_affected)
                    with col4:
                        critical = sum(1 for r in report.function_reports if r.risk_score in ["Critical", "High"])
                        if critical > 0:
                            st.metric("⚠️ High Risk", critical)
                        else:
                            st.metric("✅ Risk Level", "Low")
                    
                    # Summary
                    st.markdown("#### 📝 Summary")
                    st.info(report.summary)
                    
                    # Changed files
                    if report.changed_files:
                        with st.expander("📁 Changed Files", expanded=False):
                            for f in report.changed_files:
                                st.markdown(f"- `{f}`")
                    
                    # Function reports
                    if report.function_reports:
                        st.markdown("#### 🔍 Function-by-Function Analysis")
                        
                        for idx, fr in enumerate(report.function_reports):
                            # Risk color coding
                            if fr.risk_score == "Critical":
                                icon, color = "🔴", "#DC3545"
                            elif fr.risk_score == "High":
                                icon, color = "🟠", "#FD7E14"
                            elif fr.risk_score == "Medium":
                                icon, color = "🟡", "#FFC107"
                            else:
                                icon, color = "🟢", "#28A745"
                            
                            with st.expander(f"{icon} **{fr.function_name}** ({fr.risk_score}) — {fr.downstream_count} downstream, {fr.upstream_count} upstream", expanded=(idx == 0)):
                                col1, col2 = st.columns([2, 1])
                                with col1:
                                    st.markdown(f"**File:** `{fr.file_path}` (line {fr.lineno})")
                                with col2:
                                    st.markdown(f"<span style='color:{color};font-weight:bold;'>Risk: {fr.risk_score}</span>", unsafe_allow_html=True)
                                
                                # Upstream dependencies (what this function calls)
                                if fr.upstream_functions:
                                    st.markdown("**⬆️ Upstream Dependencies (calls):**")
                                    for name, path, line in fr.upstream_functions[:10]:
                                        st.markdown(f"  - `{name}` in `{Path(path).name}` (line {line})")
                                    if len(fr.upstream_functions) > 10:
                                        st.caption(f"... and {len(fr.upstream_functions) - 10} more")
                                
                                # Downstream dependencies (called by)
                                if fr.downstream_functions:
                                    st.markdown("**⬇️ Downstream Dependencies (called by):**")
                                    for name, path, line in fr.downstream_functions[:10]:
                                        st.markdown(f"  - `{name}` in `{Path(path).name}` (line {line})")
                                    if len(fr.downstream_functions) > 10:
                                        st.caption(f"... and {len(fr.downstream_functions) - 10} more")
                                
                                if fr.risk_analysis and use_llm:
                                    st.markdown("**🧠 LLM Analysis:**")
                                    st.markdown(fr.risk_analysis)
                    
                    # Export options
                    st.markdown("---")
                    st.markdown("#### 📥 Export Report")
                    col1, col2 = st.columns(2)
                    with col1:
                        md_report = generate_impact_report_markdown(report)
                        st.download_button(
                            "📝 Download Markdown Report",
                            data=md_report,
                            file_name="impact_report.md",
                            mime="text/markdown",
                            use_container_width=True
                        )
                    with col2:
                        from ai_doc_layer.impact_analyzer import generate_impact_report_json
                        json_report = generate_impact_report_json(report)
                        st.download_button(
                            "📄 Download JSON Report",
                            data=json_report,
                            file_name="impact_report.json",
                            mime="application/json",
                            use_container_width=True
                        )
                
                elif analysis_mode == "File Analysis":
                    if not target_file:
                        st.error("⚠️ Please enter a target file path.")
                    else:
                        file_path = repo / target_file
                        if not file_path.exists():
                            st.error(f"❌ File not found: {target_file}")
                        else:
                            status = st.status("🔬 Analyzing file impact...", expanded=True)
                            
                            status.write("📊 Building call graph...")
                            analyzer.build_graph()
                            
                            status.write(f"🔍 Analyzing {target_file}...")
                            
                            if not use_llm:
                                analyzer.llm = None
                            
                            report = analyzer.analyze_file(file_path, max_depth=max_depth)
                            
                            status.update(label="✅ Analysis complete!", state="complete", expanded=False)
                            
                            # Display results
                            st.markdown("---")
                            st.markdown(f"### 📊 Impact Analysis: `{target_file}`")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("🔧 Functions in File", len(report.function_reports))
                            with col2:
                                st.metric("📡 Total Downstream", report.total_downstream_affected)
                            
                            for fr in report.function_reports:
                                if fr.risk_score == "Critical":
                                    icon = "🔴"
                                elif fr.risk_score == "High":
                                    icon = "🟠"
                                elif fr.risk_score == "Medium":
                                    icon = "🟡"
                                else:
                                    icon = "🟢"
                                
                                with st.expander(f"{icon} **{fr.function_name}** — {fr.downstream_count} downstream, {fr.upstream_count} upstream"):
                                    st.markdown(f"**Line:** {fr.lineno}")
                                    
                                    # Upstream dependencies
                                    if fr.upstream_functions:
                                        st.markdown("**⬆️ Upstream (calls):**")
                                        for name, path, line in fr.upstream_functions[:5]:
                                            st.markdown(f"  - `{name}` in `{Path(path).name}`")
                                        if len(fr.upstream_functions) > 5:
                                            st.caption(f"... and {len(fr.upstream_functions) - 5} more")
                                    
                                    # Downstream dependencies
                                    if fr.downstream_functions:
                                        st.markdown("**⬇️ Downstream (called by):**")
                                        for name, path, line in fr.downstream_functions[:5]:
                                            st.markdown(f"  - `{name}` in `{Path(path).name}`")
                                        if len(fr.downstream_functions) > 5:
                                            st.caption(f"... and {len(fr.downstream_functions) - 5} more")
                                    
                                    if fr.risk_analysis:
                                        st.markdown("**Analysis:**")
                                        st.markdown(fr.risk_analysis)
                
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                st.error(f"❌ Connection Error: {e}")
                st.info("💡 Make sure Ollama is running: `ollama serve`")
            except (OSError, ValueError, RuntimeError) as e:
                st.error(f"❌ Error: {e}")
                st.info("💡 Make sure this is a valid git repository.")
    
    # Help section
    st.markdown("---")
    with st.expander("❓ How It Works", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            #### 🎯 What This Tool Does
            
            1. **Builds a call graph** of your entire codebase
            2. **Detects changed functions** from git commits
            3. **Traces downstream callers** that might be affected
            4. **Uses LLM** to analyze semantic risks
            5. **Generates risk reports** with scores and suggestions
            """)
        
        with col2:
            st.markdown("""
            #### ⚡ Why It Matters
            
            - Linters catch syntax, not **behavioral intent**
            - Tests only catch **what they cover**
            - This tool predicts **semantic drift**
            - Get early warning of **breaking changes**
            - Understand **ripple effects** of your changes
            """)

