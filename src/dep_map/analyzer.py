"""
依赖关系分析器

提供统计分析和报告功能。
"""

from collections import Counter
from dataclasses import dataclass

from .graph import DependencyGraph, DependencyType
from .parser import PackageInfo


@dataclass
class PackageAnalysis:
    """软件包分析结果"""

    name: str
    version: str
    repo: str

    # 依赖统计
    direct_deps_count: int
    total_deps_count: int
    build_deps_count: int
    runtime_deps_count: int

    # 被依赖统计
    direct_rdeps_count: int
    total_rdeps_count: int

    # 深度
    dependency_depth: int

    # 分类
    is_leaf: bool  # 没有被依赖
    is_root: bool  # 没有依赖
    is_core: bool  # 被大量包依赖


@dataclass
class RepoAnalysis:
    """仓库分析结果"""

    name: str
    package_count: int
    total_deps: int
    avg_deps: float

    most_depended: list[tuple[str, int]]
    most_dependencies: list[tuple[str, int]]

    cross_repo_deps: dict[str, int]  # 对其他仓库的依赖数


class DependencyAnalyzer:
    """依赖关系分析器"""

    def __init__(self, graph: DependencyGraph):
        self.graph = graph

    def analyze_package(self, package: str) -> PackageAnalysis | None:
        """
        分析单个软件包

        Args:
            package: 软件包名称

        Returns:
            分析结果
        """
        pkg_info = self.graph.packages.get(package)
        if not pkg_info:
            return None

        # 直接依赖
        direct_deps = self.graph.get_dependencies(package)
        runtime_deps = self.graph.get_dependencies(package, DependencyType.RUNTIME)
        build_deps = self.graph.get_dependencies(package, DependencyType.BUILD)

        # 递归依赖
        all_deps = self.graph.get_dependencies(package, recursive=True)

        # 被依赖
        direct_rdeps = self.graph.get_reverse_dependencies(package)
        all_rdeps = self.graph.get_reverse_dependencies(package, recursive=True)

        # 判断是否是核心包
        is_core = len(direct_rdeps) > 50

        return PackageAnalysis(
            name=package,
            version=f"{pkg_info.version}-r{pkg_info.release}",
            repo=pkg_info.repo,
            direct_deps_count=len(direct_deps),
            total_deps_count=len(all_deps),
            build_deps_count=len(build_deps),
            runtime_deps_count=len(runtime_deps),
            direct_rdeps_count=len(direct_rdeps),
            total_rdeps_count=len(all_rdeps),
            dependency_depth=self.graph.get_dependency_depth(package),
            is_leaf=len(direct_rdeps) == 0,
            is_root=len(direct_deps) == 0,
            is_core=is_core,
        )

    def analyze_repo(self, repo: str) -> RepoAnalysis:
        """
        分析仓库

        Args:
            repo: 仓库名称

        Returns:
            分析结果
        """
        # 筛选该仓库的包
        repo_packages = {name: pkg for name, pkg in self.graph.packages.items() if pkg.repo == repo}

        if not repo_packages:
            return RepoAnalysis(
                name=repo,
                package_count=0,
                total_deps=0,
                avg_deps=0,
                most_depended=[],
                most_dependencies=[],
                cross_repo_deps={},
            )

        # 统计
        total_deps = 0
        dep_counts = {}
        rdep_counts = {}
        cross_repo: Counter[str] = Counter()

        for name in repo_packages:
            deps = self.graph.get_dependencies(name)
            total_deps += len(deps)
            dep_counts[name] = len(self.graph.get_dependencies(name, recursive=True))
            rdep_counts[name] = len(self.graph.get_reverse_dependencies(name))

            # 跨仓库依赖
            for dep in deps:
                dep_pkg = self.graph.packages.get(dep)
                if dep_pkg and dep_pkg.repo != repo:
                    cross_repo[dep_pkg.repo] += 1

        # 排序
        most_depended = sorted(rdep_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        most_dependencies = sorted(dep_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return RepoAnalysis(
            name=repo,
            package_count=len(repo_packages),
            total_deps=total_deps,
            avg_deps=total_deps / len(repo_packages),
            most_depended=most_depended,
            most_dependencies=most_dependencies,
            cross_repo_deps=dict(cross_repo),
        )

    def find_circular_dependencies(self) -> list[list[str]]:
        """
        查找循环依赖

        Returns:
            循环依赖列表
        """
        return self.graph.find_cycles()

    def find_unused_packages(self) -> list[str]:
        """
        查找未被使用的包（叶子节点）

        Returns:
            未被使用的包列表
        """
        return self.graph.get_leaf_packages()

    def find_base_packages(self) -> list[str]:
        """
        查找基础包（被依赖最多的包）

        Returns:
            基础包列表
        """
        most_depended = self.graph.get_most_depended(100)
        return [pkg for pkg, count in most_depended if count > 20]

    def get_dependency_chain(self, source: str, target: str) -> list[str] | None:
        """
        获取两个包之间的依赖链

        Args:
            source: 源包
            target: 目标包

        Returns:
            依赖链
        """
        return self.graph.get_dependency_path(source, target)

    def get_common_dependencies(self, packages: list[str]) -> list[str]:
        """
        获取多个包的公共依赖

        Args:
            packages: 软件包列表

        Returns:
            公共依赖列表
        """
        if not packages:
            return []

        # 获取每个包的依赖集合
        dep_sets = []
        for pkg in packages:
            deps = set(self.graph.get_dependencies(pkg, recursive=True))
            dep_sets.append(deps)

        # 计算交集
        common = dep_sets[0]
        for deps in dep_sets[1:]:
            common = common.intersection(deps)

        return sorted(common)

    def get_unique_dependencies(self, package: str, compared_to: list[str]) -> list[str]:
        """
        获取相对于其他包的独特依赖

        Args:
            package: 目标包
            compared_to: 比较的包列表

        Returns:
            独特依赖列表
        """
        pkg_deps = set(self.graph.get_dependencies(package, recursive=True))

        other_deps = set()
        for other in compared_to:
            other_deps.update(self.graph.get_dependencies(other, recursive=True))

        unique = pkg_deps - other_deps
        return sorted(unique)

    def estimate_install_size(self, package: str) -> dict:
        """
        估算安装大小（按包数量）

        Args:
            package: 软件包名称

        Returns:
            安装统计
        """
        deps = self.graph.get_dependencies(package, recursive=True)

        by_repo: Counter[str] = Counter()
        for dep in deps:
            pkg = self.graph.packages.get(dep)
            if pkg:
                by_repo[pkg.repo] += 1

        return {
            "package_count": len(deps) + 1,
            "by_repo": dict(by_repo),
        }

    def generate_report(self) -> dict:
        """
        生成完整分析报告

        Returns:
            报告字典
        """
        stats = self.graph.get_statistics()

        # 按仓库分析
        repos = {pkg.repo for pkg in self.graph.packages.values()}
        repo_analyses = {}
        for repo in repos:
            if repo:
                repo_analyses[repo] = self.analyze_repo(repo)

        # 核心包
        core_packages = self.find_base_packages()

        # 循环依赖
        cycles = self.find_circular_dependencies()

        # 最被依赖的包
        most_depended = self.graph.get_most_depended(20)

        # 依赖最多的包
        most_deps = self.graph.get_most_dependencies(20)

        return {
            "summary": {
                "total_packages": stats["nodes"],
                "total_edges": stats["edges"],
                "density": stats["density"],
                "is_dag": stats["is_dag"],
                "components": stats["weakly_connected_components"],
            },
            "repos": {
                name: {
                    "package_count": analysis.package_count,
                    "avg_deps": round(analysis.avg_deps, 2),
                    "cross_repo_deps": analysis.cross_repo_deps,
                }
                for name, analysis in repo_analyses.items()
            },
            "core_packages": core_packages[:20],
            "most_depended": most_depended,
            "most_dependencies": most_deps,
            "circular_dependencies_count": len(cycles),
            "circular_dependencies": cycles[:10] if cycles else [],
        }

    def print_report(self):
        """打印分析报告"""
        report = self.generate_report()

        print("=" * 60)
        print("Alpine Linux 软件包依赖分析报告")
        print("=" * 60)

        print("\n## 总体统计\n")
        summary = report["summary"]
        print(f"  总软件包数: {summary['total_packages']}")
        print(f"  总依赖边数: {summary['total_edges']}")
        print(f"  图密度: {summary['density']:.6f}")
        print(f"  是否为有向无环图: {'是' if summary['is_dag'] else '否'}")
        print(f"  弱连通分量数: {summary['components']}")

        print("\n## 仓库分析\n")
        for repo, data in report["repos"].items():
            print(f"  [{repo}]")
            print(f"    软件包数: {data['package_count']}")
            print(f"    平均依赖数: {data['avg_deps']}")
            if data["cross_repo_deps"]:
                print(f"    跨仓库依赖: {data['cross_repo_deps']}")

        print("\n## 被依赖最多的包 (Top 20)\n")
        for pkg, count in report["most_depended"]:
            print(f"  {pkg}: {count}")

        print("\n## 依赖最多的包 (Top 20)\n")
        for pkg, count in report["most_dependencies"]:
            print(f"  {pkg}: {count}")

        if report["circular_dependencies"]:
            print(f"\n## 循环依赖 (共 {report['circular_dependencies_count']} 个)\n")
            for cycle in report["circular_dependencies"]:
                print(f"  {' -> '.join(cycle)} -> {cycle[0]}")

        print("\n" + "=" * 60)


def test_analyzer():
    """测试分析器"""
    from .graph import DependencyGraph

    # 创建测试数据
    packages = {
        "app": PackageInfo(name="app", repo="community", depends=["libfoo", "libbar"]),
        "libfoo": PackageInfo(name="libfoo", repo="main", depends=["libc"]),
        "libbar": PackageInfo(name="libbar", repo="main", depends=["libc", "libfoo"]),
        "libc": PackageInfo(name="libc", repo="main"),
        "gcc": PackageInfo(name="gcc", repo="main", depends=["libc"]),
    }

    graph = DependencyGraph(packages)
    analyzer = DependencyAnalyzer(graph)

    # 分析单个包
    analysis = analyzer.analyze_package("app")
    if analysis:
        print(f"Package: {analysis.name}")
        print(f"  Direct deps: {analysis.direct_deps_count}")
        print(f"  Total deps: {analysis.total_deps_count}")
        print(f"  Is leaf: {analysis.is_leaf}")

    # 生成报告
    analyzer.print_report()


if __name__ == "__main__":
    test_analyzer()
