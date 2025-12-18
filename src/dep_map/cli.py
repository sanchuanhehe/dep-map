"""
命令行入口

提供 dep-map 命令行工具。
"""

import json
import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.tree import Tree

from .analyzer import DependencyAnalyzer
from .graph import DependencyGraph, DependencyType
from .scanner import AportsScanner
from .visualizer import Visualizer

console = Console()


def get_cache_path() -> Path:
    """获取缓存文件路径"""
    cache_dir = Path.home() / ".cache" / "dep-map"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "packages.json"


def load_or_scan(aports_path: str | None, use_cache: bool = True) -> DependencyGraph:
    """加载或扫描仓库"""
    cache_path = get_cache_path()

    # 尝试从缓存加载
    if use_cache and cache_path.exists() and not aports_path:
        console.print("[dim]Loading from cache...[/dim]")
        scanner = AportsScanner(".")
        scanner.load_from_json(str(cache_path))
        return DependencyGraph(scanner.get_all_packages())

    if not aports_path:
        console.print("[red]Error:[/red] No aports path specified and no cache found.")
        console.print("Run 'dep-map scan <aports_path>' first.")
        sys.exit(1)

    # 扫描仓库
    scanner = AportsScanner(aports_path)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Scanning aports...", total=None)

        def progress_callback(current, total, name):
            progress.update(task, completed=current, total=total, description=f"Scanning: {name}")

        result = scanner.scan(progress_callback=progress_callback)

    console.print(
        f"[green]✓[/green] Scanned {result.successful} packages in {result.scan_time:.2f}s"
    )

    if result.failed > 0:
        console.print(f"[yellow]Warning:[/yellow] {result.failed} packages failed to parse")

    # 保存缓存
    scanner.save_to_json(str(cache_path))
    console.print(f"[dim]Cache saved to {cache_path}[/dim]")

    return DependencyGraph(scanner.get_all_packages())


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Alpine Linux APK 依赖关系图谱工具"""
    pass


@main.command()
@click.argument("aports_path", type=click.Path(exists=True))
@click.option("--repos", "-r", multiple=True, default=["main", "community"], help="要扫描的仓库")
@click.option("--output", "-o", type=click.Path(), help="输出 JSON 文件路径")
def scan(aports_path: str, repos: tuple, output: str | None):
    """扫描 aports 仓库并构建依赖图谱"""
    console.print(
        Panel(f"[bold]Scanning aports repository[/bold]\n{aports_path}", border_style="blue")
    )

    scanner = AportsScanner(aports_path, repos=list(repos))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        task = progress.add_task("Scanning...", total=None)

        def progress_callback(current, total, name):
            progress.update(
                task, completed=current, total=total, description=f"[cyan]{name}[/cyan]"
            )

        result = scanner.scan(progress_callback=progress_callback)

    console.print()

    # 显示统计
    stats = scanner.get_statistics()

    table = Table(title="Scan Results", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Total Packages", str(stats["total_packages"]))
    table.add_row("Scan Time", f"{result.scan_time:.2f}s")
    table.add_row("Failed", str(result.failed))

    for repo, count in stats["by_repo"].items():
        table.add_row(f"  {repo}", str(count))

    table.add_row("Avg Dependencies", f"{stats['avg_dependencies']:.2f}")
    table.add_row(
        "Most Dependencies",
        f"{stats['max_dependencies_package']} ({stats['max_dependencies_count']})",
    )

    console.print(table)

    # 保存
    output_path = output or str(get_cache_path())
    scanner.save_to_json(output_path)
    console.print(f"\n[green]✓[/green] Saved to {output_path}")


@main.command()
@click.argument("package")
@click.option("--aports", "-a", type=click.Path(exists=True), help="aports 仓库路径")
@click.option("--recursive", "-r", is_flag=True, help="递归显示所有依赖")
@click.option("--depth", "-d", default=3, help="最大递归深度")
@click.option(
    "--type", "-t", "dep_type", type=click.Choice(["all", "runtime", "build"]), default="all"
)
@click.option("--tree", is_flag=True, help="以树形结构显示")
def deps(package: str, aports: str | None, recursive: bool, depth: int, dep_type: str, tree: bool):
    """查询软件包的依赖关系"""
    graph = load_or_scan(aports)

    if package not in graph.packages:
        console.print(f"[red]Error:[/red] Package '{package}' not found")
        sys.exit(1)

    dtype = {
        "all": DependencyType.ALL,
        "runtime": DependencyType.RUNTIME,
        "build": DependencyType.BUILD,
    }[dep_type]

    pkg_info = graph.packages[package]
    console.print(
        Panel(
            f"[bold]{package}[/bold] {pkg_info.version}-r{pkg_info.release}\n"
            f"[dim]{pkg_info.description}[/dim]",
            title="Package Info",
            border_style="blue",
        )
    )

    if tree:
        # 树形显示
        tree_data = graph.get_dependency_tree(package, dtype, depth)

        def build_tree(node_data, parent_tree):
            name = node_data["name"]
            node_pkg = graph.packages.get(name)

            label = f"[cyan]{name}[/cyan]"
            if node_pkg:
                label += f" [dim]({node_pkg.repo})[/dim]"

            if node_data.get("truncated"):
                label += " [yellow]...[/yellow]"

            branch = parent_tree.add(label)

            for child in node_data.get("children", []):
                build_tree(child, branch)

        rich_tree = Tree(f"[bold green]{package}[/bold green]")
        for child in tree_data.get("children", []):
            build_tree(child, rich_tree)

        console.print(rich_tree)
    else:
        # 列表显示
        deps_list = graph.get_dependencies(
            package, dep_type=dtype, recursive=recursive, max_depth=depth if recursive else -1
        )

        if not deps_list:
            console.print("[dim]No dependencies[/dim]")
            return

        table = Table(show_header=True, header_style="bold")
        table.add_column("Package", style="cyan")
        table.add_column("Version")
        table.add_column("Repo")

        for dep in deps_list:
            dep_pkg = graph.packages.get(dep)
            if dep_pkg:
                table.add_row(dep, f"{dep_pkg.version}-r{dep_pkg.release}", dep_pkg.repo)
            else:
                table.add_row(dep, "[dim]N/A[/dim]", "[dim]N/A[/dim]")

        console.print(f"\n[bold]Dependencies ({len(deps_list)})[/bold]")
        console.print(table)


@main.command()
@click.argument("package")
@click.option("--aports", "-a", type=click.Path(exists=True), help="aports 仓库路径")
@click.option("--recursive", "-r", is_flag=True, help="递归显示")
@click.option("--depth", "-d", default=2, help="最大递归深度")
def rdeps(package: str, aports: str | None, recursive: bool, depth: int):
    """查询软件包的反向依赖（哪些包依赖此包）"""
    graph = load_or_scan(aports)

    if package not in graph.packages:
        console.print(f"[red]Error:[/red] Package '{package}' not found")
        sys.exit(1)

    rdeps_list = graph.get_reverse_dependencies(
        package, recursive=recursive, max_depth=depth if recursive else -1
    )

    if not rdeps_list:
        console.print(f"[dim]No packages depend on {package}[/dim]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Package", style="cyan")
    table.add_column("Version")
    table.add_column("Repo")

    for dep in rdeps_list:
        dep_pkg = graph.packages.get(dep)
        if dep_pkg:
            table.add_row(dep, f"{dep_pkg.version}-r{dep_pkg.release}", dep_pkg.repo)

    console.print(f"\n[bold]Reverse Dependencies ({len(rdeps_list)})[/bold]")
    console.print(table)


@main.command()
@click.argument("package")
@click.option("--aports", "-a", type=click.Path(exists=True), help="aports 仓库路径")
@click.option("--output", "-o", required=True, type=click.Path(), help="输出文件路径")
@click.option("--depth", "-d", default=3, help="最大深度")
@click.option("--format", "-f", "fmt", type=click.Choice(["graph", "tree", "d3"]), default="graph")
@click.option("--include-reverse", "-r", is_flag=True, help="包含反向依赖")
@click.option(
    "--type",
    "-t",
    "dep_type",
    type=click.Choice(["runtime", "build", "all"]),
    default="runtime",
    help="依赖类型 (默认: runtime)",
)
@click.option("--show-all-types", is_flag=True, help="显示所有依赖类型（用不同样式区分）")
def visualize(
    package: str,
    aports: str | None,
    output: str,
    depth: int,
    fmt: str,
    include_reverse: bool,
    dep_type: str,
    show_all_types: bool,
):
    """生成依赖关系可视化图

    默认只显示运行时依赖 (runtime)，使用 --show-all-types 可以显示所有类型。
    不同依赖类型用不同线条样式区分：

    \b
    - Runtime (运行时): 绿色实线
    - Build (构建):    蓝色虚线
    - Check (检查):    橙色点线
    """
    graph = load_or_scan(aports)

    if package not in graph.packages:
        console.print(f"[red]Error:[/red] Package '{package}' not found")
        sys.exit(1)

    # 转换依赖类型
    dtype_map = {
        "runtime": DependencyType.RUNTIME,
        "build": DependencyType.BUILD,
        "all": DependencyType.ALL,
    }
    dtype = dtype_map[dep_type]

    viz = Visualizer(graph)

    with console.status(f"Generating visualization for {package}..."):
        if fmt == "graph":
            viz.render_html(
                package,
                output,
                dep_type=dtype,
                max_depth=depth,
                include_reverse=include_reverse,
                show_all_types=show_all_types,
            )
        elif fmt == "tree":
            viz.render_tree_html(package, output, max_depth=depth)
        elif fmt == "d3":
            viz.render_d3_html(package, output, max_depth=depth)

    console.print(f"[green]✓[/green] Generated {output}")
    console.print(f"[dim]Open in browser: file://{os.path.abspath(output)}[/dim]")


@main.command()
@click.option("--aports", "-a", type=click.Path(exists=True), help="aports 仓库路径")
@click.option("--output", "-o", type=click.Path(), help="输出 HTML 文件路径")
@click.option("--max-nodes", "-n", default=300, help="最大节点数 (仅当不使用 --all 时)")
@click.option(
    "--all", "show_all", is_flag=True, help="显示所有节点（完整依赖图，可在 HTML 中过滤）"
)
@click.option(
    "--repo",
    "-r",
    type=click.Choice(["main", "community", "testing"]),
    help="只包含指定仓库的包（在生成时过滤）",
)
def overview(
    aports: str | None, output: str | None, max_nodes: int, show_all: bool, repo: str | None
):
    """生成完整依赖图概览

    生成的 HTML 文件包含交互式过滤器，可以在浏览器中动态过滤：

    \b
    节点过滤选项（侧边栏）：
    - Root Package:  输入包名查看其依赖子树
    - Min Reverse Deps: 过滤掉被依赖数少于此值的包
    - Min Dependencies: 过滤掉依赖数少于此值的包
    - Repository:    只显示指定仓库的包
    - Hide orphans:  隐藏孤立包（无依赖且不被依赖）

    \b
    边过滤选项（顶部）：
    - Runtime: 显示运行时依赖（绿色实线）
    - Build:   显示构建依赖（蓝色虚线）
    - Check:   显示检查依赖（橙色点线）

    \b
    示例：
    dep-map overview --all -o full-graph.html       # 生成完整图
    dep-map overview --all --repo main -o main.html # 只生成 main 仓库
    dep-map overview -n 500 -o top500.html          # 只取前 500 个节点
    """
    graph = load_or_scan(aports)

    # 如果指定了 repo，过滤图
    if repo:
        filtered_packages = {name: pkg for name, pkg in graph.packages.items() if pkg.repo == repo}
        console.print(
            f"[cyan]Filtering to {repo} repository: {len(filtered_packages)} packages[/cyan]"
        )

        # 创建一个新的 graph 只包含指定仓库的包
        from dep_map.graph import DependencyGraph

        filtered_graph = DependencyGraph(filtered_packages)
        graph = filtered_graph

    output_path = output or "dependency-overview.html"

    viz = Visualizer(graph)

    if show_all:
        total = len(graph.packages)
        console.print(f"[yellow]Generating graph with {total} packages...[/yellow]")
        if not repo:
            console.print("[dim]Tip: Use filters in the HTML sidebar to narrow down the view[/dim]")

        with console.status("Generating graph..."):
            viz.render_full_graph_html(
                output_path, max_nodes=total, dep_type=DependencyType.ALL, show_all_types=True
            )
    else:
        with console.status("Generating overview..."):
            viz.render_full_graph_html(
                output_path, max_nodes=max_nodes, dep_type=DependencyType.ALL, show_all_types=True
            )

    console.print(f"[green]✓[/green] Generated {output_path}")
    console.print(f"[dim]Open in browser: file://{os.path.abspath(output_path)}[/dim]")


@main.command()
@click.option("--aports", "-a", type=click.Path(exists=True), help="aports 仓库路径")
@click.option("--json", "as_json", is_flag=True, help="输出 JSON 格式")
def stats(aports: str | None, as_json: bool):
    """显示依赖图统计信息"""
    graph = load_or_scan(aports)
    analyzer = DependencyAnalyzer(graph)

    report = analyzer.generate_report()

    if as_json:
        console.print(json.dumps(report, indent=2, ensure_ascii=False))
        return

    # 总体统计
    summary = report["summary"]
    console.print(Panel("[bold]Summary[/bold]", border_style="blue"))

    table = Table(show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Total Packages", str(summary["total_packages"]))
    table.add_row("Total Edges", str(summary["total_edges"]))
    table.add_row("Graph Density", f"{summary['density']:.6f}")
    table.add_row("Is DAG", "Yes" if summary["is_dag"] else "No")
    table.add_row("Connected Components", str(summary["components"]))

    console.print(table)

    # 仓库统计
    console.print(Panel("[bold]Repository Statistics[/bold]", border_style="blue"))

    table = Table(show_header=True, header_style="bold")
    table.add_column("Repository", style="cyan")
    table.add_column("Packages", justify="right")
    table.add_column("Avg Deps", justify="right")

    for repo, data in report["repos"].items():
        table.add_row(repo, str(data["package_count"]), str(data["avg_deps"]))

    console.print(table)

    # 被依赖最多
    console.print(Panel("[bold]Most Depended Packages[/bold]", border_style="blue"))

    table = Table(show_header=True, header_style="bold")
    table.add_column("#", style="dim")
    table.add_column("Package", style="cyan")
    table.add_column("Dependents", justify="right")

    for i, (pkg, count) in enumerate(report["most_depended"][:15], 1):
        table.add_row(str(i), pkg, str(count))

    console.print(table)

    # 循环依赖
    if report["circular_dependencies"]:
        console.print(
            Panel(
                f"[yellow]Found {report['circular_dependencies_count']} circular dependencies[/yellow]",
                border_style="yellow",
            )
        )


@main.command()
@click.argument("source")
@click.argument("target")
@click.option("--aports", "-a", type=click.Path(exists=True), help="aports 仓库路径")
def path(source: str, target: str, aports: str | None):
    """查找两个包之间的依赖路径"""
    graph = load_or_scan(aports)

    dep_path = graph.get_dependency_path(source, target)

    if not dep_path:
        console.print(f"[yellow]No dependency path found from {source} to {target}[/yellow]")
        return

    console.print(f"\n[bold]Dependency path ({len(dep_path) - 1} hops):[/bold]\n")

    for i, pkg in enumerate(dep_path):
        if i > 0:
            console.print("  ↓")

        pkg_info = graph.packages.get(pkg)
        if pkg_info:
            console.print(f"  [cyan]{pkg}[/cyan] [dim]({pkg_info.repo})[/dim]")
        else:
            console.print(f"  [cyan]{pkg}[/cyan]")


@main.command()
@click.option("--aports", "-a", type=click.Path(exists=True), help="aports 仓库路径")
@click.option("--port", "-p", default=8080, help="服务端口")
@click.option("--host", "-h", "host", default="127.0.0.1", help="绑定地址")
def serve(aports: str | None, port: int, host: str):
    """启动 Web 界面"""
    graph = load_or_scan(aports)

    try:
        from .web import create_app

        app = create_app(graph)

        console.print(
            Panel(
                f"[bold green]Web interface started[/bold green]\n\n"
                f"Open http://{host}:{port} in your browser",
                border_style="green",
            )
        )

        app.run(host=host, port=port, debug=False)
    except ImportError:
        console.print("[red]Error:[/red] Flask is required for web interface")
        console.print("Install with: pip install flask")
        sys.exit(1)


@main.command()
@click.argument("package")
@click.option("--aports", "-a", type=click.Path(exists=True), help="aports 仓库路径")
def info(package: str, aports: str | None):
    """显示软件包详细信息"""
    graph = load_or_scan(aports)

    if package not in graph.packages:
        console.print(f"[red]Error:[/red] Package '{package}' not found")
        sys.exit(1)

    analyzer = DependencyAnalyzer(graph)
    analysis = analyzer.analyze_package(package)
    pkg = graph.packages[package]

    # 基本信息
    console.print(
        Panel(
            f"[bold]{pkg.name}[/bold] {pkg.version}-r{pkg.release}\n\n"
            f"[dim]{pkg.description}[/dim]\n\n"
            f"URL: {pkg.url}\n"
            f"License: {pkg.license}\n"
            f"Repository: {pkg.repo}\n"
            f"Maintainer: {pkg.maintainer}",
            title="Package Information",
            border_style="blue",
        )
    )

    # 依赖统计
    if analysis:
        table = Table(title="Dependency Statistics", show_header=True, header_style="bold")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")

        table.add_row("Direct Dependencies", str(analysis.direct_deps_count))
        table.add_row("Total Dependencies", str(analysis.total_deps_count))
        table.add_row("Runtime Dependencies", str(analysis.runtime_deps_count))
        table.add_row("Build Dependencies", str(analysis.build_deps_count))
        table.add_row("Direct Reverse Deps", str(analysis.direct_rdeps_count))
        table.add_row("Total Reverse Deps", str(analysis.total_rdeps_count))
        table.add_row("Dependency Depth", str(analysis.dependency_depth))
        table.add_row("Is Leaf Package", "Yes" if analysis.is_leaf else "No")
        table.add_row("Is Core Package", "Yes" if analysis.is_core else "No")

        console.print(table)

    # 直接依赖列表
    if pkg.depends:
        console.print(f"\n[bold]Runtime Dependencies:[/bold] {', '.join(pkg.depends)}")

    if pkg.makedepends:
        console.print(f"\n[bold]Build Dependencies:[/bold] {', '.join(pkg.makedepends)}")

    if pkg.subpackages:
        console.print(f"\n[bold]Subpackages:[/bold] {', '.join(pkg.subpackages)}")


if __name__ == "__main__":
    main()
