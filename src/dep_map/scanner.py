"""
aports 仓库扫描器

扫描 Alpine Linux aports 仓库，解析所有 APKBUILD 文件。
"""

import json
import time
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from .parser import APKBUILDParser, PackageInfo


@dataclass
class ScanResult:
    """扫描结果"""

    packages: dict[str, PackageInfo]
    errors: list[str]
    scan_time: float
    total_files: int
    successful: int
    failed: int

    def to_dict(self) -> dict:
        return {
            "packages": {k: v.to_dict() for k, v in self.packages.items()},
            "errors": self.errors,
            "scan_time": self.scan_time,
            "total_files": self.total_files,
            "successful": self.successful,
            "failed": self.failed,
        }


class AportsScanner:
    """aports 仓库扫描器"""

    # 标准仓库目录
    REPOS = ["main", "community", "testing", "unmaintained"]

    def __init__(self, aports_path: str, repos: list[str] | None = None):
        """
        初始化扫描器

        Args:
            aports_path: aports 仓库路径
            repos: 要扫描的仓库列表，默认为所有仓库
        """
        self.aports_path = Path(aports_path)
        self.repos = repos or self.REPOS
        self.parser = APKBUILDParser()
        self._packages: dict[str, PackageInfo] = {}
        self._provides_map: dict[str, str] = {}  # provides -> pkgname
        self._subpkg_map: dict[str, str] = {}  # subpackage -> pkgname

    def scan(
        self, progress_callback: Callable[[int, int, str], None] | None = None, max_workers: int = 4
    ) -> ScanResult:
        """
        扫描所有 APKBUILD 文件

        Args:
            progress_callback: 进度回调函数 (current, total, package_name)
            max_workers: 并行工作线程数

        Returns:
            扫描结果
        """
        start_time = time.time()
        errors = []

        # 收集所有 APKBUILD 文件路径
        apkbuild_files = list(self._find_apkbuild_files())
        total_files = len(apkbuild_files)

        # 并行解析
        successful = 0
        failed = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self._parse_file, f): f for f in apkbuild_files}

            for i, future in enumerate(as_completed(futures)):
                filepath = futures[future]
                try:
                    pkg = future.result()
                    if pkg:
                        self._packages[pkg.name] = pkg

                        # 建立 provides 映射
                        for prov in pkg.provides:
                            # 移除版本号
                            prov_name = prov.split("=")[0].split(">")[0].split("<")[0]
                            self._provides_map[prov_name] = pkg.name

                        # 建立子包映射
                        for subpkg in pkg.subpackages:
                            self._subpkg_map[subpkg] = pkg.name

                        successful += 1

                        if progress_callback:
                            progress_callback(i + 1, total_files, pkg.name)
                    else:
                        failed += 1
                        errors.append(f"Failed to parse: {filepath}")
                except Exception as e:
                    failed += 1
                    errors.append(f"Error parsing {filepath}: {e}")

        scan_time = time.time() - start_time

        return ScanResult(
            packages=self._packages,
            errors=errors,
            scan_time=scan_time,
            total_files=total_files,
            successful=successful,
            failed=failed,
        )

    def scan_single(self, package_name: str) -> PackageInfo | None:
        """
        扫描单个软件包

        Args:
            package_name: 软件包名称

        Returns:
            软件包信息，如果未找到则返回 None
        """
        for repo in self.repos:
            apkbuild_path = self.aports_path / repo / package_name / "APKBUILD"
            if apkbuild_path.exists():
                return self._parse_file(str(apkbuild_path))
        return None

    def _find_apkbuild_files(self) -> Iterator[str]:
        """查找所有 APKBUILD 文件"""
        for repo in self.repos:
            repo_path = self.aports_path / repo
            if not repo_path.exists():
                continue

            for entry in repo_path.iterdir():
                if entry.is_dir():
                    apkbuild = entry / "APKBUILD"
                    if apkbuild.exists():
                        yield str(apkbuild)

    def _parse_file(self, filepath: str) -> PackageInfo | None:
        """解析单个 APKBUILD 文件"""
        return self.parser.parse_file(filepath)

    def get_package(self, name: str) -> PackageInfo | None:
        """获取软件包信息"""
        return self._packages.get(name)

    def get_all_packages(self) -> dict[str, PackageInfo]:
        """获取所有软件包"""
        return self._packages.copy()

    def resolve_package_name(self, name: str) -> str | None:
        """
        解析软件包名称（处理 provides 和 subpackages）

        Args:
            name: 可能是包名、provides 名称或子包名

        Returns:
            实际的包名
        """
        # 首先检查是否是直接包名
        if name in self._packages:
            return name

        # 检查 provides
        if name in self._provides_map:
            return self._provides_map[name]

        # 检查子包
        if name in self._subpkg_map:
            return self._subpkg_map[name]

        return None

    def save_to_json(self, filepath: str):
        """保存扫描结果到 JSON 文件"""
        data = {
            "packages": {k: v.to_dict() for k, v in self._packages.items()},
            "provides_map": self._provides_map,
            "subpkg_map": self._subpkg_map,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_from_json(self, filepath: str):
        """从 JSON 文件加载扫描结果"""
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        self._packages = {}
        for name, pkg_dict in data["packages"].items():
            pkg = PackageInfo(name=name)
            for key, value in pkg_dict.items():
                if hasattr(pkg, key):
                    setattr(pkg, key, value)
            self._packages[name] = pkg

        self._provides_map = data.get("provides_map", {})
        self._subpkg_map = data.get("subpkg_map", {})

    def get_statistics(self) -> dict:
        """获取统计信息"""
        repo_counts: dict[str, int] = {}
        total_deps = 0
        max_deps_pkg = None
        max_deps_count = 0

        for pkg in self._packages.values():
            repo = pkg.repo or "unknown"
            repo_counts[repo] = repo_counts.get(repo, 0) + 1

            deps_count = len(pkg.all_depends)
            total_deps += deps_count

            if deps_count > max_deps_count:
                max_deps_count = deps_count
                max_deps_pkg = pkg.name

        return {
            "total_packages": len(self._packages),
            "by_repo": repo_counts,
            "total_dependencies": total_deps,
            "avg_dependencies": total_deps / len(self._packages) if self._packages else 0,
            "max_dependencies_package": max_deps_pkg,
            "max_dependencies_count": max_deps_count,
            "provides_count": len(self._provides_map),
            "subpackages_count": len(self._subpkg_map),
        }


def test_scanner():
    """测试扫描器"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python scanner.py <aports_path>")
        return

    aports_path = sys.argv[1]
    scanner = AportsScanner(aports_path)

    def progress(current, total, name):
        print(f"\r[{current}/{total}] {name}".ljust(80), end="", flush=True)

    print("Scanning aports repository...")
    result = scanner.scan(progress_callback=progress)
    print()

    print(f"\nScan completed in {result.scan_time:.2f}s")
    print(f"Total files: {result.total_files}")
    print(f"Successful: {result.successful}")
    print(f"Failed: {result.failed}")

    stats = scanner.get_statistics()
    print("\nStatistics:")
    print(f"  Total packages: {stats['total_packages']}")
    print(f"  By repo: {stats['by_repo']}")
    print(f"  Avg dependencies: {stats['avg_dependencies']:.2f}")
    print(f"  Most deps: {stats['max_dependencies_package']} ({stats['max_dependencies_count']})")


if __name__ == "__main__":
    test_scanner()
