# cli.py
from pathlib import Path
from typing import Optional

import click
import requests

from .code_parser import find_python_files, extract_functions_from_file
from .diff_analyzer import get_changed_files, get_diff_text
from .doc_generator import DocGenerator
from .writer import inject_docstrings_into_file, write_module_markdown
from .uml_generator import generate_repo_uml
from .ask_cli import CodebaseAssistant
from .impact_analyzer import (
    ImpactAnalyzer,
    generate_impact_report_markdown,
    generate_impact_report_json,
)
from .validation import (
    validate_directory_path,
    validate_positive_integer,
    check_ollama_connection,
    validate_git_repository
)


@click.group()
def cli():
    pass


@cli.command()
@click.argument("repo", type=click.Path(exists=True, file_okay=False))
@click.option("--only-changed", is_flag=True, help="Only process files changed in last commit.")
def generate(repo: str, only_changed: bool):
    """Generate documentation for Python files in the repository."""
    try:
        repo_path = validate_directory_path(repo)
    except (ValueError, FileNotFoundError) as e:
        click.echo(f"❌ Invalid repository path: {e}", err=True)
        return
    
    # Check Ollama connection
    is_connected, error_msg = check_ollama_connection()
    if not is_connected:
        click.echo(f"❌ {error_msg}", err=True)
        return
    
    click.echo(f"Using repo: {repo_path}")

    doc_gen = DocGenerator()

    if only_changed:
        files = get_changed_files(repo_path)
        if not files:
            click.echo("No changed Python files detected between HEAD~1 and HEAD.")
            return
    else:
        files = find_python_files(repo_path)

    click.echo(f"Found {len(files)} Python files to process.")

    for file_path in files:
        click.echo(f"Processing {file_path} ...")
        functions = extract_functions_from_file(file_path)
        if not functions:
            continue

        func_docs = {}
        for func in functions:
            ds = doc_gen.generate_docstring(func, file_path)
            func_docs[func.lineno] = ds

        inject_docstrings_into_file(file_path, func_docs)

        module_md = doc_gen.generate_module_overview(file_path, functions)
        write_module_markdown(repo_path, file_path, module_md, functions)

    click.echo("Documentation generation completed.")


@cli.command()
@click.argument("repo", type=click.Path(exists=True, file_okay=False))
def summarize_last_commit(repo: str):
    repo_path = Path(repo).resolve()
    doc_gen = DocGenerator()
    diff_text = get_diff_text(repo_path)
    summary = doc_gen.generate_commit_summary(diff_text)
    click.echo(summary)


@cli.command()
@click.argument("repo", type=click.Path(exists=True, file_okay=False))
@click.option("--out-dir", type=click.Path(), default=None)
@click.option("--no-render", is_flag=True)
def generate_uml(repo: str, out_dir: Optional[str], no_render: bool):
    repo_path = Path(repo).resolve()
    docs_root = repo_path / "ai_docs"
    out = Path(out_dir).resolve() if out_dir else docs_root / "diagrams"
    click.echo(f"Generating UML diagrams into {out} ...")
    generate_repo_uml(repo_path, out, render_png=(not no_render))
    click.echo("UML generation completed.")


@cli.command()
@click.argument("repo", type=click.Path(exists=True, file_okay=False))
@click.argument("question", type=str)
@click.option("--top-k", type=int, default=4)
def ask(repo: str, question: str, top_k: int):
    repo_path = Path(repo).resolve()
    click.echo(f"Asking against {repo_path}: {question}")
    assistant = CodebaseAssistant(repo_path)
    resp = assistant.ask(question, top_k=top_k)
    click.echo("\n---- Answer ----\n")
    click.echo(resp)


@cli.command()
@click.argument("repo", type=click.Path(exists=True, file_okay=False))
@click.option("--base", default="HEAD~1")
@click.option("--target", default="HEAD")
@click.option("--depth", default=3, type=int)
@click.option("--output", type=click.Choice(["markdown", "json", "console"]), default="console")
@click.option("--out-file", type=click.Path(), default=None)
def analyze_impact(repo: str, base: str, target: str, depth: int, output: str, out_file: Optional[str]):
    """Analyze the downstream impact of code changes between commits."""
    try:
        repo_path = validate_directory_path(repo)
        validate_git_repository(repo_path)
        depth = validate_positive_integer(depth, "depth", min_value=1)
    except (ValueError, FileNotFoundError) as e:
        click.echo(f"❌ Invalid input: {e}", err=True)
        return
    
    click.echo(f"🔍 Analyzing impact: {base}..{target} in {repo_path}")

    try:
        analyzer = ImpactAnalyzer(repo_path)
        report = analyzer.analyze_commit(base=base, target=target, max_downstream_depth=depth)
    except requests.exceptions.ConnectionError:
        click.echo("❌ Cannot connect to Ollama. Make sure Ollama is running:", err=True)
        click.echo("   ollama serve", err=True)
        click.echo("   ollama pull deepseek-coder:6.7b", err=True)
        return
    except (OSError, ValueError, RuntimeError) as e:
        click.echo(f"❌ Analysis failed: {e}", err=True)
        return

    if output == "json":
        result = generate_impact_report_json(report)
    elif output == "markdown":
        result = generate_impact_report_markdown(report)
    else:
        lines = [
            "",
            "=" * 60,
            "SEMANTIC IMPACT ANALYSIS REPORT",
            "=" * 60,
            "",
            report.summary,
            "",
        ]
        for r in report.function_reports:
            risk_emoji = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}.get(r.risk_score, "⚪")
            lines.append(f"{risk_emoji} {r.function_name} ({r.risk_score}) — {r.downstream_count} downstream")
        lines.append("")
        lines.append("Use --output markdown or --output json for full details.")
        result = "\n".join(lines)

    if out_file:
        Path(out_file).write_text(result, encoding="utf-8")
        click.echo(f"✅ Report written to {out_file}")
    else:
        click.echo(result)


@cli.command()
@click.argument("repo", type=click.Path(exists=True, file_okay=False))
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--depth", default=3, type=int)
def analyze_file_impact(repo: str, file_path: str, depth: int):
    repo_path = Path(repo).resolve()
    fpath = Path(file_path).resolve()

    click.echo(f"📊 Analyzing downstream impact for {fpath.name}")

    try:
        analyzer = ImpactAnalyzer(repo_path)
        reports = analyzer.analyze_file(fpath)
    except (OSError, ValueError, RuntimeError) as e:
        click.echo(f"❌ Error: {e}", err=True)
        return

    if not reports:
        click.echo("No functions found in file.")
        return

    click.echo(f"\nFound {len(reports)} function(s):\n")
    for r in reports:
        click.echo(f"  • {r.function_name} (line {r.lineno}) — {r.downstream_count} downstream callers")
        for fpath_d, fname, lno in r.downstream_functions[:5]:
            click.echo(f"      └─ {fname} in {Path(fpath_d).name}:{lno}")
        if r.downstream_count > 5:
            click.echo(f"      └─ ... and {r.downstream_count - 5} more")


@cli.command()
@click.argument("repo", type=click.Path(exists=True, file_okay=False))
@click.option("--out-file", type=click.Path(), default=None)
def build_call_graph(repo: str, out_file: Optional[str]):
    from .call_graph import build_call_graph as build_cg
    import json

    repo_path = Path(repo).resolve()
    click.echo(f"🔗 Building call graph for {repo_path}")

    graph = build_cg(repo_path)
    click.echo(f"Found {len(graph)} functions.\n")

    most_called = sorted(graph.values(), key=lambda f: len(f.called_by), reverse=True)[:10]
    click.echo("Top 10 most-called functions:")
    for fn in most_called:
        click.echo(f"  • {fn.name} — called by {len(fn.called_by)} functions")

    if out_file:
        data = {
            qn: {
                "file": str(fn.file_path),
                "lineno": fn.lineno,
                "calls": list(fn.calls),
                "called_by": list(fn.called_by),
            }
            for qn, fn in graph.items()
        }
        Path(out_file).write_text(json.dumps(data, indent=2), encoding="utf-8")
        click.echo(f"\n✅ Call graph written to {out_file}")
