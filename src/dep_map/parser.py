"""
APKBUILD 文件解析器

解析 Alpine Linux APKBUILD 文件，提取软件包信息和依赖关系。
支持更复杂的 bash 脚本特性。
"""

import re
import os
from dataclasses import dataclass, field
from typing import List, Optional, Set, Dict, Any, Tuple
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


class BashVariableContext:
    """
    Bash 变量上下文，模拟简单的 bash 变量展开
    
    支持：
    - 简单变量赋值: var=value
    - 变量引用: $var, ${var}
    - 参数展开: ${var%%pattern}, ${var##pattern}, ${var:-default}
    - 条件赋值: [ test ] && var=val1 || var=val2
    """
    
    def __init__(self):
        self.variables: Dict[str, str] = {}
        # 预设一些常见的环境变量为空（表示本机构建）
        self._defaults = {
            "CHOST": "",
            "CTARGET": "",
            "CBUILD": "",
            "CARCH": "",
            "CTARGET_ARCH": "",
            "BOOTSTRAP": "",
            "CROSS_COMPILE": "",
        }
    
    def get(self, name: str, default: str = "") -> str:
        """获取变量值"""
        if name in self.variables:
            return self.variables[name]
        return self._defaults.get(name, default)
    
    def set(self, name: str, value: str):
        """设置变量值"""
        self.variables[name] = value
    
    def expand(self, value: str) -> str:
        """展开变量引用"""
        if not value:
            return value
        
        result = value
        
        # 展开 ${var%%pattern} - 移除最长后缀
        result = re.sub(
            r'\$\{(\w+)%%([^}]*)\}',
            lambda m: self._expand_remove_suffix(m.group(1), m.group(2), longest=True),
            result
        )
        
        # 展开 ${var%pattern} - 移除最短后缀
        result = re.sub(
            r'\$\{(\w+)%([^}]*)\}',
            lambda m: self._expand_remove_suffix(m.group(1), m.group(2), longest=False),
            result
        )
        
        # 展开 ${var##pattern} - 移除最长前缀
        result = re.sub(
            r'\$\{(\w+)##([^}]*)\}',
            lambda m: self._expand_remove_prefix(m.group(1), m.group(2), longest=True),
            result
        )
        
        # 展开 ${var#pattern} - 移除最短前缀
        result = re.sub(
            r'\$\{(\w+)#([^}]*)\}',
            lambda m: self._expand_remove_prefix(m.group(1), m.group(2), longest=False),
            result
        )
        
        # 展开 ${var:-default} - 默认值
        result = re.sub(
            r'\$\{(\w+):-([^}]*)\}',
            lambda m: self.get(m.group(1)) or m.group(2),
            result
        )
        
        # 展开 ${var:=default} - 赋默认值
        result = re.sub(
            r'\$\{(\w+):=([^}]*)\}',
            lambda m: self._expand_assign_default(m.group(1), m.group(2)),
            result
        )
        
        # 展开 ${var} 格式
        result = re.sub(
            r'\$\{(\w+)\}',
            lambda m: self.get(m.group(1)),
            result
        )
        
        # 展开 $var 格式（注意要避免匹配 $( 等）
        result = re.sub(
            r'\$([a-zA-Z_]\w*)(?![(\w])',
            lambda m: self.get(m.group(1)),
            result
        )
        
        return result
    
    def _expand_remove_suffix(self, varname: str, pattern: str, longest: bool) -> str:
        """移除后缀模式"""
        value = self.get(varname)
        if not value or not pattern:
            return value
        
        # 简单处理：将 shell 通配符转换为正则
        regex_pattern = pattern.replace('*', '.*').replace('?', '.')
        
        if longest:
            # 贪婪匹配
            match = re.search(f'({regex_pattern})$', value)
            if match:
                return value[:match.start()]
        else:
            # 非贪婪匹配
            match = re.search(f'({regex_pattern.replace(".*", ".*?")})$', value)
            if match:
                return value[:match.start()]
        
        return value
    
    def _expand_remove_prefix(self, varname: str, pattern: str, longest: bool) -> str:
        """移除前缀模式"""
        value = self.get(varname)
        if not value or not pattern:
            return value
        
        # 简单处理：将 shell 通配符转换为正则
        regex_pattern = pattern.replace('*', '.*').replace('?', '.')
        
        if longest:
            # 贪婪匹配
            match = re.search(f'^({regex_pattern})', value)
            if match:
                return value[match.end():]
        else:
            # 非贪婪匹配
            match = re.search(f'^({regex_pattern.replace(".*", ".*?")})', value)
            if match:
                return value[match.end():]
        
        return value
    
    def _expand_assign_default(self, varname: str, default: str) -> str:
        """如果变量为空则赋予默认值"""
        value = self.get(varname)
        if not value:
            self.set(varname, default)
            return default
        return value


class APKBUILDParser:
    """
    APKBUILD 文件解析器
    
    更接近 bash 脚本的解析行为，支持：
    - 变量展开和参数替换
    - 条件语句（简单处理）
    - 多行字符串
    - 子包解析
    """
    
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
        self._ctx: BashVariableContext = BashVariableContext()
        self._first_pkgname: Optional[str] = None  # 保存第一次定义的 pkgname
    
    def parse_file(self, filepath: str) -> Optional[PackageInfo]:
        """解析 APKBUILD 文件"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return self.parse_content(content, filepath)
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
            return None
    
    # 为了兼容旧代码，添加别名
    parse = parse_file
    
    def parse_content(self, content: str, filepath: str = "") -> Optional[PackageInfo]:
        """解析 APKBUILD 内容"""
        self._ctx = BashVariableContext()
        self._first_pkgname = None
        
        # 第一遍：解析所有变量赋值
        self._parse_variables(content)
        
        # 获取包名（优先使用第一次定义的 pkgname）
        pkgname = self._first_pkgname or self._ctx.get("pkgname")
        if not pkgname:
            return None
        
        # 清理包名（移除引号和空白）
        pkgname = pkgname.strip().strip('"\'')
        
        # 如果 pkgname 仍然包含未展开的变量，尝试从文件路径推断
        if '$' in pkgname and filepath:
            dir_name = Path(filepath).parent.name
            if dir_name and not dir_name.startswith('.'):
                pkgname = dir_name
        
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
        pkg.version = self._ctx.expand(self._ctx.get("pkgver")) or ""
        pkg.release = self._parse_pkgrel(content)
        pkg.description = self._ctx.get("pkgdesc", "").strip('"')
        pkg.url = self._ctx.get("url", "").strip('"')
        pkg.license = self._ctx.get("license", "").strip('"')
        pkg.arch = self._ctx.get("arch", "all").strip('"')
        
        # 提取维护者信息
        maintainer_match = re.search(r'^#\s*Maintainer:\s*(.+)$', content, re.MULTILINE)
        if maintainer_match:
            pkg.maintainer = maintainer_match.group(1).strip()
        
        # 提取贡献者
        for match in re.finditer(r'^#\s*Contributor:\s*(.+)$', content, re.MULTILINE):
            pkg.contributors.append(match.group(1).strip())
        
        # 提取依赖关系
        pkg.depends = self._extract_dep_list(content, "depends", pkgname)
        pkg.makedepends = self._extract_dep_list(content, "makedepends", pkgname)
        pkg.makedepends_build = self._extract_dep_list(content, "makedepends_build", pkgname)
        pkg.makedepends_host = self._extract_dep_list(content, "makedepends_host", pkgname)
        pkg.checkdepends = self._extract_dep_list(content, "checkdepends", pkgname)
        
        # 提取提供和替换
        pkg.provides = self._extract_dep_list(content, "provides", pkgname)
        pkg.replaces = self._extract_dep_list(content, "replaces", pkgname)
        
        # 提取子包
        pkg.subpackages = self._extract_subpackages(content, pkgname)
        
        return pkg
    
    def _parse_variables(self, content: str):
        """
        解析内容中的变量赋值
        
        处理：
        - 简单赋值: var=value
        - 带引号赋值: var="value"
        - 条件赋值: [ test ] && var=val
        """
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # 跳过注释和空行
            if not line or line.startswith('#'):
                continue
            
            # 处理简单变量赋值: var=value 或 var="value"
            assign_match = re.match(r'^([a-zA-Z_]\w*)=(.*)$', line)
            if assign_match:
                varname = assign_match.group(1)
                value = assign_match.group(2).strip()
                
                # 移除引号
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                # 展开变量引用
                expanded_value = self._ctx.expand(value)
                
                # 保存第一次定义的 pkgname
                if varname == "pkgname" and self._first_pkgname is None:
                    # 如果值不包含变量引用，直接使用
                    if '$' not in value:
                        self._first_pkgname = expanded_value
                    else:
                        # 包含变量引用，先存储原始值
                        self._first_pkgname = expanded_value if expanded_value and '$' not in expanded_value else None
                
                self._ctx.set(varname, expanded_value)
                continue
            
            # 处理条件赋值: [ test ] && var=val1 || var=val2
            # 简化处理：假设测试条件为 false（本机构建场景）
            cond_match = re.match(r'^\[.*\]\s*&&\s*([a-zA-Z_]\w*)=([^\s|]+)(?:\s*\|\|\s*([a-zA-Z_]\w*)=(.+))?', line)
            if cond_match:
                # 使用 || 后的值（条件为 false 时的值）
                if cond_match.group(3) and cond_match.group(4):
                    varname = cond_match.group(3)
                    value = cond_match.group(4).strip().strip('"\'')
                    self._ctx.set(varname, self._ctx.expand(value))
                continue
            
            # 处理 : "${VAR:=default}" 格式的默认值设置
            default_match = re.match(r'^:\s*"\$\{([a-zA-Z_]\w*):=([^}]*)\}"', line)
            if default_match:
                varname = default_match.group(1)
                default = default_match.group(2)
                if not self._ctx.get(varname):
                    self._ctx.set(varname, default)
    
    def _parse_pkgrel(self, content: str) -> int:
        """
        解析 pkgrel 值，支持 shell 算术表达式
        """
        pkgrel_str = self._ctx.get("pkgrel")
        if not pkgrel_str:
            # 尝试直接从内容提取
            match = re.search(r'^pkgrel=(\S+)', content, re.MULTILINE)
            if match:
                pkgrel_str = match.group(1)
        
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
        
        return 0
    
    def _eval_shell_arithmetic(self, content: str, expr: str) -> int:
        """评估简单的 shell 算术表达式"""
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
        
        expr = re.sub(r'_\w+', replace_var, expr)
        expr = re.sub(r'[^\d+\-*/\s]', '', expr)
        
        try:
            if re.match(r'^[\d\s+\-*/]+$', expr):
                return int(eval(expr))
        except:
            pass
        
        return 0
    
    def _extract_dep_list(self, content: str, varname: str, pkgname: str = "") -> List[str]:
        """提取依赖列表（支持多行和变量展开）"""
        deps = []
        
        # 首先尝试从变量上下文获取
        value = self._ctx.get(varname)
        if value and value.strip() and value.strip() != ' ':
            deps = self._parse_deps_string(value, pkgname)
            if deps:
                return deps
        
        # 否则尝试直接从内容解析多行定义
        deps_str = self._extract_multiline_var(content, varname)
        if deps_str:
            deps = self._parse_deps_string(deps_str, pkgname)
        
        return deps
    
    def _extract_multiline_var(self, content: str, varname: str) -> str:
        """提取可能跨多行的变量值"""
        lines = content.split('\n')
        in_var = False
        result = []
        quote_char = None
        
        for line in lines:
            if not in_var:
                # 查找变量定义开始
                match = re.match(rf'^{varname}=(.*)$', line)
                if match:
                    value = match.group(1)
                    
                    # 检查是否是带引号的多行
                    if value.startswith('"'):
                        if value.endswith('"') and len(value) > 1:
                            # 单行完整定义
                            return value[1:-1]
                        else:
                            # 多行开始
                            in_var = True
                            quote_char = '"'
                            result.append(value[1:])
                    elif value.startswith("'"):
                        if value.endswith("'") and len(value) > 1:
                            return value[1:-1]
                        else:
                            in_var = True
                            quote_char = "'"
                            result.append(value[1:])
                    else:
                        # 不带引号的单行
                        return value
            else:
                # 在多行变量中
                if quote_char and quote_char in line:
                    # 找到结束引号
                    end_pos = line.find(quote_char)
                    result.append(line[:end_pos])
                    break
                else:
                    result.append(line)
        
        return ' '.join(result)
    
    def _parse_deps_string(self, deps_str: str, pkgname: str = "") -> List[str]:
        """解析依赖字符串"""
        deps = []
        
        # 移除注释
        lines = deps_str.split('\n')
        cleaned_lines = []
        for line in lines:
            comment_pos = line.find('#')
            if comment_pos >= 0:
                line = line[:comment_pos]
            cleaned_lines.append(line)
        
        deps_str = ' '.join(cleaned_lines)
        
        # 展开变量
        deps_str = self._ctx.expand(deps_str)
        
        # 分割依赖项
        tokens = deps_str.split()
        
        for token in tokens:
            token = token.strip()
            if not token:
                continue
            
            # 跳过仍然包含变量引用的 token
            if '$' in token:
                # 尝试替换 $pkgname
                if pkgname and '$pkgname' in token:
                    token = token.replace('$pkgname', pkgname)
                else:
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
        if dep in ['', '\\', '"', "'", '(', ')', ' ']:
            return None
        
        # 移除前导的 ! (表示 NOT/冲突)
        if dep.startswith('!'):
            return None
        
        # 移除版本约束 (>=, <=, =, >, <, ~)
        dep = re.split(r'[><=~]', dep)[0]
        
        # 处理 :: 分隔符（表示子包）
        if '::' in dep:
            dep = dep.split('::')[0]
        
        # 移除括号内容
        dep = re.sub(r'\([^)]*\)', '', dep)
        
        dep = dep.strip()
        
        # 验证包名格式
        if not dep or not re.match(r'^[a-zA-Z0-9]', dep):
            return None
        
        return dep
    
    def _extract_subpackages(self, content: str, pkgname: str) -> List[str]:
        """提取子包列表"""
        subpkgs = []
        
        raw_subpkgs = self._extract_dep_list(content, "subpackages", pkgname)
        
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
    
    # 测试 gcc APKBUILD
    print("Testing gcc APKBUILD...")
    result = parser.parse_file("/home/sanchuanhehe/Documents/aports/main/gcc/APKBUILD")
    if result:
        print(f"  pkgname: {result.name}")
        print(f"  version: {result.version}-r{result.release}")
        print(f"  depends: {result.depends}")
        print(f"  makedepends_build: {result.makedepends_build[:5]}...")
    else:
        print("  Failed to parse")
    
    print()
    
    # 测试普通 APKBUILD
    print("Testing curl APKBUILD...")
    result = parser.parse_file("/home/sanchuanhehe/Documents/aports/main/curl/APKBUILD")
    if result:
        print(f"  pkgname: {result.name}")
        print(f"  version: {result.version}-r{result.release}")
        print(f"  depends: {result.depends}")
    else:
        print("  Failed to parse")


if __name__ == "__main__":
    test_parser()
