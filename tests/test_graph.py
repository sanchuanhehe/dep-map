"""
测试依赖图
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dep_map.graph import DependencyGraph, DependencyType
from dep_map.parser import PackageInfo


class TestDependencyGraph:
    """测试依赖图"""

    def setup_method(self):
        """创建测试数据"""
        self.packages = {
            "app": PackageInfo(
                name="app",
                repo="community",
                depends=["libfoo", "libbar"],
                makedepends=["cmake", "gcc"],
            ),
            "libfoo": PackageInfo(
                name="libfoo",
                repo="main",
                depends=["libc"],
                makedepends=["gcc"],
            ),
            "libbar": PackageInfo(
                name="libbar",
                repo="main",
                depends=["libc", "libfoo"],
            ),
            "libc": PackageInfo(name="libc", repo="main"),
            "cmake": PackageInfo(
                name="cmake",
                repo="main",
                depends=["libc"],
            ),
            "gcc": PackageInfo(
                name="gcc",
                repo="main",
                depends=["libc"],
            ),
        }

        self.graph = DependencyGraph(self.packages)

    def test_direct_dependencies(self):
        """测试直接依赖"""
        deps = self.graph.get_dependencies("app")

        assert "libfoo" in deps
        assert "libbar" in deps
        assert "cmake" in deps
        assert "gcc" in deps

    def test_runtime_dependencies(self):
        """测试运行时依赖"""
        deps = self.graph.get_dependencies("app", dep_type=DependencyType.RUNTIME)

        assert "libfoo" in deps
        assert "libbar" in deps
        assert "cmake" not in deps
        assert "gcc" not in deps

    def test_build_dependencies(self):
        """测试构建依赖"""
        deps = self.graph.get_dependencies("app", dep_type=DependencyType.BUILD)

        assert "cmake" in deps
        assert "gcc" in deps
        assert "libfoo" not in deps

    def test_recursive_dependencies(self):
        """测试递归依赖"""
        deps = self.graph.get_dependencies("app", recursive=True)

        assert "libfoo" in deps
        assert "libbar" in deps
        assert "libc" in deps

    def test_reverse_dependencies(self):
        """测试反向依赖"""
        rdeps = self.graph.get_reverse_dependencies("libc")

        assert "libfoo" in rdeps
        assert "libbar" in rdeps
        assert "cmake" in rdeps
        assert "gcc" in rdeps

    def test_recursive_reverse_dependencies(self):
        """测试递归反向依赖"""
        rdeps = self.graph.get_reverse_dependencies("libc", recursive=True)

        assert "libfoo" in rdeps
        assert "libbar" in rdeps
        assert "app" in rdeps

    def test_dependency_path(self):
        """测试依赖路径"""
        path = self.graph.get_dependency_path("app", "libc")

        assert path is not None
        assert path[0] == "app"
        assert path[-1] == "libc"

    def test_no_dependency_path(self):
        """测试无依赖路径"""
        path = self.graph.get_dependency_path("libc", "app")

        assert path is None

    def test_dependency_tree(self):
        """测试依赖树"""
        tree = self.graph.get_dependency_tree("app", max_depth=2)

        assert tree["name"] == "app"
        assert len(tree["children"]) > 0

    def test_leaf_packages(self):
        """测试叶子包"""
        leaves = self.graph.get_leaf_packages()

        # app 是叶子，因为没有其他包依赖它
        assert "app" in leaves

    def test_root_packages(self):
        """测试根包"""
        roots = self.graph.get_root_packages()

        # libc 是根包，因为它没有依赖
        assert "libc" in roots

    def test_statistics(self):
        """测试统计信息"""
        stats = self.graph.get_statistics()

        assert stats["nodes"] == 6
        assert stats["edges"] > 0
        assert "density" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
