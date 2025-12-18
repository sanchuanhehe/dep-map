"""
APKBUILD 文件解析器

解析 Alpine Linux APKBUILD 文件，提取软件包信息和依赖关系。
"""

import re
import os
from dataclasses import dataclass, field
from typing import List, Optional, Set, Dict, Any
from pathlib import Path


@dataclass
class PackageInfo:
    """软件包信息"""
    
    # 基本信息
    name: str
    version: str = ""
    release: int = 0
    description: str = ""
    url: str = ""
    license: str = ""
    arch: str = "all"
    
    # 依赖关系
    depends: List[str] = field(default_factory=list)
    makedepends: List[str] = field(default_factory=list)
    makedepends_build: List[str] = field(default_factory=list)
    makedepends_host: List[str] = field(default_factory=list)
    checkdepends: List[str] = field(default_factory=list)
    
    # 提供和替换
    provides: List[str] = field(default_factory=list)
    replaces: List[str] = field(default_factory=list)
    
    # 子包
    subpackages: List[str] = field(default_factory=list)
    
    # 元数据
    maintainer: str = ""
    contributors: List[str] = field(default_factory=list)
    repo: str = ""  # main, community, testing
    filepath: str = ""
    
    @property
    def all_depends(self) -> Set[str]:
        """获取所有依赖（包括构建依赖）"""
        all_deps = set()
        all_deps.update(self.depends)
        all_deps.update(self.makedepends)
        all_deps.update(self.makedepends_build)
        all_deps.update(self.makedepends_host)
        all_deps.update(self.checkdepends)
        return all_deps
    
    @property
    def runtime_depends(self) -> Set[str]:
        """获取运行时依赖"""
        return set(self.depends)
    
    @property
    def build_depends(self) -> Set[str]:
        """获取构建依赖"""
        deps = set()
        deps.update(self.makedepends)
        deps.update(self.makedepends_build)
        deps.update(self.makedepends_host)
        return deps
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "version": self.version,
            "release": self.release,
            "description": self.description,
            "url": self.url,
            "license": self.license,
            "arch": self.arch,
            "depends": self.depends,
            "makedepends": self.makedepends,
            "makedepends_build": self.makedepends_build,
            "makedepends_host": self.makedepends_host,
            "checkdepends": self.checkdepends,
            "provides": self.provides,
            "replaces": self.replaces,
            "subpackages": self.subpackages,
            "maintainer": self.maintainer,
            "contributors": self.contributors,
            "repo": self.repo,
            "filepath": self.filepath,
        }


class APKBUILDParser:
    """APKBUILD 文件解析器"""
    
    # 变量匹配模式
    VAR_PATTERNS = {
        "pkgname": r'^pkgname=([^\n]+)',
        "pkgver": r'^pkgver=([^\n]+)',
        "pkgrel": r'^pkgrel=([^\n]+)',
        "pkgdesc": r'^pkgdesc="([^"]*)"',
        "url": r'^url="([^"]*)"',
        "arch": r'^arch="([^"]*)"',
        "license": r'^license="([^"]*)"',
        "maintainer": r'^#\s*Maintainer:\s*(.+)$',
        "contributor": r'^#\s*Contributor:\s*(.+)$',
    }
    
    # 依赖变量（可能跨多行）
    DEP_VARS = [
        "depends",
        "makedepends",
        "makedepends_build", 
        "makedepends_host",
        "checkdepends",
        "provides",
        "replaces",
        "subpackages",
    ]
    
    def __init__(self):
        self._var_cache: Dict[str, str] = {}
    
    def parse_file(self, filepath: str) -> Optional[PackageInfo]:
        """解析 APKBUILD 文件"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return self.parse_content(content, filepath)
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
            return None
    
    def parse_content(self, content: str, filepath: str = "") -> Optional[PackageInfo]:
        """解析 APKBUILD 内容"""
        self._var_cache = {}
        
        # 提取包名
        pkgname = self._extract_var(content, "pkgname")
        if not pkgname:
            return None
        
        # 创建包信息对象
        pkg = PackageInfo(name=pkgname)
        pkg.filepath = filepath
        
        # 确定仓库类型
        if filepath:
            path_parts = Path(filepath).parts
            for repo in ["main", "community", "testing", "unmaintained"]:
                if repo in path_parts:
                    pkg.repo = repo
                    break
        
        # 提取基本信息
        pkg.version = self._extract_var(content, "pkgver") or ""
        pkg.release = self._parse_pkgrel(content)
        pkg.description = self._extract_var(content, "pkgdesc") or ""
        pkg.url = self._extract_var(content, "url") or ""
        pkg.license = self._extract_var(content, "license") or ""
        pkg.arch = self._extract_var(content, "arch") or "all"
        
        # 提取维护者信息
        maintainer_match = re.search(self.VAR_PATTERNS["maintainer"], content, re.MULTILINE)
        if maintainer_match:
            pkg.maintainer = maintainer_match.group(1).strip()
        
        # 提取贡献者
        for match in re.finditer(self.VAR_PATTERNS["contributor"], content, re.MULTILINE):
            pkg.contributors.append(match.group(1).strip())
        
        # 提取依赖关系
        pkg.depends = self._extract_dep_list(content, "depends")
        pkg.makedepends = self._extract_dep_list(content, "makedepends")
        pkg.makedepends_build = self._extract_dep_list(content, "makedepends_build")
        pkg.makedepends_host = self._extract_dep_list(content, "makedepends_host")
        pkg.checkdepends = self._extract_dep_list(content, "checkdepends")
        
        # 提取提供和替换
        pkg.provides = self._extract_dep_list(content, "provides")
        pkg.replaces = self._extract_dep_list(content, "replaces")
        
        # 提取子包
        pkg.subpackages = self._extract_subpackages(content, pkgname)
        
        return pkg
    
    def _parse_pkgrel(self, content: str) -> int:
        """
        解析 pkgrel 值，支持 shell 算术表达式
        
        处理以下格式：
        - pkgrel=0
        - pkgrel=$(( _krel + _rel ))
        - pkgrel=$((_rel + 1))
        """
        pkgrel_str = self._extract_var(content, "pkgrel")
        if not pkgrel_str:
            return 0
        
        # 简单数字
        if pkgrel_str.isdigit():
            return int(pkgrel_str)
        
        # 处理 shell 算术表达式 $(( ... ))
        arith_match = re.match(r'\$\(\(\s*(.+?)\s*\)\)', pkgrel_str)
        if arith_match:
            expr = arith_match.group(1)
            return self._eval_shell_arithmetic(content, expr)
        
        # 无法解析，返回 0
        return 0
    
    def _eval_shell_arithmetic(self, content: str, expr: str) -> int:
        """
        评估简单的 shell 算术表达式
        
        支持：变量引用、加法、减法、乘法
        """
        # 提取所有文件中定义的变量
        var_values = {}
        
        # 匹配 _varname=value 格式的变量定义
        var_pattern = r'^(_\w+)=(\d+)'
        for match in re.finditer(var_pattern, content, re.MULTILINE):
            var_name = match.group(1)
            var_value = match.group(2)
            var_values[var_name] = int(var_value)
        
        # 替换表达式中的变量
        def replace_var(m):
            var_name = m.group(0)
            return str(var_values.get(var_name, 0))
        
        # 替换变量引用
        expr = re.sub(r'_\w+', replace_var, expr)
        
        # 清理表达式（只保留数字和运算符）
        expr = re.sub(r'[^\d+\-*/\s]', '', expr)
        
        try:
            # 安全评估简单算术表达式
            # 只允许数字和基本运算符
            if re.match(r'^[\d\s+\-*/]+$', expr):
                return int(eval(expr))
        except:
            pass
        
        return 0
    
    def _extract_var(self, content: str, varname: str) -> Optional[str]:
        """提取简单变量值"""
        if varname in self._var_cache:
            return self._var_cache[varname]
        
        # 尝试匹配带引号的值
        pattern = rf'^{varname}="([^"]*)"'
        match = re.search(pattern, content, re.MULTILINE)
        if match:
            value = match.group(1).strip()
            self._var_cache[varname] = value
            return value
        
        # 尝试匹配不带引号的值
        pattern = rf'^{varname}=([^\s\n]+)'
        match = re.search(pattern, content, re.MULTILINE)
        if match:
            value = match.group(1).strip()
            self._var_cache[varname] = value
            return value
        
        return None
    
    def _extract_dep_list(self, content: str, varname: str) -> List[str]:
        """提取依赖列表（支持多行）"""
        deps = []
        
        # 匹配单行定义: varname="dep1 dep2"
        pattern = rf'^{varname}="([^"]*)"'
        match = re.search(pattern, content, re.MULTILINE)
        if match:
            deps_str = match.group(1)
            deps = self._parse_deps_string(deps_str)
            return deps
        
        # 匹配多行定义
        # varname="
        #   dep1
        #   dep2
        # "
        pattern = rf'^{varname}="\s*\n([\s\S]*?)(?:^[^\s#]|\Z)'
        match = re.search(pattern, content, re.MULTILINE)
        if match:
            # 找到多行定义的结束引号
            start_pattern = rf'^{varname}="'
            start_match = re.search(start_pattern, content, re.MULTILINE)
            if start_match:
                start_pos = start_match.end()
                # 找到匹配的结束引号（不在注释行中）
                end_pos = self._find_closing_quote(content, start_pos)
                if end_pos > start_pos:
                    deps_str = content[start_pos:end_pos]
                    deps = self._parse_deps_string(deps_str)
                    return deps
        
        # 尝试另一种多行格式
        # varname="dep1
        # dep2
        # dep3"
        lines = content.split('\n')
        in_var = False
        deps_str = ""
        
        for line in lines:
            stripped = line.strip()
            
            if not in_var:
                if stripped.startswith(f'{varname}="'):
                    in_var = True
                    # 提取开始引号后的内容
                    start = stripped.find('"') + 1
                    end = stripped.rfind('"')
                    if end > start:
                        # 单行定义
                        deps_str = stripped[start:end]
                        break
                    else:
                        # 多行开始
                        deps_str = stripped[start:]
            else:
                # 检查是否结束
                if '"' in stripped:
                    end = stripped.find('"')
                    deps_str += " " + stripped[:end]
                    break
                else:
                    deps_str += " " + stripped
        
        if deps_str:
            deps = self._parse_deps_string(deps_str)
        
        return deps
    
    def _find_closing_quote(self, content: str, start: int) -> int:
        """找到闭合引号的位置"""
        in_escape = False
        for i in range(start, len(content)):
            c = content[i]
            if in_escape:
                in_escape = False
                continue
            if c == '\\':
                in_escape = True
                continue
            if c == '"':
                return i
        return -1
    
    def _parse_deps_string(self, deps_str: str) -> List[str]:
        """解析依赖字符串"""
        deps = []
        
        # 移除注释
        lines = deps_str.split('\n')
        cleaned_lines = []
        for line in lines:
            # 移除 # 注释（但保留 $pkgname 等变量引用）
            comment_pos = line.find('#')
            if comment_pos >= 0:
                line = line[:comment_pos]
            cleaned_lines.append(line)
        
        deps_str = ' '.join(cleaned_lines)
        
        # 分割依赖项
        tokens = deps_str.split()
        
        for token in tokens:
            token = token.strip()
            if not token:
                continue
            
            # 跳过变量引用和特殊语法
            if token.startswith('$'):
                # 处理 $pkgname- 前缀的子包引用
                if token == '$pkgname' or token.startswith('$pkgname-'):
                    continue
                continue
            
            # 清理依赖名称
            dep = self._clean_dep_name(token)
            if dep:
                deps.append(dep)
        
        return deps
    
    def _clean_dep_name(self, dep: str) -> Optional[str]:
        """清理依赖名称，移除版本约束等"""
        if not dep:
            return None
        
        # 跳过空字符串和特殊字符
        if dep in ['', '\\', '"', "'", '(', ')']:
            return None
        
        # 移除前导的 ! (表示 NOT)
        if dep.startswith('!'):
            return None
        
        # 移除版本约束 (>=, <=, =, >, <, ~)
        dep = re.split(r'[><=~]', dep)[0]
        
        # 移除尾部的 -dev, -doc 等后缀变量引用
        # 保留实际的包名
        
        # 处理 :: 分隔符（表示子包）
        if '::' in dep:
            dep = dep.split('::')[0]
        
        # 移除括号内容
        dep = re.sub(r'\([^)]*\)', '', dep)
        
        dep = dep.strip()
        
        # 验证包名格式（基本检查）
        if not dep or not re.match(r'^[a-zA-Z0-9]', dep):
            return None
        
        return dep
    
    def _extract_subpackages(self, content: str, pkgname: str) -> List[str]:
        """提取子包列表"""
        subpkgs = []
        
        raw_subpkgs = self._extract_dep_list(content, "subpackages")
        
        for subpkg in raw_subpkgs:
            # 处理 $pkgname-xxx 格式
            if subpkg.startswith('$pkgname-'):
                subpkg = pkgname + subpkg[8:]
            elif subpkg.startswith('$pkgname'):
                continue
            
            # 处理 pkgname-xxx:funcname 格式
            if ':' in subpkg:
                subpkg = subpkg.split(':')[0]
            
            if subpkg and subpkg != pkgname:
                subpkgs.append(subpkg)
        
        return subpkgs


def test_parser():
    """测试解析器"""
    parser = APKBUILDParser()
    
    # 测试内容
    test_content = '''
# Contributor: Test User <test@example.com>
# Maintainer: Main User <main@example.com>
pkgname=test-package
pkgver=1.2.3
pkgrel=1
pkgdesc="A test package"
url="https://example.com"
arch="all"
license="MIT"
depends="dep1 dep2>=1.0"
makedepends="
    cmake
    gcc
    make
    "
subpackages="$pkgname-doc $pkgname-dev"
'''
    
    pkg = parser.parse_content(test_content, "/test/main/test-package/APKBUILD")
    
    if pkg:
        print(f"Package: {pkg.name}")
        print(f"Version: {pkg.version}-r{pkg.release}")
        print(f"Description: {pkg.description}")
        print(f"Depends: {pkg.depends}")
        print(f"Makedepends: {pkg.makedepends}")
        print(f"Subpackages: {pkg.subpackages}")
        print(f"Repo: {pkg.repo}")
    else:
        print("Failed to parse")


if __name__ == "__main__":
    test_parser()
