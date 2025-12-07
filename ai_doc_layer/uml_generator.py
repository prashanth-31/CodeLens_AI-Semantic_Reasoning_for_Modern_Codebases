# uml_generator.py
import ast
from pathlib import Path
from typing import Dict
import pydot


def parse_module(path: Path) -> Dict:
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    classes = {}
    functions = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            methods = []
            bases = [getattr(b, "id", getattr(b, "attr", "")) for b in node.bases]
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    methods.append(item.name)
            classes[node.name] = {"methods": methods, "bases": bases}
        elif isinstance(node, ast.FunctionDef):
            functions.append(node.name)
    return {"classes": classes, "functions": functions}


def module_to_dot(module_info: Dict, module_name: str) -> pydot.Dot:
    graph = pydot.Dot(graph_type="digraph", rankdir="LR")
    for cls, info in module_info["classes"].items():
        label = f"{cls}\\n" + "\\n".join(info["methods"][:10])
        node = pydot.Node(f"{module_name}.{cls}", label=label, shape="record")
        graph.add_node(node)
    for fn in module_info["functions"]:
        node = pydot.Node(f"{module_name}.{fn}", label=fn, shape="ellipse")
        graph.add_node(node)
    for cls, info in module_info["classes"].items():
        for base in info["bases"]:
            if base:
                edge = pydot.Edge(f"{module_name}.{base}", f"{module_name}.{cls}")
                graph.add_edge(edge)
    return graph


def generate_repo_uml(repo_path: Path, out_dir: Path, render_png: bool = True):
    out_dir.mkdir(parents=True, exist_ok=True)
    modules = []

    for py in repo_path.rglob("*.py"):
        try:
            mi = parse_module(py)
            if not mi["classes"] and not mi["functions"]:
                continue
            modules.append((py, mi))
        except Exception:
            continue

    for py, mi in modules:
        safe = str(py.relative_to(repo_path)).replace("/", "_").replace("\\", "_")
        module_name = py.stem

        dot = module_to_dot(mi, module_name)
        dot_path = out_dir / f"{safe}.dot"
        png_path = out_dir / f"{safe}.png"

        dot.write(str(dot_path), format='raw')

        if render_png:
            try:
                dot.write(str(png_path), format="png")
            except Exception as e:
                print(f"Error generating PNG for {py}: {e}")
