# CodeLens AI — Semantic Code Impact Analyzer

<div align="center">

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Ollama](https://img.shields.io/badge/powered%20by-Ollama-orange.svg)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-red.svg)

**A production-ready tool that detects downstream semantic risks when you change code**

Uses call-graph analysis + local LLM reasoning via Ollama to prevent breaking changes before they reach production.

[Features](#-features) • [Installation](#-installation) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [Contributing](#-contributing)

</div>

---

## 🎯 The Problem This Solves

When developers modify code, they often break things in distant parts of the codebase — not through compile errors, but through **semantic drift**:

```python
# Developer changes this:
def get_user_data(user_id):
    return {"id": user_id, "name": "John"}  # Returns dict

# 50 files later, someone expects this format:
user = get_user_data(123)
print(user.name)  # Now breaks! Was expecting object, got dict
```

**The Gap:**
- ✅ Linters catch syntax/type issues
- ✅ Tests catch what they cover
- ❌ **No tool traces semantic impact across your codebase**

**CodeLens AI bridges this gap** by combining:
1. **Static call-graph analysis** — traces all downstream dependencies
2. **LLM semantic reasoning** — analyzes: "What assumptions might break?"
3. **Risk scoring** — prioritizes critical changes for review

---

## ✨ Features

### 🔬 Semantic Impact Analysis (Core Feature)
- **Call Graph Builder** — AST-based analysis of your entire codebase
- **Downstream Tracing** — Identifies all functions affected by your changes
- **LLM-Powered Analysis** — Uses deepseek-coder via Ollama to detect semantic risks
- **Risk Scoring** — Categorizes changes as Low/Medium/High/Critical
- **Multi-Format Reports** — Output as Markdown, JSON, or console
- **Git Integration** — Analyze commits, branches, or specific file changes
- **100% Local** — No API keys, no data leaves your machine

### 📝 Intelligent Documentation
- **Auto-Generated Docstrings** — Context-aware function documentation
- **Module Overviews** — High-level Markdown summaries
- **Commit Summarization** — LLM-powered git commit explanations
- **Export Options** — Python stubs, Markdown, or inject directly

### 📊 Code Visualization
- **UML Class Diagrams** — Auto-generated architecture diagrams
- **Dependency Graphs** — Visualize relationships and inheritance
- **DOT & PNG Export** — Using Graphviz for professional output

### 💬 Intelligent Codebase Q&A
- **Semantic Search** — TF-IDF + LLM retrieval for accurate answers
- **Context-Aware** — References specific files, functions, and line numbers
- **Conversation History** — Multi-turn conversations about your code
- **Source Citations** — Always shows where information comes from

### 🎨 Modern Streamlit UI
- **Four Integrated Tabs** — Docstrings, UML, Chat, Impact Analysis
- **Dark/Light Theme** — Professional, responsive design
- **Real-Time Progress** — Live status updates during processing
- **Export Ready** — Download results in multiple formats

---

## 📋 Requirements

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.8+ | Core runtime |
| Ollama | Latest | LLM inference (deepseek-coder) |
| Graphviz | Latest (optional) | UML diagram rendering |
| Git | Any (optional) | Impact analysis on commits |

**Python Dependencies** (auto-installed):
```
streamlit>=1.28.0
GitPython>=3.1.40
click
requests
torch
transformers
scikit-learn
pydot
graphviz
python-dotenv
astor
```

---

## 🚀 Installation

### 1️⃣ Install Ollama

**Windows:**
```powershell
# Download from https://ollama.com/download
# Or use winget:
winget install Ollama.Ollama
```

**macOS/Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 2️⃣ Pull the AI Model

```bash
ollama pull deepseek-coder:6.7b
```

### 3️⃣ Clone & Setup Project

```bash
git clone https://github.com/prashanth-31/CodeLens_AI-Semantic_Reasoning_for_Modern_Codebases.git
cd CodeLens_AI-Semantic_Reasoning_for_Modern_Codebases

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.\.venv\Scripts\Activate.ps1

# Activate (macOS/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4️⃣ (Optional) Install Graphviz

**Windows:**
```powershell
winget install graphviz
# Add to PATH: C:\Program Files\Graphviz\bin
```

**macOS:**
```bash
brew install graphviz
```

**Linux:**
```bash
sudo apt-get install graphviz  # Debian/Ubuntu
sudo yum install graphviz      # RHEL/CentOS
```

### 5️⃣ Verify Installation

```bash
# Start Ollama (if not running)
ollama serve

# Test the CLI
python -m ai_doc_layer --help

# Or launch the Streamlit UI
streamlit run app.py
```

---

## 🎯 Quick Start

### 🖥️ Streamlit UI (Recommended)

```bash
# Start Ollama first
ollama serve

# Launch the app
streamlit run app.py

# Navigate to http://localhost:8501
```

**Features:**
- 📝 **Tab 1: Docstring Generator** — Generate docs for entire projects
- 📊 **Tab 2: UML Visualizer** — Create class diagrams
- 💬 **Tab 3: Code Chat** — Ask questions about your codebase
- 🔬 **Tab 4: Impact Analysis** — Analyze commit changes

### 🔧 CLI Usage

#### Semantic Impact Analysis

**Analyze last commit:**
```bash
python -m ai_doc_layer analyze-impact ./my-project
```

**Compare specific commits:**
```bash
python -m ai_doc_layer analyze-impact ./my-project \
  --base HEAD~3 \
  --target HEAD \
  --output markdown \
  --out-file impact-report.md
```

**Analyze specific file changes:**
```bash
python -m ai_doc_layer analyze-file-impact ./my-project ./src/api.py
```

#### Documentation Generation

**Generate docstrings for entire project:**
```bash
python -m ai_doc_layer generate ./my-project
```

**Only changed files:**
```bash
python -m ai_doc_layer generate ./my-project --only-changed
```

**Generate UML diagrams:**
```bash
python -m ai_doc_layer generate-uml ./my-project --out-dir ./docs/diagrams
```

#### Codebase Q&A

```bash
python -m ai_doc_layer ask ./my-project "How does the authentication system work?"
```

---

## 📊 Example Output

### Impact Analysis Report

```
============================================================
SEMANTIC IMPACT ANALYSIS REPORT
============================================================
Repository: my-awesome-project
Commits: abc123..def456
Analysis Time: 2024-12-07 15:30:42

📊 SUMMARY
─────────────────────────────────────────────────────────
Files Changed:           5
Functions Modified:      8
Downstream Affected:     24
High/Critical Risk:      2 ⚠️
Medium Risk:             3 ⚡
Low Risk:                3 ✓

🔴 CRITICAL RISKS
─────────────────────────────────────────────────────────
📄 src/auth/validator.py::validate_token (line 45)
   Downstream Impact: 12 functions
   
   RISK ANALYSIS:
   • Changed return type from bool to dict
   • 8 callers expect boolean response
   • Breaking change in error handling flow
   • Affects: login_handler, refresh_token, check_permissions
   
   RECOMMENDED ACTIONS:
   1. Update all callers to handle dict response
   2. Add backward compatibility layer
   3. Write tests for: login_handler, api_middleware
   
🟡 MEDIUM RISKS
─────────────────────────────────────────────────────────
[Additional details...]

📥 FULL REPORT: impact-report.md
```

---

## 🏗️ Architecture

```
CodeLens_AI/
├── app.py                      # Streamlit web interface
├── ai_doc_layer/
│   ├── __init__.py
│   ├── cli.py                 # Click-based CLI commands
│   ├── ollama_client.py       # Ollama LLM integration
│   ├── call_graph.py          # AST-based call graph builder
│   ├── impact_analyzer.py     # Semantic impact analysis engine
│   ├── code_parser.py         # Python AST parsing utilities
│   ├── doc_generator.py       # Docstring generation
│   ├── search_index.py        # TF-IDF semantic search
│   ├── visualizer.py          # UML generation
│   ├── validation.py          # Input validation utilities
│   ├── cache.py               # Response caching
│   └── config.py              # Configuration management
├── requirements.txt           # Python dependencies
├── pyproject.toml            # Package configuration
├── setup.cfg                 # Build configuration
└── README.md                 # This file
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# Ollama server URL (default: http://localhost:11434)
export OLLAMA_HOST="http://your-host:11434"

# Custom model (default: deepseek-coder:6.7b)
export OLLAMA_MODEL="codellama:13b"

# Timeout for LLM requests (default: 300 seconds)
export OLLAMA_TIMEOUT="600"
```

### Programmatic Configuration

```python
from ai_doc_layer.ollama_client import OllamaClient

# Custom configuration
client = OllamaClient(
    base_url="http://localhost:11434",
    model="deepseek-coder:6.7b",
    timeout=600  # 10 minutes for large analyses
)
```

---

## 🧪 Development & Testing

### Run Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# With coverage
pytest --cov=ai_doc_layer tests/
```

### Code Quality

```bash
# Format code
black ai_doc_layer/

# Lint
flake8 ai_doc_layer/

# Type checking
mypy ai_doc_layer/
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🌟 Why CodeLens AI?

| Tool | Call Graph | Semantic Analysis | Local | Risk Scoring |
|------|------------|-------------------|-------|--------------|
| **CodeLens AI** | ✅ | ✅ | ✅ | ✅ |
| Linters (flake8, pylint) | ❌ | ❌ | ✅ | ❌ |
| Type Checkers (mypy) | ❌ | ❌ | ✅ | ❌ |
| Unit Tests | ❌ | Partial | ✅ | ❌ |
| CodeRabbit / GitHub Copilot | ❌ | Superficial | ❌ | ❌ |
| SonarQube | Partial | ❌ | ❌ | Limited |

**CodeLens AI is the only tool that combines call-graph tracing with LLM semantic reasoning, running 100% locally.**

---

## 📞 Support

- 🐛 **Issues**: [GitHub Issues](https://github.com/prashanth-31/CodeLens_AI-Semantic_Reasoning_for_Modern_Codebases/issues)
- 📧 **Contact**: [Create an issue](https://github.com/prashanth-31/CodeLens_AI-Semantic_Reasoning_for_Modern_Codebases/issues/new)
- 📖 **Documentation**: See [FIXES_APPLIED.md](FIXES_APPLIED.md) for recent improvements

---

## 🙏 Acknowledgments

- **Ollama** — For making local LLM inference accessible
- **DeepSeek** — For the excellent deepseek-coder model
- **Streamlit** — For the amazing UI framework
- **Python Community** — For the robust ecosystem

---

<div align="center">

**⭐ Star this repo if you find it useful! ⭐**

Made with ❤️ by the CodeLens AI team

</div>