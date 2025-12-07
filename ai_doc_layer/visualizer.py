# visualizer.py
from pathlib import Path
import ast
import pydot
from typing import Dict, List, Set, Optional


class UMLGenerator:
    def __init__(self):
        self.class_map: Dict[str, dict] = {}
        self.functions_map: Dict[str, List[str]] = {}
        self.dependencies: Dict[str, Set[str]] = {}
        self.imports_map: Dict[str, Set[str]] = {}

    def _get_base_name(self, base) -> Optional[str]:
        if isinstance(base, ast.Name):
            return base.id
        if isinstance(base, ast.Attribute):
            parts = []
            node = base
            while isinstance(node, ast.Attribute):
                parts.append(node.attr)
                node = node.value
            if isinstance(node, ast.Name):
                parts.append(node.id)
            parts.reverse()
            return ".".join(parts)
        return None

    def _extract_dependencies(self, node: ast.AST, class_name: str):
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and child.id in self.class_map:
                if child.id != class_name:
                    self.dependencies.setdefault(class_name, set()).add(child.id)
            elif isinstance(child, ast.Attribute):
                if isinstance(child.value, ast.Name):
                    target = child.value.id
                    if target in self.class_map and target != class_name:
                        self.dependencies.setdefault(class_name, set()).add(target)

    def _parse_file(self, file_path: Path):
        src = file_path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        fname = str(file_path)

        local_classes = {}
        local_functions = []
        local_imports = set()

        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    local_imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    local_imports.add(node.module.split('.')[0])

            elif isinstance(node, ast.ClassDef):
                cname = node.name
                methods = []
                attributes = []

                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        methods.append(item.name)
                    elif isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                attributes.append(target.id)

                bases = []
                for b in node.bases:
                    base = self._get_base_name(b)
                    if base:
                        bases.append(base)

                local_classes[cname] = {
                    "file": fname,
                    "methods": methods,
                    "attributes": attributes,
                    "bases": bases,
                    "node": node
                }

            elif isinstance(node, ast.FunctionDef):
                local_functions.append(node.name)

        for cname, info in local_classes.items():
            self.class_map[cname] = info

        self.functions_map[fname] = local_functions
        self.imports_map[fname] = local_imports

    def _analyze_dependencies(self):
        for cname, info in self.class_map.items():
            self._extract_dependencies(info["node"], cname)

    def generate(self, repo: Path, out_png: Path):
        for py_file in repo.rglob("*.py"):
            rel_parts = py_file.relative_to(repo).parts
            if any(p.startswith(".") or p in ("venv", ".venv", "__pycache__", "build", "dist") for p in rel_parts):
                continue
            try:
                self._parse_file(py_file)
            except (SyntaxError, OSError, ValueError):
                continue

        self._analyze_dependencies()

        graph = pydot.Dot(
            "UML",
            graph_type="digraph",
            rankdir="TB",
            splines="ortho",
            nodesep="0.8",
            ranksep="1.0",
            fontname="Helvetica",
            bgcolor="#FAFAFA"
        )

        graph.set_node_defaults(fontname="Helvetica", fontsize="11")
        graph.set_edge_defaults(fontname="Helvetica", fontsize="9")

        file_clusters = {}

        for cname, info in self.class_map.items():
            fname = info["file"]
            short_fname = Path(fname).name

            if fname not in file_clusters:
                file_clusters[fname] = pydot.Cluster(
                    f"cluster_{short_fname.replace('.', '_')}",
                    label=short_fname,
                    style="rounded,filled",
                    fillcolor="#E8EAF6",
                    color="#5C6BC0",
                    fontcolor="#283593",
                    fontsize="12",
                    fontname="Helvetica-Bold"
                )

            attr_rows = ""
            if info.get("attributes"):
                for attr in info["attributes"][:5]:
                    attr_rows += f'<TR><TD ALIGN="LEFT" BGCOLOR="#F5F5F5"><FONT COLOR="#666666">+ {attr}</FONT></TD></TR>'
                if len(info["attributes"]) > 5:
                    attr_rows += f'<TR><TD ALIGN="LEFT" BGCOLOR="#F5F5F5"><FONT COLOR="#999999">... +{len(info["attributes"])-5} more</FONT></TD></TR>'

            method_rows = ""
            public_methods = [m for m in info["methods"] if not m.startswith("_")]
            private_methods = [m for m in info["methods"] if m.startswith("_") and not m.startswith("__")]
            dunder_methods = [m for m in info["methods"] if m.startswith("__")]

            for m in public_methods[:8]:
                method_rows += f'<TR><TD ALIGN="LEFT" BGCOLOR="#FFFFFF"><FONT COLOR="#1565C0">+ {m}()</FONT></TD></TR>'
            for m in private_methods[:3]:
                method_rows += f'<TR><TD ALIGN="LEFT" BGCOLOR="#FFFFFF"><FONT COLOR="#7B1FA2">- {m}()</FONT></TD></TR>'
            
            total = len(info["methods"])
            shown = min(len(public_methods), 8) + min(len(private_methods), 3)
            if total > shown:
                method_rows += f'<TR><TD ALIGN="LEFT" BGCOLOR="#FFFFFF"><FONT COLOR="#999999">... +{total-shown} more</FONT></TD></TR>'

            label = f'''<
<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="6">
<TR><TD BGCOLOR="#3F51B5" COLSPAN="1"><FONT COLOR="white"><B>{cname}</B></FONT></TD></TR>
{attr_rows}
{method_rows if method_rows else '<TR><TD BGCOLOR="#FFFFFF"><FONT COLOR="#999999">(no methods)</FONT></TD></TR>'}
</TABLE>
>'''

            node = pydot.Node(
                cname,
                label=label,
                shape="plaintext"
            )
            file_clusters[fname].add_node(node)

        for cluster in file_clusters.values():
            graph.add_subgraph(cluster)

        for cname, info in self.class_map.items():
            for base in info["bases"]:
                if base in self.class_map:
                    graph.add_edge(
                        pydot.Edge(
                            base,
                            cname,
                            arrowhead="onormal",
                            arrowtail="none",
                            style="solid",
                            color="#4CAF50",
                            penwidth="2.0",
                            label="extends",
                            fontcolor="#2E7D32",
                            fontsize="9"
                        )
                    )

        for cname, deps in self.dependencies.items():
            for dep in deps:
                if dep in self.class_map and dep not in self.class_map.get(cname, {}).get("bases", []):
                    graph.add_edge(
                        pydot.Edge(
                            cname,
                            dep,
                            arrowhead="vee",
                            style="dashed",
                            color="#FF9800",
                            penwidth="1.5",
                            label="uses",
                            fontcolor="#E65100",
                            fontsize="8"
                        )
                    )

        if self.functions_map:
            standalone_funcs = []
            for fname, funcs in self.functions_map.items():
                if funcs:
                    short_name = Path(fname).stem
                    public_funcs = [f for f in funcs if not f.startswith("_")][:5]
                    if public_funcs:
                        standalone_funcs.append((short_name, public_funcs))

            if standalone_funcs:
                func_cluster = pydot.Cluster(
                    "cluster_functions",
                    label="Module Functions",
                    style="rounded,filled",
                    fillcolor="#FFF3E0",
                    color="#FF9800",
                    fontcolor="#E65100",
                    fontsize="12",
                    fontname="Helvetica-Bold"
                )

                for module_name, funcs in standalone_funcs[:5]:
                    func_rows = "".join([f'<TR><TD ALIGN="LEFT"><FONT COLOR="#1565C0">{f}()</FONT></TD></TR>' for f in funcs])
                    label = f'''<
<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">
<TR><TD BGCOLOR="#FFB74D"><B>{module_name}</B></TD></TR>
{func_rows}
</TABLE>
>'''
                    func_cluster.add_node(pydot.Node(
                        f"module_{module_name}",
                        label=label,
                        shape="plaintext"
                    ))

                graph.add_subgraph(func_cluster)

        graph.write(str(out_png), format='png')
