#!/usr/bin/env python3
"""
示例脚本：分析特定包的依赖关系

使用方法:
    python examples/analyze_package.py <cache_file> <package_name>
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dep_map import AportsScanner, DependencyGraph, Visualizer, DependencyAnalyzer
from dep_map.graph import DependencyType


def print_tree(tree, indent=0):
    """递归打印依赖树"""
    prefix = "  " * indent
    marker = "├─" if indent > 0 else ""
    name = tree["name"]
    
    if tree.get("truncated"):
        print(f"{prefix}{marker} {name} ...")
        return
    
    print(f"{prefix}{marker} {name}")
    
    for i, child in enumerate(tree.get("children", [])):
        print_tree(child, indent + 1)


def main():
    if len(sys.argv) < 3:
        print("Usage: python analyze_package.py <cache_file> <package_name>")
        print("\nExample:")
        print("  python analyze_package.py packages-cache.json curl")
        sys.exit(1)
    
    cache_file = sys.argv[1]
    package_name = sys.argv[2]
    
    # 加载缓存
    print(f"📂 Loading cache from {cache_file}...")
    scanner = AportsScanner(".")
    scanner.load_from_json(cache_file)
    
    # 构建图
    graph = DependencyGraph(scanner.get_all_packages())
    analyzer = DependencyAnalyzer(graph)
    
    # 检查包是否存在
    if package_name not in graph.packages:
        print(f"❌ Package '{package_name}' not found")
        
        # 尝试模糊匹配
        matches = [n for n in graph.packages if package_name.lower() in n.lower()]
        if matches:
            print(f"\nDid you mean:")
            for m in matches[:10]:
                print(f"  - {m}")
        sys.exit(1)
    
    pkg = graph.packages[package_name]
    analysis = analyzer.analyze_package(package_name)
    
    # 打印包信息
    print()
    print("=" * 60)
    print(f"📦 {package_name} {pkg.version}-r{pkg.release}")
    print("=" * 60)
    print()
    
    print(f"Repository: {pkg.repo}")
    print(f"License: {pkg.license}")
    print(f"URL: {pkg.url}")
    if pkg.description:
        print(f"\nDescription:\n  {pkg.description}")
    if pkg.maintainer:
        print(f"\nMaintainer: {pkg.maintainer}")
    
    print()
    print("-" * 60)
    print("📊 Dependency Statistics")
    print("-" * 60)
    
    if analysis:
        print(f"\n  Dependencies:")
        print(f"    Direct:    {analysis.direct_deps_count}")
        print(f"    Recursive: {analysis.total_deps_count}")
        print(f"    Runtime:   {analysis.runtime_deps_count}")
        print(f"    Build:     {analysis.build_deps_count}")
        
        print(f"\n  Reverse Dependencies (who depends on this):")
        print(f"    Direct:    {analysis.direct_rdeps_count}")
        print(f"    Recursive: {analysis.total_rdeps_count}")
        
        print(f"\n  Package Type:")
        if analysis.is_core:
            print("    🌟 Core package (heavily depended)")
        if analysis.is_leaf:
            print("    🍃 Leaf package (not depended by others)")
        if analysis.is_root:
            print("    🌱 Root package (no dependencies)")
    
    # 运行时依赖
    print()
    print("-" * 60)
    print("🔗 Runtime Dependencies")
    print("-" * 60)
    
    runtime_deps = graph.get_dependencies(package_name, dep_type=DependencyType.RUNTIME)
    if runtime_deps:
        for dep in runtime_deps:
            dep_pkg = graph.packages.get(dep)
            repo = f"[{dep_pkg.repo}]" if dep_pkg else ""
            print(f"  • {dep} {repo}")
    else:
        print("  (none)")
    
    # 构建依赖
    print()
    print("-" * 60)
    print("🔨 Build Dependencies")
    print("-" * 60)
    
    build_deps = graph.get_dependencies(package_name, dep_type=DependencyType.BUILD)
    if build_deps:
        for dep in build_deps:
            dep_pkg = graph.packages.get(dep)
            repo = f"[{dep_pkg.repo}]" if dep_pkg else ""
            print(f"  • {dep} {repo}")
    else:
        print("  (none)")
    
    # 依赖树
    print()
    print("-" * 60)
    print("🌳 Dependency Tree (depth=3)")
    print("-" * 60)
    print()
    
    tree = graph.get_dependency_tree(package_name, max_depth=3)
    print_tree(tree)
    
    # 被依赖列表
    print()
    print("-" * 60)
    print("📥 Packages that depend on this (top 20)")
    print("-" * 60)
    
    rdeps = graph.get_reverse_dependencies(package_name)
    if rdeps:
        for dep in rdeps[:20]:
            dep_pkg = graph.packages.get(dep)
            repo = f"[{dep_pkg.repo}]" if dep_pkg else ""
            print(f"  • {dep} {repo}")
        if len(rdeps) > 20:
            print(f"  ... and {len(rdeps) - 20} more")
    else:
        print("  (none)")
    
    # 生成可视化
    print()
    print("-" * 60)
    print("🎨 Generating Visualizations")
    print("-" * 60)
    
    viz = Visualizer(graph)
    
    # 依赖图
    deps_file = f"{package_name}-dependencies.html"
    viz.render_html(package_name, deps_file, max_depth=3)
    print(f"  ✅ Dependencies graph: {deps_file}")
    
    # 依赖树
    tree_file = f"{package_name}-tree.html"
    viz.render_tree_html(package_name, tree_file, max_depth=4)
    print(f"  ✅ Dependency tree: {tree_file}")
    
    # D3 力导向图
    d3_file = f"{package_name}-d3.html"
    viz.render_d3_html(package_name, d3_file, max_depth=3)
    print(f"  ✅ D3 force graph: {d3_file}")
    
    print()
    print("✨ Done! Open the HTML files in your browser to explore.")


if __name__ == "__main__":
    main()
