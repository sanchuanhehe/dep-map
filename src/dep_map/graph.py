"""
依赖关系图谱构建器

使用 NetworkX 构建和操作软件包依赖关系图。
"""

import json
from collections import deque
from typing import Dict, List, Set, Optional, Tuple, Iterator
from dataclasses import dataclass
from enum import Enum

try:
    import networkx as nx
except ImportError:
    nx = None

from .parser import PackageInfo


class DependencyType(Enum):
    """依赖类型"""
    RUNTIME = "runtime"      # 运行时依赖
    BUILD = "build"          # 构建依赖
    CHECK = "check"          # 测试依赖
    ALL = "all"              # 所有依赖


@dataclass
class DependencyInfo:
    """依赖信息"""
    package: str
    dependency: str
    dep_type: DependencyType
    depth: int = 0


class DependencyGraph:
    """依赖关系图"""
    
    def __init__(self, packages: Optional[Dict[str, PackageInfo]] = None):
        """
        初始化依赖图
        
        Args:
            packages: 软件包信息字典
        """
        if nx is None:
            raise ImportError("networkx is required. Install with: pip install networkx")
        
        self.packages = packages or {}
        self._graph: nx.DiGraph = nx.DiGraph()
        self._reverse_graph: nx.DiGraph = nx.DiGraph()
        self._provides_map: Dict[str, str] = {}
        self._subpkg_map: Dict[str, str] = {}
        
        if packages:
            self._build_graph()
    
    def _build_graph(self):
        """构建依赖图"""
        # 首先建立 provides 和 subpackage 映射
        for name, pkg in self.packages.items():
            # 添加节点
            self._graph.add_node(name, **pkg.to_dict())
            
            # provides 映射
            for prov in pkg.provides:
                prov_name = prov.split('=')[0].split('>')[0].split('<')[0]
                self._provides_map[prov_name] = name
            
            # subpackage 映射
            for subpkg in pkg.subpackages:
                self._subpkg_map[subpkg] = name
        
        # 添加依赖边
        for name, pkg in self.packages.items():
            # 运行时依赖
            for dep in pkg.depends:
                resolved = self._resolve_dep(dep)
                if resolved and resolved in self._graph:
                    self._graph.add_edge(name, resolved, type="runtime")
            
            # 构建依赖
            for dep in pkg.build_depends:
                resolved = self._resolve_dep(dep)
                if resolved and resolved in self._graph:
                    self._graph.add_edge(name, resolved, type="build")
            
            # 测试依赖
            for dep in pkg.checkdepends:
                resolved = self._resolve_dep(dep)
                if resolved and resolved in self._graph:
                    self._graph.add_edge(name, resolved, type="check")
        
        # 构建反向图
        self._reverse_graph = self._graph.reverse(copy=True)
    
    def _resolve_dep(self, dep: str) -> Optional[str]:
        """解析依赖名称"""
        # 直接匹配
        if dep in self.packages:
            return dep
        
        # provides 匹配
        if dep in self._provides_map:
            return self._provides_map[dep]
        
        # subpackage 匹配
        if dep in self._subpkg_map:
            return self._subpkg_map[dep]
        
        return None
    
    def add_package(self, pkg: PackageInfo):
        """添加软件包"""
        self.packages[pkg.name] = pkg
        self._graph.add_node(pkg.name, **pkg.to_dict())
        
        # 更新映射
        for prov in pkg.provides:
            prov_name = prov.split('=')[0]
            self._provides_map[prov_name] = pkg.name
        
        for subpkg in pkg.subpackages:
            self._subpkg_map[subpkg] = pkg.name
        
        # 添加边
        for dep in pkg.depends:
            resolved = self._resolve_dep(dep)
            if resolved and resolved in self._graph:
                self._graph.add_edge(pkg.name, resolved, type="runtime")
        
        for dep in pkg.build_depends:
            resolved = self._resolve_dep(dep)
            if resolved and resolved in self._graph:
                self._graph.add_edge(pkg.name, resolved, type="build")
    
    def get_dependencies(
        self, 
        package: str, 
        dep_type: DependencyType = DependencyType.ALL,
        recursive: bool = False,
        max_depth: int = -1
    ) -> List[str]:
        """
        获取软件包的依赖
        
        Args:
            package: 软件包名称
            dep_type: 依赖类型
            recursive: 是否递归获取所有依赖
            max_depth: 最大深度，-1 表示无限制
            
        Returns:
            依赖列表
        """
        if package not in self._graph:
            return []
        
        if recursive:
            return self._get_recursive_deps(package, dep_type, max_depth)
        else:
            return self._get_direct_deps(package, dep_type)
    
    def _get_direct_deps(self, package: str, dep_type: DependencyType) -> List[str]:
        """获取直接依赖"""
        deps = []
        
        for _, target, data in self._graph.out_edges(package, data=True):
            edge_type = data.get("type", "runtime")
            
            if dep_type == DependencyType.ALL:
                deps.append(target)
            elif dep_type == DependencyType.RUNTIME and edge_type == "runtime":
                deps.append(target)
            elif dep_type == DependencyType.BUILD and edge_type == "build":
                deps.append(target)
            elif dep_type == DependencyType.CHECK and edge_type == "check":
                deps.append(target)
        
        return sorted(set(deps))
    
    def _get_recursive_deps(
        self, 
        package: str, 
        dep_type: DependencyType,
        max_depth: int
    ) -> List[str]:
        """递归获取所有依赖"""
        visited = set()
        queue = deque([(package, 0)])
        
        while queue:
            current, depth = queue.popleft()
            
            if current in visited:
                continue
            
            if max_depth >= 0 and depth > max_depth:
                continue
            
            visited.add(current)
            
            for dep in self._get_direct_deps(current, dep_type):
                if dep not in visited:
                    queue.append((dep, depth + 1))
        
        visited.discard(package)
        return sorted(visited)
    
    def get_reverse_dependencies(
        self, 
        package: str,
        dep_type: DependencyType = DependencyType.ALL,
        recursive: bool = False,
        max_depth: int = -1
    ) -> List[str]:
        """
        获取反向依赖（哪些包依赖此包）
        
        Args:
            package: 软件包名称
            dep_type: 依赖类型
            recursive: 是否递归
            max_depth: 最大深度
            
        Returns:
            依赖此包的包列表
        """
        if package not in self._reverse_graph:
            return []
        
        if recursive:
            return self._get_recursive_rdeps(package, dep_type, max_depth)
        else:
            return self._get_direct_rdeps(package, dep_type)
    
    def _get_direct_rdeps(self, package: str, dep_type: DependencyType) -> List[str]:
        """获取直接反向依赖"""
        rdeps = []
        
        for _, target, data in self._reverse_graph.out_edges(package, data=True):
            edge_type = data.get("type", "runtime")
            
            if dep_type == DependencyType.ALL:
                rdeps.append(target)
            elif dep_type == DependencyType.RUNTIME and edge_type == "runtime":
                rdeps.append(target)
            elif dep_type == DependencyType.BUILD and edge_type == "build":
                rdeps.append(target)
            elif dep_type == DependencyType.CHECK and edge_type == "check":
                rdeps.append(target)
        
        return sorted(set(rdeps))
    
    def _get_recursive_rdeps(
        self, 
        package: str,
        dep_type: DependencyType,
        max_depth: int
    ) -> List[str]:
        """递归获取所有反向依赖"""
        visited = set()
        queue = deque([(package, 0)])
        
        while queue:
            current, depth = queue.popleft()
            
            if current in visited:
                continue
            
            if max_depth >= 0 and depth > max_depth:
                continue
            
            visited.add(current)
            
            for rdep in self._get_direct_rdeps(current, dep_type):
                if rdep not in visited:
                    queue.append((rdep, depth + 1))
        
        visited.discard(package)
        return sorted(visited)
    
    def get_dependency_tree(
        self, 
        package: str,
        dep_type: DependencyType = DependencyType.ALL,
        max_depth: int = 3
    ) -> dict:
        """
        获取依赖树结构
        
        Args:
            package: 软件包名称
            dep_type: 依赖类型
            max_depth: 最大深度
            
        Returns:
            树形结构字典
        """
        def build_tree(pkg: str, depth: int, visited: Set[str]) -> dict:
            if depth > max_depth or pkg in visited:
                return {"name": pkg, "children": [], "truncated": True}
            
            visited.add(pkg)
            children = []
            
            for dep in self._get_direct_deps(pkg, dep_type):
                child_tree = build_tree(dep, depth + 1, visited.copy())
                children.append(child_tree)
            
            return {
                "name": pkg,
                "children": children,
                "truncated": False
            }
        
        return build_tree(package, 0, set())
    
    def get_dependency_path(
        self, 
        source: str, 
        target: str
    ) -> Optional[List[str]]:
        """
        获取两个包之间的依赖路径
        
        Args:
            source: 源包
            target: 目标包
            
        Returns:
            依赖路径，如果不存在则返回 None
        """
        if source not in self._graph or target not in self._graph:
            return None
        
        try:
            return nx.shortest_path(self._graph, source, target)
        except nx.NetworkXNoPath:
            return None
    
    def find_cycles(self) -> List[List[str]]:
        """查找循环依赖"""
        try:
            cycles = list(nx.simple_cycles(self._graph))
            return cycles
        except:
            return []
    
    def get_dependency_depth(self, package: str) -> int:
        """获取软件包的依赖深度（到根的最长路径）"""
        if package not in self._graph:
            return 0
        
        deps = self.get_dependencies(package, recursive=True)
        if not deps:
            return 0
        
        max_depth = 0
        for dep in deps:
            path = self.get_dependency_path(package, dep)
            if path:
                max_depth = max(max_depth, len(path) - 1)
        
        return max_depth
    
    def get_most_depended(self, top_n: int = 20) -> List[Tuple[str, int]]:
        """获取被依赖最多的包"""
        counts = {}
        for pkg in self.packages:
            rdeps = self.get_reverse_dependencies(pkg)
            counts[pkg] = len(rdeps)
        
        sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_counts[:top_n]
    
    def get_most_dependencies(self, top_n: int = 20) -> List[Tuple[str, int]]:
        """获取依赖最多的包"""
        counts = {}
        for pkg in self.packages:
            deps = self.get_dependencies(pkg, recursive=True)
            counts[pkg] = len(deps)
        
        sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_counts[:top_n]
    
    def get_leaf_packages(self) -> List[str]:
        """获取叶子包（没有被其他包依赖的包）"""
        leaves = []
        for pkg in self.packages:
            if not self.get_reverse_dependencies(pkg):
                leaves.append(pkg)
        return sorted(leaves)
    
    def get_root_packages(self) -> List[str]:
        """获取根包（没有依赖其他包的包）"""
        roots = []
        for pkg in self.packages:
            if not self.get_dependencies(pkg):
                roots.append(pkg)
        return sorted(roots)
    
    def get_subgraph(
        self, 
        packages: List[str],
        include_deps: bool = True,
        max_depth: int = 2
    ) -> 'DependencyGraph':
        """
        获取子图
        
        Args:
            packages: 包列表
            include_deps: 是否包含依赖
            max_depth: 包含依赖时的最大深度
            
        Returns:
            子图
        """
        nodes = set(packages)
        
        if include_deps:
            for pkg in packages:
                deps = self.get_dependencies(pkg, recursive=True, max_depth=max_depth)
                nodes.update(deps)
        
        subgraph_pkgs = {
            name: self.packages[name] 
            for name in nodes 
            if name in self.packages
        }
        
        return DependencyGraph(subgraph_pkgs)
    
    def to_dict(self) -> dict:
        """导出为字典"""
        nodes = []
        edges = []
        
        for node in self._graph.nodes():
            node_data = dict(self._graph.nodes[node])
            node_data["id"] = node
            nodes.append(node_data)
        
        for source, target, data in self._graph.edges(data=True):
            edges.append({
                "source": source,
                "target": target,
                "type": data.get("type", "runtime")
            })
        
        return {"nodes": nodes, "edges": edges}
    
    def to_json(self, filepath: str):
        """导出为 JSON 文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    def get_statistics(self) -> dict:
        """获取图统计信息"""
        return {
            "nodes": self._graph.number_of_nodes(),
            "edges": self._graph.number_of_edges(),
            "density": nx.density(self._graph),
            "is_dag": nx.is_directed_acyclic_graph(self._graph),
            "weakly_connected_components": nx.number_weakly_connected_components(self._graph),
            "avg_in_degree": sum(d for _, d in self._graph.in_degree()) / self._graph.number_of_nodes() if self._graph.number_of_nodes() > 0 else 0,
            "avg_out_degree": sum(d for _, d in self._graph.out_degree()) / self._graph.number_of_nodes() if self._graph.number_of_nodes() > 0 else 0,
        }


def test_graph():
    """测试依赖图"""
    from .parser import PackageInfo
    
    # 创建测试包
    packages = {
        "app": PackageInfo(
            name="app",
            depends=["libfoo", "libbar"],
            makedepends=["cmake", "gcc"]
        ),
        "libfoo": PackageInfo(
            name="libfoo",
            depends=["libc"],
            makedepends=["gcc"]
        ),
        "libbar": PackageInfo(
            name="libbar",
            depends=["libc", "libfoo"],
        ),
        "libc": PackageInfo(name="libc"),
        "cmake": PackageInfo(name="cmake", depends=["libc"]),
        "gcc": PackageInfo(name="gcc", depends=["libc"]),
    }
    
    graph = DependencyGraph(packages)
    
    print("Dependencies of app:", graph.get_dependencies("app"))
    print("All deps of app:", graph.get_dependencies("app", recursive=True))
    print("Reverse deps of libc:", graph.get_reverse_dependencies("libc"))
    print("Path app -> libc:", graph.get_dependency_path("app", "libc"))
    print("Statistics:", graph.get_statistics())


if __name__ == "__main__":
    test_graph()
