# AI Documentation Layer — Semantic Code Impact Analyzer

A research-grade CLI and Streamlit tool that goes beyond docstring generation:  
**Detects downstream semantic risks when you change code** using call-graph analysis + local LLM via Ollama.

## The Problem This Solves

When developers modify code, they often break things in distant parts of the codebase — not through compile errors, but through **semantic drift**:
- A function now returns a slightly different format
- An invariant is silently violated
- A side-effect is introduced that downstream callers don't expect

**Static analysis and linters catch syntax/type issues, not behavioral intent.**  
**Tests only catch what they cover.**  
**Existing LLM code review tools analyze diffs superficially — they don't trace impact.**

This tool fuses **static call-graph analysis** with **LLM-powered semantic reasoning** to identify:
- Which functions are affected by your change
- What assumptions might now be broken
- Risk scores and suggested test cases

## Features

### 🔬 Semantic Impact Analysis (Novel)
- Build a **call graph** of your entire codebase
- **Trace downstream dependents** when you change a function
- Use **deepseek-coder:6.7b via Ollama** to semantically analyze: "What assumptions in these downstream callers might now be violated?"
- Generate **risk-scored impact reports** (Markdown/JSON)
- **Fully local** — no API keys, no data leaves your machine

### 📝 Documentation Generation
- Auto-generate docstrings for Python functions
- Create per-module Markdown overviews in `ai_docs/`
- Summarize git commits with LLM

### 📊 Visualization
- UML/structure diagrams (DOT + PNG via Graphviz)

### 💬 Codebase Q&A
- Ask questions about your code using TF-IDF retrieval + LLM context

## Requirements

- Python 3.9+
- **Ollama** running locally with `deepseek-coder:6.7b` model
- Optional: PyTorch + Transformers (for local docstring generation)
- Optional: Graphviz on PATH (for UML PNG output)

## Installation

### 1. Install Ollama and pull the model

```powershell
# Install Ollama from https://ollama.com/download
# Then pull the model:
ollama pull deepseek-coder:6.7b
```

### 2. Clone and set up the project

```powershell
git clone https://github.com/manupks/LLM-Docstring-File-parser.git
cd LLM-Docstring-File-parser
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Start Ollama (if not running)

```powershell
ollama serve
```

## CLI Usage

### 🔬 Semantic Impact Analysis

Analyze the impact of your last commit:
```powershell
python -m ai_doc_layer analyze-impact <path-to-repo>
```

Compare specific commits:
```powershell
python -m ai_doc_layer analyze-impact <repo> --base HEAD~3 --target HEAD --output markdown --out-file report.md
```

Quick file-level impact check (no LLM, just call-graph):
```powershell
python -m ai_doc_layer analyze-file-impact <repo> <file.py>
```

Build and inspect the call graph:
```powershell
python -m ai_doc_layer build-call-graph <repo> --out-file graph.json
```

### 📝 Documentation Commands

```powershell
python -m ai_doc_layer generate <repo> [--only-changed]
python -m ai_doc_layer generate-uml <repo> [--out-dir PATH]
python -m ai_doc_layer summarize-last-commit <repo>
python -m ai_doc_layer ask <repo> "How does X work?"
```

## Configuration

By default, the tool connects to Ollama at `http://localhost:11434`. Override with:

```powershell
$env:OLLAMA_HOST="http://your-host:11434"
```

## Streamlit App

Interactive UI with tabs for docstrings, UML, and chat:
```powershell
streamlit run app.py
```

## Example Output

```
============================================================
SEMANTIC IMPACT ANALYSIS REPORT
============================================================

Analyzed 3 changed function(s).
Total downstream functions affected: 12
⚠️  1 HIGH/CRITICAL risk change(s) detected!
⚡ 2 medium risk changes.

🔴 parse_config (Critical) — 8 downstream
🟡 validate_input (Medium) — 3 downstream
🟢 format_output (Low) — 1 downstream

Use --output markdown for full details.
```

## Architecture

```
ai_doc_layer/
├── ollama_client.py      # Ollama/deepseek-coder integration
├── call_graph.py         # AST-based call-graph builder
├── impact_analyzer.py    # Core semantic impact engine
├── cli.py                # Click-based CLI
├── code_parser.py        # Python AST extraction
├── doc_generator.py      # Docstring generation
├── search_index.py       # TF-IDF search for Q&A
└── ...
```

## Why This Shouldn't Already Exist

| Tool | Limitation |
|------|------------|
| Linters/Type Checkers | Don't reason about behavioral intent |
| Unit Tests | Only catch what they cover |
| CodeRabbit/Copilot Review | Analyze diffs superficially, no impact tracing |
| This Tool | **Fuses call-graph + LLM semantic reasoning, runs fully local** |

## License

See `LICENSE` for details.