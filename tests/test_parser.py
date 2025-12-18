"""
测试 APKBUILD 解析器
"""

import pytest
import os
import sys

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dep_map.parser import APKBUILDParser, PackageInfo


class TestAPKBUILDParser:
    """测试 APKBUILD 解析器"""
    
    def setup_method(self):
        self.parser = APKBUILDParser()
    
    def test_parse_simple_package(self):
        """测试解析简单包"""
        content = '''
pkgname=test-package
pkgver=1.2.3
pkgrel=1
pkgdesc="A test package"
url="https://example.com"
arch="all"
license="MIT"
depends="dep1 dep2"
'''
        pkg = self.parser.parse_content(content)
        
        assert pkg is not None
        assert pkg.name == "test-package"
        assert pkg.version == "1.2.3"
        assert pkg.release == 1
        assert pkg.description == "A test package"
        assert pkg.url == "https://example.com"
        assert pkg.arch == "all"
        assert pkg.license == "MIT"
        assert "dep1" in pkg.depends
        assert "dep2" in pkg.depends
    
    def test_parse_multiline_depends(self):
        """测试解析多行依赖"""
        content = '''
pkgname=test-package
pkgver=1.0.0
pkgrel=0
makedepends="
    cmake
    gcc
    make
    "
'''
        pkg = self.parser.parse_content(content)
        
        assert pkg is not None
        assert "cmake" in pkg.makedepends
        assert "gcc" in pkg.makedepends
        assert "make" in pkg.makedepends
    
    def test_parse_version_constraints(self):
        """测试解析带版本约束的依赖"""
        content = '''
pkgname=test-package
pkgver=1.0.0
pkgrel=0
depends="libfoo>=1.0 libbar<2.0 libbaz=3.0"
'''
        pkg = self.parser.parse_content(content)
        
        assert pkg is not None
        assert "libfoo" in pkg.depends
        assert "libbar" in pkg.depends
        assert "libbaz" in pkg.depends
    
    def test_parse_maintainer(self):
        """测试解析维护者信息"""
        content = '''
# Maintainer: Test User <test@example.com>
# Contributor: Another User <another@example.com>
pkgname=test-package
pkgver=1.0.0
pkgrel=0
'''
        pkg = self.parser.parse_content(content)
        
        assert pkg is not None
        assert "Test User" in pkg.maintainer
        assert len(pkg.contributors) == 1
        assert "Another User" in pkg.contributors[0]
    
    def test_repo_detection(self):
        """测试仓库检测"""
        content = '''
pkgname=test-package
pkgver=1.0.0
pkgrel=0
'''
        pkg = self.parser.parse_content(
            content, 
            filepath="/path/to/aports/main/test-package/APKBUILD"
        )
        
        assert pkg is not None
        assert pkg.repo == "main"
        
        pkg2 = self.parser.parse_content(
            content,
            filepath="/path/to/aports/community/test-package/APKBUILD"
        )
        
        assert pkg2 is not None
        assert pkg2.repo == "community"
    
    def test_subpackages(self):
        """测试子包解析"""
        content = '''
pkgname=test-package
pkgver=1.0.0
pkgrel=0
subpackages="$pkgname-doc $pkgname-dev"
'''
        pkg = self.parser.parse_content(content)
        
        assert pkg is not None
        # 注意：$pkgname 会被跳过，因为需要实际替换
        # 这里测试的是解析器不会崩溃


class TestPackageInfo:
    """测试 PackageInfo 类"""
    
    def test_all_depends(self):
        """测试获取所有依赖"""
        pkg = PackageInfo(
            name="test",
            depends=["dep1"],
            makedepends=["makedep1"],
            checkdepends=["checkdep1"],
        )
        
        all_deps = pkg.all_depends
        assert "dep1" in all_deps
        assert "makedep1" in all_deps
        assert "checkdep1" in all_deps
    
    def test_runtime_depends(self):
        """测试运行时依赖"""
        pkg = PackageInfo(
            name="test",
            depends=["dep1", "dep2"],
            makedepends=["makedep1"],
        )
        
        runtime = pkg.runtime_depends
        assert "dep1" in runtime
        assert "dep2" in runtime
        assert "makedep1" not in runtime
    
    def test_build_depends(self):
        """测试构建依赖"""
        pkg = PackageInfo(
            name="test",
            depends=["dep1"],
            makedepends=["makedep1"],
            makedepends_build=["builddep1"],
            makedepends_host=["hostdep1"],
        )
        
        build = pkg.build_depends
        assert "makedep1" in build
        assert "builddep1" in build
        assert "hostdep1" in build
        assert "dep1" not in build
    
    def test_to_dict(self):
        """测试转换为字典"""
        pkg = PackageInfo(
            name="test",
            version="1.0.0",
            depends=["dep1"],
        )
        
        d = pkg.to_dict()
        assert d["name"] == "test"
        assert d["version"] == "1.0.0"
        assert "dep1" in d["depends"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
