# impact_analyzer.py
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import json
import requests

from .call_graph import build_call_graph, get_downstream_dependents, get_upstream_dependencies, FunctionNode
from .diff_analyzer import get_changed_files, get_diff_text
from .code_parser import extract_functions_from_file, FunctionInfo
from .ollama_client import OllamaClient


@dataclass
class ImpactReport:
    function_name: str
    file_path: str
    lineno: int
    changed_code: str
    downstream_count: int
    downstream_functions: List[Tuple[str, str, int]]
    upstream_count: int
    upstream_functions: List[Tuple[str, str, int]]
    risk_analysis: str
    risk_score: str


@dataclass
class FullImpactReport:
    repo_path: str
    commit_range: str
    changed_files: List[str]
    function_reports: List[ImpactReport]
    summary: str
    total_downstream_affected: int


class ImpactAnalyzer:

    def __init__(self, repo_path: Path, llm_client: Optional[OllamaClient] = None):
        self.repo_path = repo_path
        self.llm: Optional[OllamaClient] = llm_client or OllamaClient()
        self.call_graph: Dict[str, FunctionNode] = {}

    def build_graph(self):
        self.call_graph = build_call_graph(self.repo_path)

    def _find_changed_functions(self, changed_files: List[Path]) -> List[Tuple[FunctionInfo, Path]]:
        result = []
        for fpath in changed_files:
            if not fpath.exists():
                continue
            try:
                funcs = extract_functions_from_file(fpath)
                for f in funcs:
                    result.append((f, fpath))
            except (SyntaxError, OSError, ValueError):
                continue
        return result

    def _match_function_to_graph(self, func: FunctionInfo, file_path: Path) -> Optional[str]:
        rel = file_path.relative_to(self.repo_path)
        module = str(rel.with_suffix("")).replace("/", ".").replace("\\", ".")
        
        candidates = [
            f"{module}.{func.name}",
            func.name,
        ]
        
        for candidate in candidates:
            if candidate in self.call_graph:
                return candidate
        
        for qn, node in self.call_graph.items():
            if node.name == func.name and node.file_path == file_path:
                return qn
        
        return None

    def analyze_commit(
        self,
        base: str = "HEAD~1",
        target: str = "HEAD",
        max_downstream_depth: int = 3,
    ) -> FullImpactReport:
        self.build_graph()

        changed_files = get_changed_files(self.repo_path, base, target)
        if not changed_files:
            return FullImpactReport(
                repo_path=str(self.repo_path),
                commit_range=f"{base}..{target}",
                changed_files=[],
                function_reports=[],
                summary="No Python files changed.",
                total_downstream_affected=0,
            )

        diff_text = get_diff_text(self.repo_path, base, target)
        changed_funcs = self._find_changed_functions(changed_files)

        function_reports: List[ImpactReport] = []
        all_downstream: set = set()

        for func, fpath in changed_funcs:
            qname = self._match_function_to_graph(func, fpath)
            
            if qname:
                dependents = get_downstream_dependents(
                    self.call_graph, [qname], max_depth=max_downstream_depth
                )
                # Get upstream dependencies
                upstream = get_upstream_dependencies(
                    self.call_graph, qname, max_depth=max_downstream_depth
                )
            else:
                dependents = []
                upstream = []

            downstream_info = [
                (str(d.file_path), d.name, d.lineno) for d in dependents
            ]
            upstream_info = [
                (str(u.file_path), u.name, u.lineno) for u in upstream
            ]
            all_downstream.update(d.qualified_name for d in dependents)

            downstream_snippets = [
                (str(d.file_path.name), d.name, d.code[:2000])
                for d in dependents[:10]
            ]

            if downstream_snippets and self.llm:
                try:
                    analysis = self.llm.analyze_impact(
                        changed_code=func.code[:3000],
                        downstream_snippets=downstream_snippets,
                        diff_context=diff_text[:2000] if diff_text else "",
                    )
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, RuntimeError) as e:
                    analysis = f"Error during LLM analysis: {e}"
            elif downstream_snippets:
                analysis = f"Found {len(dependents)} downstream dependencies. Enable LLM for detailed semantic analysis."
            else:
                analysis = "No downstream dependents found. This function appears to be a leaf node or entry point."

            risk_score = self._extract_risk_score(analysis)

            report = ImpactReport(
                function_name=func.name,
                file_path=str(fpath),
                lineno=func.lineno,
                changed_code=func.code[:500] + ("..." if len(func.code) > 500 else ""),
                downstream_count=len(dependents),
                downstream_functions=downstream_info,
                upstream_count=len(upstream),
                upstream_functions=upstream_info,
                risk_analysis=analysis,
                risk_score=risk_score,
            )
            function_reports.append(report)

        summary = self._generate_summary(function_reports, len(all_downstream))

        return FullImpactReport(
            repo_path=str(self.repo_path),
            commit_range=f"{base}..{target}",
            changed_files=[str(f) for f in changed_files],
            function_reports=function_reports,
            summary=summary,
            total_downstream_affected=len(all_downstream),
        )

    def analyze_file(self, file_path: Path, max_depth: int = 3) -> FullImpactReport:
        """Analyze a single file and return impact report."""
        if not self.call_graph:
            self.build_graph()

        funcs = extract_functions_from_file(file_path)
        reports = []
        all_downstream = set()

        for func in funcs:
            qname = self._match_function_to_graph(func, file_path)

            if qname:
                dependents = get_downstream_dependents(
                    self.call_graph, [qname], max_depth=max_depth
                )
                # Get upstream dependencies
                upstream = get_upstream_dependencies(
                    self.call_graph, qname, max_depth=max_depth
                )
            else:
                dependents = []
                upstream = []

            downstream_info = [(d.name, str(d.file_path) if d.file_path else "", d.lineno) for d in dependents]
            upstream_info = [(u.name, str(u.file_path) if u.file_path else "", u.lineno) for u in upstream]
            all_downstream.update(d.name for d in dependents)

            # Determine risk based on downstream count
            if len(dependents) >= 5:
                risk_score = "High"
            elif len(dependents) >= 2:
                risk_score = "Medium"
            elif len(dependents) >= 1:
                risk_score = "Low"
            else:
                risk_score = "None"

            report = ImpactReport(
                function_name=func.name,
                file_path=str(file_path),
                lineno=func.lineno,
                changed_code=func.code[:500] if func.code else "",
                downstream_count=len(dependents),
                downstream_functions=downstream_info,
                upstream_count=len(upstream),
                upstream_functions=upstream_info,
                risk_analysis="",
                risk_score=risk_score,
            )
            reports.append(report)

        return FullImpactReport(
            repo_path=str(self.repo_path),
            commit_range="file-analysis",
            changed_files=[str(file_path)],
            function_reports=reports,
            summary=self._generate_summary(reports, len(all_downstream)),
            total_downstream_affected=len(all_downstream),
        )

    def _extract_risk_score(self, analysis: str) -> str:
        analysis_lower = analysis.lower()
        if "critical" in analysis_lower:
            return "Critical"
        elif "high" in analysis_lower and "risk" in analysis_lower:
            return "High"
        elif "medium" in analysis_lower:
            return "Medium"
        elif "low" in analysis_lower:
            return "Low"
        return "Unknown"

    def _generate_summary(self, reports: List[ImpactReport], total_downstream: int) -> str:
        if not reports:
            return "No functions analyzed."

        high_risk = sum(1 for r in reports if r.risk_score in ("High", "Critical"))
        medium_risk = sum(1 for r in reports if r.risk_score == "Medium")

        lines = [
            f"Analyzed {len(reports)} changed function(s).",
            f"Total downstream functions affected: {total_downstream}",
        ]

        if high_risk > 0:
            lines.append(f"⚠️  {high_risk} HIGH/CRITICAL risk change(s) detected!")
        if medium_risk > 0:
            lines.append(f"⚡ {medium_risk} medium risk change(s).")
        if high_risk == 0 and medium_risk == 0:
            lines.append("✅ No significant risks detected.")

        return "\n".join(lines)


def generate_impact_report_json(report: FullImpactReport) -> str:
    return json.dumps(
        {
            "repo_path": report.repo_path,
            "commit_range": report.commit_range,
            "changed_files": report.changed_files,
            "summary": report.summary,
            "total_downstream_affected": report.total_downstream_affected,
            "function_reports": [
                {
                    "function_name": r.function_name,
                    "file_path": r.file_path,
                    "lineno": r.lineno,
                    "downstream_count": r.downstream_count,
                    "risk_score": r.risk_score,
                    "downstream_functions": r.downstream_functions,
                    "risk_analysis": r.risk_analysis,
                }
                for r in report.function_reports
            ],
        },
        indent=2,
    )


def generate_impact_report_markdown(report: FullImpactReport) -> str:
    lines = [
        "# Semantic Impact Analysis Report",
        "",
        f"**Repository:** `{report.repo_path}`",
        f"**Commit Range:** `{report.commit_range}`",
        f"**Changed Files:** {len(report.changed_files)}",
        f"**Total Downstream Affected:** {report.total_downstream_affected}",
        "",
        "## Summary",
        "",
        report.summary,
        "",
        "---",
        "",
        "## Function-by-Function Analysis",
        "",
    ]

    for r in report.function_reports:
        risk_emoji = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}.get(
            r.risk_score, "⚪"
        )

        lines.extend([
            f"### {risk_emoji} `{r.function_name}` ({r.file_path}:{r.lineno})",
            "",
            f"**Risk Score:** {r.risk_score}",
            f"**Downstream Dependents:** {r.downstream_count}",
            "",
        ])

        if r.downstream_functions:
            lines.append("**Affected Functions:**")
            for fpath, fname, lno in r.downstream_functions[:10]:
                lines.append(f"- `{fname}` in `{Path(fpath).name}:{lno}`")
            if len(r.downstream_functions) > 10:
                lines.append(f"- ... and {len(r.downstream_functions) - 10} more")
            lines.append("")

        lines.extend([
            "**Analysis:**",
            "",
            r.risk_analysis,
            "",
            "---",
            "",
        ])

    return "\n".join(lines)
