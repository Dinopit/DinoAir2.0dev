"""
Static import cycle checker for DinoAir 2.0

Scans Python modules under specified package roots (default: src, pseudocode_translator),
builds an import graph using AST, and reports any cycles found. Exits with code 0 when
no cycles are detected; otherwise exits with code 1.

Usage:
    python tests/import_cycle_check.py
    python tests/import_cycle_check.py --packages src pseudocode_translator
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set


def discover_modules(root: Path, package_roots: List[str]) -> Dict[str, Path]:
    modules: Dict[str, Path] = {}
    for pkg in package_roots:
        base = root / pkg
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            rel = path.relative_to(root).with_suffix("")
            parts = list(rel.parts)
            # Ensure module path uses dots
            mod = ".".join(parts)
            modules[mod] = path
    return modules


def resolve_relative(module: str, level: int, name: str | None) -> str | None:
    parts = module.split(".")
    if level > len(parts):
        return None
    base = parts[: len(parts) - level]
    if name:
        base += name.split(".")
    if not base:
        return None
    return ".".join(base)


def build_import_graph(modules: Dict[str, Path]) -> Dict[str, Set[str]]:
    graph: Dict[str, Set[str]] = defaultdict(set)
    mod_names = set(modules.keys())
    for mod, path in modules.items():
        try:
            src = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(src, filename=str(path))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = alias.name
                    if any(target == m or target.startswith(m + ".") for m in mod_names):
                        graph[mod].add(target)
            elif isinstance(node, ast.ImportFrom):
                if node.level and node.level > 0:
                    abs_base = resolve_relative(mod, node.level, node.module)
                else:
                    abs_base = node.module
                if abs_base and any(abs_base == m or abs_base.startswith(m + ".") for m in mod_names):
                    graph[mod].add(abs_base)
    return graph


def find_cycles(graph: Dict[str, Set[str]]) -> List[List[str]]:
    visited: Set[str] = set()
    stack: Set[str] = set()
    parent: Dict[str, str] = {}
    cycles: List[List[str]] = []

    def dfs(u: str):
        visited.add(u)
        stack.add(u)
        for v in graph.get(u, ()):  
            if v not in visited:
                parent[v] = u
                dfs(v)
            elif v in stack:
                cycle = [v]
                x = u
                while x != v and x in parent:
                    cycle.append(x)
                    x = parent[x]
                cycle.append(v)
                cycle.reverse()
                if cycle not in cycles:
                    cycles.append(cycle)
        stack.remove(u)

    for node in list(graph.keys()):
        if node not in visited:
            dfs(node)
    return cycles


def main() -> int:
    parser = argparse.ArgumentParser(description="Import cycle checker")
    parser.add_argument(
        "--packages",
        nargs="*",
        default=["src", "pseudocode_translator"],
        help="Top-level package roots to scan",
    )
    args = parser.parse_args()

    root = Path(__file__).parent.parent
    modules = discover_modules(root, args.packages)
    graph = build_import_graph(modules)
    cycles = find_cycles(graph)

    if not cycles:
        print("No import cycles detected.")
        return 0

    print("Detected import cycles (within project modules):")
    for i, cycle in enumerate(cycles, 1):
        print(f"  {i}. " + " -> ".join(cycle))
    return 1


if __name__ == "__main__":
    sys.exit(main())
