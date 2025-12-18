#!/usr/bin/env python3
"""
示例脚本：扫描 aports 仓库并生成依赖图

使用方法:
    python examples/quick_scan.py /path/to/aports
"""

import sys
import os

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dep_map import AportsScanner, DependencyGraph, Visualizer, DependencyAnalyzer


def main():
    if len(sys.argv) < 2:
        print("Usage: python quick_scan.py <aports_path> [package_name]")
        print("\nExamples:")
        print("  python quick_scan.py /path/to/aports")
        print("  python quick_scan.py /path/to/aports curl")
        sys.exit(1)
    
    aports_path = sys.argv[1]
    target_package = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"🔍 Scanning aports repository: {aports_path}")
    print()
    
    # 创建扫描器
    scanner = AportsScanner(aports_path, repos=["main", "community"])
    
    # 扫描
    def progress(current, total, name):
        if current % 100 == 0 or current == total:
            print(f"\r  Progress: {current}/{total} packages", end='', flush=True)
    
    result = scanner.scan(progress_callback=progress)
    print()
    print()
    
    # 显示统计
    stats = scanner.get_statistics()
    print("📊 Scan Results:")
    print(f"  Total packages: {stats['total_packages']}")
    print(f"  Scan time: {result.scan_time:.2f}s")
    print(f"  By repository:")
    for repo, count in stats['by_repo'].items():
        print(f"    - {repo}: {count}")
    print()
    
    # 构建依赖图
    print("🔗 Building dependency graph...")
    graph = DependencyGraph(scanner.get_all_packages())
    
    graph_stats = graph.get_statistics()
    print(f"  Nodes: {graph_stats['nodes']}")
    print(f"  Edges: {graph_stats['edges']}")
    print(f"  Is DAG: {graph_stats['is_dag']}")
    print()
    
    # 分析
    analyzer = DependencyAnalyzer(graph)
    
    # 最被依赖的包
    print("🏆 Most depended packages:")
    most_depended = graph.get_most_depended(10)
    for i, (pkg, count) in enumerate(most_depended, 1):
        print(f"  {i}. {pkg}: {count} dependents")
    print()
    
    # 如果指定了目标包
    if target_package:
        if target_package not in graph.packages:
            print(f"❌ Package '{target_package}' not found")
            sys.exit(1)
        
        pkg = graph.packages[target_package]
        analysis = analyzer.analyze_package(target_package)
        
        print(f"📦 Package: {target_package}")
        print(f"  Version: {pkg.version}-r{pkg.release}")
        print(f"  Repository: {pkg.repo}")
        print(f"  Description: {pkg.description[:80]}..." if pkg.description else "  Description: N/A")
        print()
        
        if analysis:
            print("  Dependencies:")
            print(f"    Direct: {analysis.direct_deps_count}")
            print(f"    Total (recursive): {analysis.total_deps_count}")
            print(f"    Runtime: {analysis.runtime_deps_count}")
            print(f"    Build: {analysis.build_deps_count}")
            print()
            print("  Reverse dependencies:")
            print(f"    Direct: {analysis.direct_rdeps_count}")
            print(f"    Total: {analysis.total_rdeps_count}")
            print()
        
        # 生成可视化
        output_file = f"{target_package}-deps.html"
        print(f"🎨 Generating visualization: {output_file}")
        
        viz = Visualizer(graph)
        viz.render_html(target_package, output_file, max_depth=3)
        
        print(f"  ✅ Open {output_file} in your browser")
    else:
        # 生成全局概览
        output_file = "dependency-overview.html"
        print(f"🎨 Generating overview visualization: {output_file}")
        
        viz = Visualizer(graph)
        viz.render_full_graph_html(output_file, max_nodes=200)
        
        print(f"  ✅ Open {output_file} in your browser")
    
    # 保存缓存
    cache_file = "packages-cache.json"
    print(f"\n💾 Saving cache to {cache_file}")
    scanner.save_to_json(cache_file)
    
    print("\n✨ Done!")


if __name__ == "__main__":
    main()
