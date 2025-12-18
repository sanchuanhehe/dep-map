"""
依赖关系可视化模块

生成交互式依赖关系图。
支持按依赖类型过滤和不同样式显示。
"""

import json
from typing import Any

from .graph import DependencyGraph, DependencyType


class Visualizer:
    """依赖关系可视化器"""

    # 节点颜色配置（按仓库）
    REPO_COLORS = {
        "main": "#4CAF50",  # 绿色
        "community": "#2196F3",  # 蓝色
        "testing": "#FF9800",  # 橙色
        "unmaintained": "#9E9E9E",  # 灰色
        "unknown": "#E0E0E0",  # 浅灰
    }

    # 边颜色配置（按依赖类型）
    EDGE_STYLES = {
        "runtime": {
            "color": "#4CAF50",  # 绿色 - 运行时依赖
            "dashes": False,  # 实线
            "width": 2,
        },
        "build": {
            "color": "#2196F3",  # 蓝色 - 构建依赖
            "dashes": [5, 5],  # 虚线
            "width": 1.5,
        },
        "check": {
            "color": "#FF9800",  # 橙色 - 检查依赖
            "dashes": [2, 2],  # 点线
            "width": 1,
        },
    }

    def __init__(self, graph: DependencyGraph):
        """
        初始化可视化器

        Args:
            graph: 依赖图
        """
        self.graph = graph

    def render_html(
        self,
        package: str,
        output_path: str,
        dep_type: DependencyType = DependencyType.RUNTIME,  # 默认只显示运行时依赖
        max_depth: int = 3,
        include_reverse: bool = False,
        show_all_types: bool = False,  # 是否显示所有类型（用不同样式区分）
        title: str | None = None,
    ):
        """
        渲染为交互式 HTML 文件

        Args:
            package: 中心软件包
            output_path: 输出文件路径
            dep_type: 依赖类型（默认只显示运行时依赖）
            max_depth: 最大深度
            include_reverse: 是否包含反向依赖
            show_all_types: 是否显示所有依赖类型（用不同样式区分）
            title: 页面标题
        """
        if show_all_types:
            # 收集所有类型的依赖，用不同样式显示
            nodes_to_show, edges_data = self._collect_all_dep_types(
                package, max_depth, include_reverse
            )
        else:
            # 只收集指定类型的依赖
            nodes_to_show, edges_data = self._collect_single_dep_type(
                package, dep_type, max_depth, include_reverse
            )

        # 构建节点数据
        nodes_data = []
        for node in nodes_to_show:
            pkg_info = self.graph.packages.get(node)
            repo = pkg_info.repo if pkg_info else "unknown"

            node_data = {
                "id": node,
                "label": node,
                "color": self.REPO_COLORS.get(repo, self.REPO_COLORS["unknown"]),
                "size": 30 if node == package else 20,
                "font": {"size": 14 if node == package else 12},
            }

            if pkg_info:
                node_data["title"] = self._make_tooltip(pkg_info)

            nodes_data.append(node_data)

        # 生成 HTML（带过滤器控制）
        html_content = self._generate_filterable_html(
            nodes_data,
            edges_data,
            package=package,
            title=title or f"Dependency Graph: {package}",
            show_all_types=show_all_types,
        )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    def _collect_single_dep_type(
        self, package: str, dep_type: DependencyType, max_depth: int, include_reverse: bool
    ) -> tuple:
        """收集单一类型的依赖"""
        nodes_to_show = {package}
        edges_data = []

        # 添加依赖
        deps = self.graph.get_dependencies(
            package, dep_type=dep_type, recursive=True, max_depth=max_depth
        )
        nodes_to_show.update(deps)

        # 添加反向依赖
        if include_reverse:
            rdeps = self.graph.get_reverse_dependencies(
                package, dep_type=dep_type, recursive=True, max_depth=max_depth
            )
            nodes_to_show.update(rdeps)

        # 确定边的样式
        if dep_type == DependencyType.RUNTIME:
            edge_style = self.EDGE_STYLES["runtime"]
            edge_type = "runtime"
        elif dep_type == DependencyType.BUILD:
            edge_style = self.EDGE_STYLES["build"]
            edge_type = "build"
        else:
            edge_style = self.EDGE_STYLES["runtime"]
            edge_type = "runtime"

        # 添加边
        for node in nodes_to_show:
            for dep in self.graph.get_dependencies(node, dep_type=dep_type):
                if dep in nodes_to_show:
                    edges_data.append(
                        {
                            "from": node,
                            "to": dep,
                            "arrows": "to",
                            "color": {"color": edge_style["color"], "opacity": 0.8},
                            "dashes": edge_style["dashes"],
                            "width": edge_style["width"],
                            "depType": edge_type,
                        }
                    )

        return nodes_to_show, edges_data

    def _collect_all_dep_types(self, package: str, max_depth: int, include_reverse: bool) -> tuple:
        """收集所有类型的依赖，用不同样式区分"""
        nodes_to_show = {package}
        edges_data = []
        edge_set = set()  # 避免重复边

        pkg_info = self.graph.packages.get(package)
        if not pkg_info:
            return nodes_to_show, edges_data

        # 递归收集依赖
        def collect_deps_recursive(pkg_name: str, current_depth: int, visited: set[str]):
            if current_depth > max_depth or pkg_name in visited:
                return
            visited.add(pkg_name)

            pkg = self.graph.packages.get(pkg_name)
            if not pkg:
                return

            # 运行时依赖
            for dep in pkg.depends:
                if dep in self.graph.packages:
                    nodes_to_show.add(dep)
                    edge_key = (pkg_name, dep, "runtime")
                    if edge_key not in edge_set:
                        edge_set.add(edge_key)
                        style = self.EDGE_STYLES["runtime"]
                        edges_data.append(
                            {
                                "from": pkg_name,
                                "to": dep,
                                "arrows": "to",
                                "color": {"color": style["color"], "opacity": 0.8},
                                "dashes": style["dashes"],
                                "width": style["width"],
                                "depType": "runtime",
                            }
                        )
                    collect_deps_recursive(dep, current_depth + 1, visited.copy())

            # 构建依赖
            for dep in pkg.build_depends:
                if dep in self.graph.packages:
                    nodes_to_show.add(dep)
                    edge_key = (pkg_name, dep, "build")
                    if edge_key not in edge_set:
                        edge_set.add(edge_key)
                        style = self.EDGE_STYLES["build"]
                        edges_data.append(
                            {
                                "from": pkg_name,
                                "to": dep,
                                "arrows": "to",
                                "color": {"color": style["color"], "opacity": 0.6},
                                "dashes": style["dashes"],
                                "width": style["width"],
                                "depType": "build",
                            }
                        )
                    collect_deps_recursive(dep, current_depth + 1, visited.copy())

            # 检查依赖
            for dep in pkg.checkdepends:
                if dep in self.graph.packages:
                    nodes_to_show.add(dep)
                    edge_key = (pkg_name, dep, "check")
                    if edge_key not in edge_set:
                        edge_set.add(edge_key)
                        style = self.EDGE_STYLES["check"]
                        edges_data.append(
                            {
                                "from": pkg_name,
                                "to": dep,
                                "arrows": "to",
                                "color": {"color": style["color"], "opacity": 0.5},
                                "dashes": style["dashes"],
                                "width": style["width"],
                                "depType": "check",
                            }
                        )
                    collect_deps_recursive(dep, current_depth + 1, visited.copy())

        collect_deps_recursive(package, 0, set())

        return nodes_to_show, edges_data

    def _generate_filterable_html(
        self,
        nodes: list[dict],
        edges: list[dict],
        package: str,
        title: str,
        show_all_types: bool = False,
    ) -> str:
        """生成带依赖类型过滤器的 HTML"""
        return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #1a1a2e;
            color: #eee;
        }}
        #header {{
            background: #16213e;
            padding: 12px 20px;
            border-bottom: 1px solid #0f3460;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        #header h1 {{
            font-size: 1.3rem;
            font-weight: 500;
        }}
        #filter-controls {{
            display: flex;
            gap: 15px;
            align-items: center;
        }}
        .filter-group {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .filter-group label {{
            display: flex;
            align-items: center;
            gap: 5px;
            cursor: pointer;
            padding: 5px 10px;
            border-radius: 4px;
            transition: background 0.2s;
        }}
        .filter-group label:hover {{
            background: rgba(255,255,255,0.1);
        }}
        .filter-group input[type="checkbox"] {{
            width: 16px;
            height: 16px;
            cursor: pointer;
        }}
        .dep-indicator {{
            display: inline-block;
            width: 20px;
            height: 3px;
            margin-right: 5px;
        }}
        .dep-runtime {{ background: #4CAF50; }}
        .dep-build {{ background: #2196F3; background: repeating-linear-gradient(90deg, #2196F3 0px, #2196F3 5px, transparent 5px, transparent 10px); }}
        .dep-check {{ background: #FF9800; background: repeating-linear-gradient(90deg, #FF9800 0px, #FF9800 2px, transparent 2px, transparent 4px); }}
        #container {{
            display: flex;
            height: calc(100vh - 55px);
        }}
        #network {{
            flex: 1;
            background: #1a1a2e;
        }}
        #sidebar {{
            width: 280px;
            background: #16213e;
            padding: 15px;
            overflow-y: auto;
            border-left: 1px solid #0f3460;
        }}
        #sidebar h3 {{
            margin-bottom: 10px;
            color: #e94560;
            font-size: 1rem;
        }}
        #search-box {{
            width: 100%;
            padding: 8px;
            margin-bottom: 15px;
            background: #1a1a2e;
            border: 1px solid #0f3460;
            color: #eee;
            border-radius: 4px;
        }}
        #search-box:focus {{
            outline: none;
            border-color: #e94560;
        }}
        #info {{
            font-size: 0.85rem;
            line-height: 1.5;
        }}
        #info p {{
            margin: 6px 0;
        }}
        #info .label {{
            color: #888;
        }}
        #legend {{
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #0f3460;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            margin: 8px 0;
            font-size: 0.85rem;
        }}
        .legend-color {{
            width: 14px;
            height: 14px;
            border-radius: 50%;
            margin-right: 8px;
        }}
        .legend-line {{
            width: 30px;
            height: 3px;
            margin-right: 8px;
        }}
        #stats {{
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #0f3460;
            font-size: 0.85rem;
        }}
        #stats p {{
            margin: 5px 0;
            color: #888;
        }}
        #stats span {{
            color: #eee;
        }}
        button {{
            background: #e94560;
            color: white;
            border: none;
            padding: 8px 14px;
            cursor: pointer;
            border-radius: 4px;
            font-size: 0.85rem;
            margin: 4px 4px 4px 0;
        }}
        button:hover {{
            background: #ff6b6b;
        }}
    </style>
</head>
<body>
    <div id="header">
        <h1>{title}</h1>
        <div id="filter-controls">
            <span style="color: #888;">Filter:</span>
            <div class="filter-group">
                <label>
                    <input type="checkbox" id="filter-runtime" checked>
                    <span class="dep-indicator dep-runtime"></span>
                    Runtime
                </label>
                <label>
                    <input type="checkbox" id="filter-build">
                    <span class="dep-indicator dep-build"></span>
                    Build
                </label>
                <label>
                    <input type="checkbox" id="filter-check">
                    <span class="dep-indicator dep-check"></span>
                    Check
                </label>
            </div>
        </div>
    </div>
    <div id="container">
        <div id="network"></div>
        <div id="sidebar">
            <h3>🔍 Search</h3>
            <input type="text" id="search-box" placeholder="Type package name...">

            <h3>📦 Package Info</h3>
            <div id="info">
                <p><em>Click on a node to see details</em></p>
            </div>

            <div id="legend">
                <h3>📊 Legend</h3>
                <p style="font-size: 0.8rem; color: #888; margin-bottom: 8px;">Node (by repo):</p>
                <div class="legend-item">
                    <div class="legend-color" style="background: #4CAF50;"></div>
                    <span>main</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #2196F3;"></div>
                    <span>community</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #FF9800;"></div>
                    <span>testing</span>
                </div>
                <p style="font-size: 0.8rem; color: #888; margin: 12px 0 8px;">Edge (by dep type):</p>
                <div class="legend-item">
                    <div class="legend-line" style="background: #4CAF50;"></div>
                    <span>Runtime (solid)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-line" style="background: repeating-linear-gradient(90deg, #2196F3 0px, #2196F3 5px, transparent 5px, transparent 10px);"></div>
                    <span>Build (dashed)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-line" style="background: repeating-linear-gradient(90deg, #FF9800 0px, #FF9800 2px, transparent 2px, transparent 4px);"></div>
                    <span>Check (dotted)</span>
                </div>
            </div>

            <div id="stats">
                <h3>📈 Statistics</h3>
                <p>Nodes: <span id="node-count">0</span></p>
                <p>Edges: <span id="edge-count">0</span></p>
                <p>Runtime: <span id="runtime-count">0</span></p>
                <p>Build: <span id="build-count">0</span></p>
                <p>Check: <span id="check-count">0</span></p>
            </div>

            <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #0f3460;">
                <button onclick="network.fit()">Fit View</button>
                <button onclick="focusCenter()">Center</button>
            </div>
        </div>
    </div>

    <script>
        // 原始数据
        const allNodes = {json.dumps(nodes, ensure_ascii=False)};
        const allEdges = {json.dumps(edges, ensure_ascii=False)};
        const centerPackage = "{package}";

        // 当前显示的数据
        const nodes = new vis.DataSet(allNodes);
        const edges = new vis.DataSet([]);

        const container = document.getElementById('network');
        const data = {{ nodes: nodes, edges: edges }};

        const options = {{
            nodes: {{
                shape: 'dot',
                font: {{
                    color: '#ffffff'
                }}
            }},
            edges: {{
                smooth: {{
                    type: 'continuous'
                }}
            }},
            physics: {{
                barnesHut: {{
                    gravitationalConstant: -3000,
                    centralGravity: 0.3,
                    springLength: 120,
                    springConstant: 0.04,
                    damping: 0.5
                }},
                stabilization: {{
                    iterations: 150
                }}
            }},
            interaction: {{
                hover: true,
                tooltipDelay: 200
            }}
        }};

        const network = new vis.Network(container, data, options);

        // 过滤器状态
        let filters = {{
            runtime: true,
            build: false,
            check: false
        }};

        // 更新显示的边
        function updateEdges() {{
            const filteredEdges = allEdges.filter(edge => {{
                if (edge.depType === 'runtime' && filters.runtime) return true;
                if (edge.depType === 'build' && filters.build) return true;
                if (edge.depType === 'check' && filters.check) return true;
                return false;
            }});

            // 找出需要显示的节点
            const connectedNodes = new Set([centerPackage]);
            filteredEdges.forEach(edge => {{
                connectedNodes.add(edge.from);
                connectedNodes.add(edge.to);
            }});

            // 更新节点可见性
            allNodes.forEach(node => {{
                const isVisible = connectedNodes.has(node.id);
                nodes.update({{
                    id: node.id,
                    hidden: !isVisible
                }});
            }});

            // 更新边
            edges.clear();
            edges.add(filteredEdges);

            // 更新统计
            updateStats(filteredEdges);
        }}

        function updateStats(filteredEdges) {{
            const visibleNodes = allNodes.filter(n => !nodes.get(n.id)?.hidden).length;
            document.getElementById('node-count').textContent = visibleNodes;
            document.getElementById('edge-count').textContent = filteredEdges.length;
            document.getElementById('runtime-count').textContent =
                filteredEdges.filter(e => e.depType === 'runtime').length;
            document.getElementById('build-count').textContent =
                filteredEdges.filter(e => e.depType === 'build').length;
            document.getElementById('check-count').textContent =
                filteredEdges.filter(e => e.depType === 'check').length;
        }}

        // 过滤器事件
        document.getElementById('filter-runtime').addEventListener('change', function() {{
            filters.runtime = this.checked;
            updateEdges();
        }});
        document.getElementById('filter-build').addEventListener('change', function() {{
            filters.build = this.checked;
            updateEdges();
        }});
        document.getElementById('filter-check').addEventListener('change', function() {{
            filters.check = this.checked;
            updateEdges();
        }});

        // 初始化显示
        updateEdges();

        // 点击节点显示信息
        network.on('click', function(params) {{
            if (params.nodes.length > 0) {{
                const nodeId = params.nodes[0];
                const node = nodes.get(nodeId);
                if (node && node.title) {{
                    document.getElementById('info').innerHTML = node.title;
                }} else {{
                    document.getElementById('info').innerHTML = `<p><strong>${{nodeId}}</strong></p>`;
                }}
            }}
        }});

        // 搜索功能
        const searchBox = document.getElementById('search-box');
        searchBox.addEventListener('input', function(e) {{
            const query = e.target.value.toLowerCase();
            if (query.length >= 2) {{
                const matchingNodes = allNodes.filter(n =>
                    n.id.toLowerCase().includes(query) && !nodes.get(n.id)?.hidden
                );
                if (matchingNodes.length > 0 && matchingNodes.length <= 10) {{
                    network.selectNodes(matchingNodes.map(n => n.id));
                    if (matchingNodes.length === 1) {{
                        network.focus(matchingNodes[0].id, {{
                            scale: 1.5,
                            animation: true
                        }});
                    }}
                }}
            }}
        }});

        searchBox.addEventListener('keydown', function(e) {{
            if (e.key === 'Enter') {{
                const query = e.target.value.toLowerCase();
                const exactMatch = allNodes.find(n => n.id.toLowerCase() === query);
                if (exactMatch && !nodes.get(exactMatch.id)?.hidden) {{
                    network.selectNodes([exactMatch.id]);
                    network.focus(exactMatch.id, {{
                        scale: 2,
                        animation: true
                    }});
                }}
            }}
        }});

        function focusCenter() {{
            network.focus(centerPackage, {{
                scale: 1.2,
                animation: true
            }});
        }}
    </script>
</body>
</html>'''

    def render_filtered_graph_html(
        self,
        output_path: str,
        title: str = "Filtered Dependency Graph",
        dep_type: DependencyType = DependencyType.RUNTIME,
        show_all_types: bool = False,
        filters: dict[str, Any] | None = None,
    ):
        """
        渲染带过滤器的依赖图

        Args:
            output_path: 输出文件路径
            title: 页面标题
            dep_type: 依赖类型
            show_all_types: 是否显示所有类型
            filters: 过滤器配置
                - root_pkg: 只显示该包的依赖子树
                - min_rdeps: 最小被依赖数
                - min_deps: 最小依赖数
                - no_orphans: 排除孤立包
                - repo: 只显示指定仓库
        """
        filters = filters or {}

        # 应用过滤器，获取要显示的节点
        nodes_to_show = self._apply_filters(filters, dep_type)

        if not nodes_to_show:
            # 如果没有节点，返回空图
            nodes_to_show = set()

        # 构建节点数据
        nodes_data = []
        rdep_counts = {}

        # 预计算被依赖数
        for pkg in nodes_to_show:
            rdep_counts[pkg] = len(
                [p for p in self.graph.get_reverse_dependencies(pkg) if p in nodes_to_show]
            )

        # 找出 root_pkg 用于高亮
        root_pkg = filters.get("root_pkg")

        for node in nodes_to_show:
            pkg_info = self.graph.packages.get(node)
            repo = pkg_info.repo if pkg_info else "unknown"
            rdep_count = rdep_counts.get(node, 0)

            # 根据节点重要性调整大小
            if node == root_pkg:
                size = 35
                font_size = 14
            elif rdep_count > 100:
                size = 30
                font_size = 12
            elif rdep_count > 20:
                size = 25
                font_size = 11
            else:
                size = max(8, min(5 + rdep_count / 5, 20))
                font_size = 9

            node_data = {
                "id": node,
                "label": node,
                "color": self.REPO_COLORS.get(repo, self.REPO_COLORS["unknown"]),
                "size": size,
                "font": {"size": font_size},
            }

            if pkg_info:
                node_data["title"] = self._make_tooltip(pkg_info)

            nodes_data.append(node_data)

        # 构建边数据
        if show_all_types:
            edges_data = self._collect_all_type_edges(nodes_to_show)
        else:
            edges_data = self._collect_single_type_edges(nodes_to_show, dep_type)

        # 生成 HTML
        html_content = self._generate_filtered_graph_html(
            nodes_data,
            edges_data,
            title,
            root_pkg=root_pkg,
            show_all_types=show_all_types,
            filters=filters,
        )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    def _apply_filters(self, filters: dict[str, Any], dep_type: DependencyType) -> set:
        """应用过滤器，返回要显示的节点集合"""
        root_pkg = filters.get("root_pkg")
        min_rdeps = filters.get("min_rdeps", 0)
        min_deps = filters.get("min_deps", 0)
        no_orphans = filters.get("no_orphans", False)
        repo_filter = filters.get("repo")

        # 如果指定了 root_pkg，只获取其依赖子树
        if root_pkg:
            nodes = self._get_subtree(root_pkg, dep_type)
        else:
            nodes = set(self.graph.packages.keys())

        # 应用仓库过滤
        if repo_filter:
            nodes = {
                pkg
                for pkg in nodes
                if self.graph.packages.get(pkg) and self.graph.packages[pkg].repo == repo_filter
            }

        # 应用被依赖数过滤
        if min_rdeps > 0:
            nodes = {
                pkg for pkg in nodes if len(self.graph.get_reverse_dependencies(pkg)) >= min_rdeps
            }

        # 应用依赖数过滤
        if min_deps > 0:
            nodes = {
                pkg
                for pkg in nodes
                if len(self.graph.get_dependencies(pkg, dep_type=dep_type)) >= min_deps
            }

        # 过滤孤立包
        if no_orphans:
            nodes = {
                pkg
                for pkg in nodes
                if (
                    len(self.graph.get_dependencies(pkg, dep_type=dep_type)) > 0
                    or len(self.graph.get_reverse_dependencies(pkg, dep_type=dep_type)) > 0
                )
            }

        return nodes

    def _get_subtree(self, root_pkg: str, dep_type: DependencyType, max_depth: int = 100) -> set:
        """获取指定包的依赖子树（包含所有向下的依赖）"""
        nodes = {root_pkg}

        def collect_deps(pkg: str, depth: int, visited: set):
            if depth > max_depth or pkg in visited:
                return
            visited.add(pkg)

            pkg_info = self.graph.packages.get(pkg)
            if not pkg_info:
                return

            # 根据类型获取依赖
            if dep_type == DependencyType.RUNTIME:
                deps = pkg_info.depends
            elif dep_type == DependencyType.BUILD:
                deps = list(pkg_info.build_depends)
            else:
                deps = list(pkg_info.all_depends)

            for dep in deps:
                if dep in self.graph.packages:
                    nodes.add(dep)
                    collect_deps(dep, depth + 1, visited.copy())

        collect_deps(root_pkg, 0, set())
        return nodes

    def _generate_filtered_graph_html(
        self,
        nodes: list[dict],
        edges: list[dict],
        title: str,
        root_pkg: str | None = None,
        show_all_types: bool = False,
        filters: dict[str, Any] | None = None,
    ) -> str:
        """生成带高级过滤器的 HTML"""
        filters = filters or {}
        filter_info = []
        if filters.get("root_pkg"):
            filter_info.append(f"Root: {filters['root_pkg']}")
        if filters.get("min_rdeps"):
            filter_info.append(f"Min rdeps: {filters['min_rdeps']}")
        if filters.get("min_deps"):
            filter_info.append(f"Min deps: {filters['min_deps']}")
        if filters.get("no_orphans"):
            filter_info.append("No orphans")
        if filters.get("repo"):
            filter_info.append(f"Repo: {filters['repo']}")

        filter_text = " | ".join(filter_info) if filter_info else "None"

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
        }}
        #header {{
            background: #16213e;
            padding: 10px 20px;
            border-bottom: 1px solid #0f3460;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }}
        #header h1 {{ font-size: 1.2rem; font-weight: 500; }}
        #filter-info {{ font-size: 0.8rem; color: #888; }}
        #filter-controls {{
            display: flex;
            gap: 12px;
            align-items: center;
        }}
        .filter-group {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .filter-group label {{
            display: flex;
            align-items: center;
            gap: 4px;
            cursor: pointer;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.85rem;
        }}
        .filter-group label:hover {{ background: rgba(255,255,255,0.1); }}
        .dep-indicator {{ display: inline-block; width: 18px; height: 3px; }}
        .dep-runtime {{ background: #4CAF50; }}
        .dep-build {{ background: repeating-linear-gradient(90deg, #2196F3 0px, #2196F3 4px, transparent 4px, transparent 8px); }}
        .dep-check {{ background: repeating-linear-gradient(90deg, #FF9800 0px, #FF9800 2px, transparent 2px, transparent 4px); }}
        #container {{ display: flex; height: calc(100vh - 55px); }}
        #network {{ flex: 1; background: #1a1a2e; }}
        #sidebar {{
            width: 280px;
            background: #16213e;
            padding: 15px;
            overflow-y: auto;
            border-left: 1px solid #0f3460;
        }}
        #sidebar h3 {{ margin-bottom: 8px; color: #e94560; font-size: 0.95rem; }}
        #search-box {{
            width: 100%;
            padding: 8px;
            margin-bottom: 12px;
            background: #1a1a2e;
            border: 1px solid #0f3460;
            color: #eee;
            border-radius: 4px;
        }}
        #search-box:focus {{ outline: none; border-color: #e94560; }}
        #info {{ font-size: 0.82rem; line-height: 1.4; }}
        .legend {{ margin-top: 12px; padding-top: 12px; border-top: 1px solid #0f3460; }}
        .legend-item {{ display: flex; align-items: center; margin: 5px 0; font-size: 0.8rem; }}
        .legend-color {{ width: 12px; height: 12px; border-radius: 50%; margin-right: 6px; }}
        .legend-line {{ width: 25px; height: 3px; margin-right: 6px; }}
        #stats {{ margin-top: 12px; padding-top: 12px; border-top: 1px solid #0f3460; font-size: 0.8rem; }}
        #stats p {{ margin: 4px 0; color: #888; }}
        #stats span {{ color: #eee; }}
        .btn-group {{ margin-top: 12px; }}
        button {{
            background: #e94560;
            color: white;
            border: none;
            padding: 6px 10px;
            cursor: pointer;
            border-radius: 4px;
            font-size: 0.8rem;
            margin: 3px;
        }}
        button:hover {{ background: #ff6b6b; }}
        button.secondary {{ background: #0f3460; }}
        button.secondary:hover {{ background: #16213e; }}
        #loading {{
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(22, 33, 62, 0.95);
            padding: 25px 40px;
            border-radius: 8px;
            text-align: center;
            z-index: 1000;
        }}
        #loading.hidden {{ display: none; }}
        .spinner {{
            border: 3px solid #0f3460;
            border-top: 3px solid #e94560;
            border-radius: 50%;
            width: 35px;
            height: 35px;
            animation: spin 1s linear infinite;
            margin: 0 auto 12px;
        }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
    </style>
</head>
<body>
    <div id="header">
        <div>
            <h1>{title}</h1>
            <div id="filter-info">Filters: {filter_text}</div>
        </div>
        <div id="filter-controls">
            <span style="color: #888; font-size: 0.85rem;">Show:</span>
            <div class="filter-group">
                <label>
                    <input type="checkbox" id="filter-runtime" checked>
                    <span class="dep-indicator dep-runtime"></span>Runtime
                </label>
                <label>
                    <input type="checkbox" id="filter-build">
                    <span class="dep-indicator dep-build"></span>Build
                </label>
                <label>
                    <input type="checkbox" id="filter-check">
                    <span class="dep-indicator dep-check"></span>Check
                </label>
            </div>
        </div>
    </div>
    <div id="container">
        <div id="network"></div>
        <div id="sidebar">
            <h3>🔍 Search</h3>
            <input type="text" id="search-box" placeholder="Type package name...">

            <h3>📦 Package Info</h3>
            <div id="info"><p><em>Click a node to see details</em></p></div>

            <div class="legend">
                <h3>Legend</h3>
                <p style="font-size: 0.75rem; color: #666; margin-bottom: 6px;">Nodes (repo):</p>
                <div class="legend-item"><div class="legend-color" style="background: #4CAF50;"></div>main</div>
                <div class="legend-item"><div class="legend-color" style="background: #2196F3;"></div>community</div>
                <div class="legend-item"><div class="legend-color" style="background: #FF9800;"></div>testing</div>
                <p style="font-size: 0.75rem; color: #666; margin: 8px 0 6px;">Edges (type):</p>
                <div class="legend-item"><div class="legend-line" style="background: #4CAF50;"></div>Runtime</div>
                <div class="legend-item"><div class="legend-line" style="background: repeating-linear-gradient(90deg, #2196F3 0px, #2196F3 4px, transparent 4px, transparent 8px);"></div>Build</div>
                <div class="legend-item"><div class="legend-line" style="background: repeating-linear-gradient(90deg, #FF9800 0px, #FF9800 2px, transparent 2px, transparent 4px);"></div>Check</div>
            </div>

            <div id="stats">
                <h3>📈 Statistics</h3>
                <p>Nodes: <span id="node-count">{len(nodes)}</span></p>
                <p>Visible edges: <span id="edge-count">0</span></p>
                <p>Runtime: <span id="runtime-count">0</span></p>
                <p>Build: <span id="build-count">0</span></p>
                <p>Check: <span id="check-count">0</span></p>
            </div>

            <div class="btn-group">
                <button onclick="network.fit()">Fit View</button>
                {"<button onclick='focusRoot()'>Go to Root</button>" if root_pkg else ""}
                <button onclick="togglePhysics()" class="secondary">Toggle Physics</button>
            </div>
        </div>
    </div>
    <div id="loading">
        <div class="spinner"></div>
        <div>Loading {len(nodes)} nodes...</div>
    </div>
    <script>
        const allNodes = {json.dumps(nodes, ensure_ascii=False)};
        const allEdges = {json.dumps(edges, ensure_ascii=False)};
        const rootPkg = {"'" + root_pkg + "'" if root_pkg else "null"};

        const nodes = new vis.DataSet(allNodes);
        const edges = new vis.DataSet([]);

        const container = document.getElementById('network');
        const data = {{ nodes: nodes, edges: edges }};

        const options = {{
            nodes: {{
                shape: 'dot',
                font: {{ color: '#fff' }}
            }},
            edges: {{
                smooth: {{ type: 'continuous', roundness: 0.2 }}
            }},
            physics: {{
                barnesHut: {{
                    gravitationalConstant: -3000,
                    centralGravity: 0.2,
                    springLength: 120,
                    springConstant: 0.04,
                    damping: 0.4
                }},
                stabilization: {{
                    iterations: Math.min(200, allNodes.length),
                    updateInterval: 25
                }}
            }},
            interaction: {{
                hover: true,
                tooltipDelay: 200,
                hideEdgesOnDrag: allNodes.length > 500,
                hideEdgesOnZoom: allNodes.length > 500
            }}
        }};

        const network = new vis.Network(container, data, options);
        let physicsEnabled = true;

        network.on('stabilizationIterationsDone', () => {{
            document.getElementById('loading').classList.add('hidden');
            network.setOptions({{ physics: {{ stabilization: false }} }});
            if (rootPkg) {{
                network.focus(rootPkg, {{ scale: 1.2, animation: {{ duration: 500 }} }});
                network.selectNodes([rootPkg]);
            }}
        }});

        let filters = {{ runtime: true, build: false, check: false }};

        function updateEdges() {{
            const filtered = allEdges.filter(e => filters[e.depType]);
            edges.clear();
            edges.add(filtered);

            document.getElementById('edge-count').textContent = filtered.length;
            document.getElementById('runtime-count').textContent = filtered.filter(e => e.depType === 'runtime').length;
            document.getElementById('build-count').textContent = filtered.filter(e => e.depType === 'build').length;
            document.getElementById('check-count').textContent = filtered.filter(e => e.depType === 'check').length;
        }}

        document.getElementById('filter-runtime').addEventListener('change', function() {{ filters.runtime = this.checked; updateEdges(); }});
        document.getElementById('filter-build').addEventListener('change', function() {{ filters.build = this.checked; updateEdges(); }});
        document.getElementById('filter-check').addEventListener('change', function() {{ filters.check = this.checked; updateEdges(); }});

        updateEdges();

        network.on('click', params => {{
            if (params.nodes.length > 0) {{
                const node = nodes.get(params.nodes[0]);
                document.getElementById('info').innerHTML = node?.title || `<p><strong>${{params.nodes[0]}}</strong></p>`;
            }}
        }});

        const searchBox = document.getElementById('search-box');
        searchBox.addEventListener('input', e => {{
            const q = e.target.value.toLowerCase();
            if (q.length >= 2) {{
                const matches = allNodes.filter(n => n.id.toLowerCase().includes(q)).slice(0, 10);
                if (matches.length > 0) {{
                    network.selectNodes(matches.map(n => n.id));
                    if (matches.length === 1) network.focus(matches[0].id, {{ scale: 1.5, animation: true }});
                }}
            }}
        }});

        searchBox.addEventListener('keydown', e => {{
            if (e.key === 'Enter') {{
                const match = allNodes.find(n => n.id.toLowerCase() === e.target.value.toLowerCase());
                if (match) {{
                    network.selectNodes([match.id]);
                    network.focus(match.id, {{ scale: 2, animation: true }});
                    document.getElementById('info').innerHTML = match.title || `<p><strong>${{match.id}}</strong></p>`;
                }}
            }}
        }});

        function focusRoot() {{
            if (rootPkg) {{
                network.focus(rootPkg, {{ scale: 1.5, animation: true }});
                network.selectNodes([rootPkg]);
            }}
        }}

        function togglePhysics() {{
            physicsEnabled = !physicsEnabled;
            network.setOptions({{ physics: {{ enabled: physicsEnabled }} }});
        }}
    </script>
</body>
</html>"""

    def render_d3_html(
        self,
        package: str,
        output_path: str,
        dep_type: DependencyType = DependencyType.ALL,
        max_depth: int = 3,
        title: str | None = None,
    ):
        """
        使用 D3.js 渲染为交互式 HTML 文件（力导向图）
        """
        # 收集节点
        nodes_to_show = {package}
        deps = self.graph.get_dependencies(
            package, dep_type=dep_type, recursive=True, max_depth=max_depth
        )
        nodes_to_show.update(deps)

        # 构建数据
        nodes = []
        links = []

        for _i, node in enumerate(nodes_to_show):
            pkg_info = self.graph.packages.get(node)
            repo = pkg_info.repo if pkg_info else "unknown"

            nodes.append(
                {
                    "id": node,
                    "group": repo,
                    "isCenter": node == package,
                }
            )

        for node in nodes_to_show:
            for dep in self.graph.get_dependencies(node, dep_type=dep_type):
                if dep in nodes_to_show:
                    links.append(
                        {
                            "source": node,
                            "target": dep,
                        }
                    )

        # 生成 HTML
        html_content = self._generate_d3_html(
            nodes, links, title=title or f"Dependency Graph: {package}"
        )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    def render_tree_html(
        self,
        package: str,
        output_path: str,
        dep_type: DependencyType = DependencyType.ALL,
        max_depth: int = 4,
        title: str | None = None,
    ):
        """
        渲染为树形结构 HTML
        """
        tree_data = self.graph.get_dependency_tree(package, dep_type, max_depth)

        html_content = self._generate_tree_html(
            tree_data, title=title or f"Dependency Tree: {package}"
        )

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    def _make_tooltip(self, pkg: Any) -> str:
        """生成节点提示信息"""
        lines = [
            f"<b>{pkg.name}</b>",
            f"Version: {pkg.version}-r{pkg.release}",
            f"Repo: {pkg.repo}",
        ]

        if pkg.description:
            lines.append(f"<br>{pkg.description[:100]}...")

        if pkg.depends:
            lines.append(f"<br>Dependencies: {len(pkg.depends)}")

        return "<br>".join(lines)

    def _generate_visjs_html(self, nodes: list[dict], edges: list[dict], title: str) -> str:
        """生成 vis.js HTML 内容"""
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #1a1a2e;
            color: #eee;
        }}
        #header {{
            background: #16213e;
            padding: 15px 20px;
            border-bottom: 1px solid #0f3460;
        }}
        #header h1 {{
            font-size: 1.5rem;
            font-weight: 500;
        }}
        #container {{
            display: flex;
            height: calc(100vh - 60px);
        }}
        #network {{
            flex: 1;
            background: #1a1a2e;
        }}
        #sidebar {{
            width: 300px;
            background: #16213e;
            padding: 20px;
            overflow-y: auto;
            border-left: 1px solid #0f3460;
        }}
        #sidebar h3 {{
            margin-bottom: 15px;
            color: #e94560;
        }}
        #info {{
            font-size: 0.9rem;
            line-height: 1.6;
        }}
        #info p {{
            margin: 8px 0;
        }}
        #info .label {{
            color: #888;
        }}
        #legend {{
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #0f3460;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            margin: 8px 0;
        }}
        .legend-color {{
            width: 16px;
            height: 16px;
            border-radius: 50%;
            margin-right: 10px;
        }}
        #controls {{
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #0f3460;
        }}
        button {{
            background: #e94560;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            margin: 5px 5px 5px 0;
        }}
        button:hover {{
            background: #ff6b6b;
        }}
    </style>
</head>
<body>
    <div id="header">
        <h1>{title}</h1>
    </div>
    <div id="container">
        <div id="network"></div>
        <div id="sidebar">
            <h3>Package Info</h3>
            <div id="info">
                <p>Click a node to see details</p>
            </div>
            <div id="legend">
                <h3>Legend</h3>
                <div class="legend-item">
                    <div class="legend-color" style="background: #4CAF50"></div>
                    <span>main</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #2196F3"></div>
                    <span>community</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #FF9800"></div>
                    <span>testing</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #9E9E9E"></div>
                    <span>unmaintained</span>
                </div>
            </div>
            <div id="controls">
                <h3>Controls</h3>
                <button onclick="network.fit()">Fit View</button>
                <button onclick="togglePhysics()">Toggle Physics</button>
            </div>
        </div>
    </div>

    <script>
        const nodes = new vis.DataSet({json.dumps(nodes)});
        const edges = new vis.DataSet({json.dumps(edges)});

        const container = document.getElementById('network');
        const data = {{ nodes: nodes, edges: edges }};

        const options = {{
            nodes: {{
                shape: 'dot',
                borderWidth: 2,
                shadow: true,
                font: {{
                    color: '#ffffff'
                }}
            }},
            edges: {{
                width: 1,
                smooth: {{
                    type: 'continuous'
                }}
            }},
            physics: {{
                enabled: true,
                barnesHut: {{
                    gravitationalConstant: -8000,
                    centralGravity: 0.3,
                    springLength: 95,
                    springConstant: 0.04,
                    damping: 0.09
                }}
            }},
            interaction: {{
                hover: true,
                tooltipDelay: 200
            }}
        }};

        const network = new vis.Network(container, data, options);
        let physicsEnabled = true;

        function togglePhysics() {{
            physicsEnabled = !physicsEnabled;
            network.setOptions({{ physics: {{ enabled: physicsEnabled }} }});
        }}

        network.on('click', function(params) {{
            if (params.nodes.length > 0) {{
                const nodeId = params.nodes[0];
                const node = nodes.get(nodeId);

                let html = '<p><span class="label">Name:</span> ' + nodeId + '</p>';
                if (node.title) {{
                    html += '<p>' + node.title + '</p>';
                }}

                document.getElementById('info').innerHTML = html;
            }}
        }});
    </script>
</body>
</html>"""

    def _generate_d3_html(self, nodes: list[dict], links: list[dict], title: str) -> str:
        """生成 D3.js HTML 内容"""
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #1a1a2e;
            overflow: hidden;
        }}
        #header {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: rgba(22, 33, 62, 0.95);
            padding: 15px 20px;
            z-index: 100;
            border-bottom: 1px solid #0f3460;
        }}
        #header h1 {{
            color: #fff;
            font-size: 1.5rem;
            font-weight: 500;
        }}
        svg {{
            width: 100vw;
            height: 100vh;
        }}
        .node {{
            cursor: pointer;
        }}
        .node circle {{
            stroke: #fff;
            stroke-width: 2px;
        }}
        .node text {{
            fill: #fff;
            font-size: 10px;
            pointer-events: none;
        }}
        .link {{
            stroke: #555;
            stroke-opacity: 0.6;
            fill: none;
        }}
        .tooltip {{
            position: absolute;
            background: rgba(0, 0, 0, 0.8);
            color: #fff;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 12px;
            pointer-events: none;
            z-index: 1000;
        }}
    </style>
</head>
<body>
    <div id="header">
        <h1>{title}</h1>
    </div>
    <div id="tooltip" class="tooltip" style="display: none;"></div>

    <script>
        const data = {{
            nodes: {json.dumps(nodes)},
            links: {json.dumps(links)}
        }};

        const colors = {{
            'main': '#4CAF50',
            'community': '#2196F3',
            'testing': '#FF9800',
            'unmaintained': '#9E9E9E',
            'unknown': '#E0E0E0'
        }};

        const width = window.innerWidth;
        const height = window.innerHeight;

        const svg = d3.select('body')
            .append('svg')
            .attr('viewBox', [0, 0, width, height]);

        // 添加箭头标记
        svg.append('defs').append('marker')
            .attr('id', 'arrowhead')
            .attr('viewBox', '-0 -5 10 10')
            .attr('refX', 20)
            .attr('refY', 0)
            .attr('orient', 'auto')
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .append('path')
            .attr('d', 'M 0,-5 L 10,0 L 0,5')
            .attr('fill', '#555');

        const simulation = d3.forceSimulation(data.nodes)
            .force('link', d3.forceLink(data.links).id(d => d.id).distance(80))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(30));

        const link = svg.append('g')
            .selectAll('line')
            .data(data.links)
            .join('line')
            .attr('class', 'link')
            .attr('marker-end', 'url(#arrowhead)');

        const node = svg.append('g')
            .selectAll('g')
            .data(data.nodes)
            .join('g')
            .attr('class', 'node')
            .call(d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended));

        node.append('circle')
            .attr('r', d => d.isCenter ? 15 : 10)
            .attr('fill', d => colors[d.group] || colors.unknown);

        node.append('text')
            .attr('dx', 15)
            .attr('dy', 4)
            .text(d => d.id);

        const tooltip = d3.select('#tooltip');

        node.on('mouseover', (event, d) => {{
            tooltip.style('display', 'block')
                .html(d.id + '<br>Repo: ' + d.group)
                .style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY - 10) + 'px');
        }})
        .on('mouseout', () => {{
            tooltip.style('display', 'none');
        }});

        simulation.on('tick', () => {{
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            node.attr('transform', d => `translate(${{d.x}},${{d.y}})`);
        }});

        function dragstarted(event) {{
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
        }}

        function dragged(event) {{
            event.subject.fx = event.x;
            event.subject.fy = event.y;
        }}

        function dragended(event) {{
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
        }}

        // 缩放
        const zoom = d3.zoom()
            .scaleExtent([0.1, 10])
            .on('zoom', (event) => {{
                svg.selectAll('g').attr('transform', event.transform);
            }});

        svg.call(zoom);
    </script>
</body>
</html>"""

    def _generate_tree_html(self, tree_data: dict, title: str) -> str:
        """生成树形结构 HTML 内容"""
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #1a1a2e;
            color: #fff;
            padding: 20px;
        }}
        h1 {{
            margin-bottom: 20px;
            font-weight: 500;
        }}
        #tree {{
            overflow: auto;
        }}
        .node circle {{
            fill: #4CAF50;
            stroke: #fff;
            stroke-width: 2px;
        }}
        .node.truncated circle {{
            fill: #FF9800;
        }}
        .node text {{
            font-size: 12px;
            fill: #fff;
        }}
        .link {{
            fill: none;
            stroke: #555;
            stroke-width: 1.5px;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div id="tree"></div>

    <script>
        const treeData = {json.dumps(tree_data)};

        const width = window.innerWidth - 40;
        const margin = {{ top: 20, right: 120, bottom: 20, left: 120 }};

        const root = d3.hierarchy(treeData);
        const treeHeight = Math.max(500, root.descendants().length * 25);

        const treeLayout = d3.tree()
            .size([treeHeight, width - margin.left - margin.right]);

        treeLayout(root);

        const svg = d3.select('#tree')
            .append('svg')
            .attr('width', width)
            .attr('height', treeHeight + margin.top + margin.bottom);

        const g = svg.append('g')
            .attr('transform', `translate(${{margin.left}},${{margin.top}})`);

        // 连接线
        g.selectAll('.link')
            .data(root.links())
            .join('path')
            .attr('class', 'link')
            .attr('d', d3.linkHorizontal()
                .x(d => d.y)
                .y(d => d.x));

        // 节点
        const node = g.selectAll('.node')
            .data(root.descendants())
            .join('g')
            .attr('class', d => 'node' + (d.data.truncated ? ' truncated' : ''))
            .attr('transform', d => `translate(${{d.y}},${{d.x}})`);

        node.append('circle')
            .attr('r', 6);

        node.append('text')
            .attr('dx', d => d.children ? -10 : 10)
            .attr('dy', 4)
            .attr('text-anchor', d => d.children ? 'end' : 'start')
            .text(d => d.data.name);
    </script>
</body>
</html>"""

    def render_full_graph_html(
        self,
        output_path: str,
        max_nodes: int = 500,
        title: str = "Full Dependency Graph",
        dep_type: DependencyType = DependencyType.RUNTIME,
        show_all_types: bool = False,
    ):
        """
        渲染完整的依赖图（带性能优化）
        """
        # 选择最重要的节点（被依赖最多的）
        most_depended = self.graph.get_most_depended(max_nodes)
        nodes_to_show = {pkg for pkg, _ in most_depended}

        nodes_data = []
        edges_data = []

        for node in nodes_to_show:
            pkg_info = self.graph.packages.get(node)
            repo = pkg_info.repo if pkg_info else "unknown"

            # 计算被依赖数作为节点大小
            rdep_count = len(self.graph.get_reverse_dependencies(node))

            node_data = {
                "id": node,
                "label": node,
                "color": self.REPO_COLORS.get(repo, self.REPO_COLORS["unknown"]),
                "size": min(10 + rdep_count / 5, 50),
                "font": {"size": 10},
            }

            if pkg_info:
                node_data["title"] = self._make_tooltip(pkg_info)

            nodes_data.append(node_data)

        # 添加边（根据依赖类型）
        if show_all_types:
            edges_data = self._collect_all_type_edges(nodes_to_show)
        else:
            edges_data = self._collect_single_type_edges(nodes_to_show, dep_type)

        if show_all_types:
            html_content = self._generate_filterable_overview_html(nodes_data, edges_data, title)
        else:
            html_content = self._generate_visjs_html(nodes_data, edges_data, title)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    def render_complete_graph_html(
        self,
        output_path: str,
        title: str = "Complete Dependency Graph",
        dep_type: DependencyType = DependencyType.RUNTIME,
        show_all_types: bool = False,
    ):
        """
        渲染包含所有节点的完整依赖图

        使用优化的渲染方式以支持大规模图谱显示。
        """
        all_packages = list(self.graph.packages.keys())
        nodes_to_show = set(all_packages)

        # 收集节点数据
        nodes_data = []

        # 为了性能，预计算每个包的反向依赖数量
        rdep_counts = {}
        for pkg in all_packages:
            rdep_counts[pkg] = len(self.graph.get_reverse_dependencies(pkg))

        # 添加所有节点
        for node in all_packages:
            pkg_info = self.graph.packages.get(node)
            repo = pkg_info.repo if pkg_info else "unknown"
            rdep_count = rdep_counts.get(node, 0)

            node_data = {
                "id": node,
                "label": node,
                "color": self.REPO_COLORS.get(repo, self.REPO_COLORS["unknown"]),
                "size": min(5 + rdep_count / 10, 40),
                "font": {"size": 8},
            }

            if pkg_info:
                node_data["title"] = self._make_tooltip(pkg_info)

            nodes_data.append(node_data)

        # 添加边（根据依赖类型）
        if show_all_types:
            edges_data = self._collect_all_type_edges(nodes_to_show)
        else:
            edges_data = self._collect_single_type_edges(nodes_to_show, dep_type)

        # 使用优化的 HTML 模板
        if show_all_types:
            html_content = self._generate_filterable_overview_html(nodes_data, edges_data, title)
        else:
            html_content = self._generate_large_graph_html(nodes_data, edges_data, title)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    def _collect_single_type_edges(
        self, nodes_to_show: set, dep_type: DependencyType
    ) -> list[dict]:
        """收集单一类型的边"""
        edges_data = []

        # 确定边的样式
        if dep_type == DependencyType.RUNTIME:
            style = self.EDGE_STYLES["runtime"]
            edge_type = "runtime"
        elif dep_type == DependencyType.BUILD:
            style = self.EDGE_STYLES["build"]
            edge_type = "build"
        else:
            style = {"color": "#444444", "dashes": False, "width": 1}
            edge_type = "all"

        for node in nodes_to_show:
            pkg_info = self.graph.packages.get(node)
            if not pkg_info:
                continue

            if dep_type == DependencyType.RUNTIME:
                deps = pkg_info.depends
            elif dep_type == DependencyType.BUILD:
                deps = list(pkg_info.build_depends)
            else:
                deps = list(pkg_info.all_depends)

            for dep in deps:
                if dep in nodes_to_show:
                    edges_data.append(
                        {
                            "from": node,
                            "to": dep,
                            "arrows": "to",
                            "color": {"color": style["color"], "opacity": 0.5},
                            "dashes": style["dashes"],
                            "width": style["width"],
                            "depType": edge_type,
                        }
                    )

        return edges_data

    def _collect_all_type_edges(self, nodes_to_show: set) -> list[dict]:
        """收集所有类型的边"""
        edges_data = []
        edge_set = set()

        for node in nodes_to_show:
            pkg_info = self.graph.packages.get(node)
            if not pkg_info:
                continue

            # 运行时依赖
            for dep in pkg_info.depends:
                if dep in nodes_to_show:
                    edge_key = (node, dep, "runtime")
                    if edge_key not in edge_set:
                        edge_set.add(edge_key)
                        style = self.EDGE_STYLES["runtime"]
                        edges_data.append(
                            {
                                "from": node,
                                "to": dep,
                                "arrows": "to",
                                "color": {"color": style["color"], "opacity": 0.6},
                                "dashes": style["dashes"],
                                "width": style["width"],
                                "depType": "runtime",
                            }
                        )

            # 构建依赖
            for dep in pkg_info.build_depends:
                if dep in nodes_to_show:
                    edge_key = (node, dep, "build")
                    if edge_key not in edge_set:
                        edge_set.add(edge_key)
                        style = self.EDGE_STYLES["build"]
                        edges_data.append(
                            {
                                "from": node,
                                "to": dep,
                                "arrows": "to",
                                "color": {"color": style["color"], "opacity": 0.4},
                                "dashes": style["dashes"],
                                "width": style["width"],
                                "depType": "build",
                            }
                        )

            # 检查依赖
            for dep in pkg_info.checkdepends:
                if dep in nodes_to_show:
                    edge_key = (node, dep, "check")
                    if edge_key not in edge_set:
                        edge_set.add(edge_key)
                        style = self.EDGE_STYLES["check"]
                        edges_data.append(
                            {
                                "from": node,
                                "to": dep,
                                "arrows": "to",
                                "color": {"color": style["color"], "opacity": 0.3},
                                "dashes": style["dashes"],
                                "width": style["width"],
                                "depType": "check",
                            }
                        )

        return edges_data

    def _generate_filterable_overview_html(
        self, nodes: list[dict], edges: list[dict], title: str
    ) -> str:
        """生成带高级过滤器的大规模图 HTML"""
        # 预计算每个节点的依赖数和被依赖数，用于客户端过滤
        node_stats = {}
        for node in nodes:
            pkg_id = node["id"]
            pkg_info = self.graph.packages.get(pkg_id)
            repo = pkg_info.repo if pkg_info else "unknown"
            deps_count = len(self.graph.get_dependencies(pkg_id)) if pkg_info else 0
            rdeps_count = len(self.graph.get_reverse_dependencies(pkg_id)) if pkg_info else 0
            node_stats[pkg_id] = {"repo": repo, "deps": deps_count, "rdeps": rdeps_count}

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
        }}
        #header {{
            background: #16213e;
            padding: 8px 15px;
            border-bottom: 1px solid #0f3460;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
        }}
        #header h1 {{ font-size: 1.1rem; font-weight: 500; }}
        #filter-controls {{
            display: flex;
            gap: 12px;
            align-items: center;
            flex-wrap: wrap;
        }}
        .filter-group {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .filter-group label {{
            display: flex;
            align-items: center;
            gap: 4px;
            cursor: pointer;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
        }}
        .filter-group label:hover {{ background: rgba(255,255,255,0.1); }}
        .dep-indicator {{ display: inline-block; width: 18px; height: 3px; }}
        .dep-runtime {{ background: #4CAF50; }}
        .dep-build {{ background: repeating-linear-gradient(90deg, #2196F3 0px, #2196F3 4px, transparent 4px, transparent 8px); }}
        .dep-check {{ background: repeating-linear-gradient(90deg, #FF9800 0px, #FF9800 2px, transparent 2px, transparent 4px); }}
        #container {{ display: flex; height: calc(100vh - 48px); }}
        #network {{ flex: 1; background: #1a1a2e; }}
        #sidebar {{
            width: 300px;
            background: #16213e;
            padding: 12px;
            overflow-y: auto;
            border-left: 1px solid #0f3460;
        }}
        #sidebar h3 {{ margin: 10px 0 8px; color: #e94560; font-size: 0.9rem; }}
        #sidebar h3:first-child {{ margin-top: 0; }}
        .input-row {{
            display: flex;
            gap: 8px;
            margin-bottom: 8px;
        }}
        .input-group {{
            flex: 1;
        }}
        .input-group label {{
            display: block;
            font-size: 0.75rem;
            color: #888;
            margin-bottom: 3px;
        }}
        .input-group input, .input-group select {{
            width: 100%;
            padding: 6px 8px;
            background: #1a1a2e;
            border: 1px solid #0f3460;
            color: #eee;
            border-radius: 4px;
            font-size: 0.8rem;
        }}
        .input-group input:focus, .input-group select:focus {{ outline: none; border-color: #e94560; }}
        .input-group input[type="number"] {{ width: 100%; }}
        #search-box {{
            width: 100%;
            padding: 8px;
            margin-bottom: 8px;
            background: #1a1a2e;
            border: 1px solid #0f3460;
            color: #eee;
            border-radius: 4px;
        }}
        #search-box:focus {{ outline: none; border-color: #e94560; }}
        #info {{ font-size: 0.78rem; line-height: 1.4; max-height: 200px; overflow-y: auto; }}
        #stats {{ margin-top: 12px; padding-top: 12px; border-top: 1px solid #0f3460; font-size: 0.78rem; }}
        #stats p {{ margin: 3px 0; color: #888; }}
        #stats span {{ color: #eee; }}
        .legend {{ margin-top: 10px; padding-top: 10px; border-top: 1px solid #0f3460; }}
        .legend-item {{ display: flex; align-items: center; margin: 4px 0; font-size: 0.75rem; }}
        .legend-color {{ width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; }}
        button {{
            background: #e94560;
            color: white;
            border: none;
            padding: 5px 10px;
            cursor: pointer;
            border-radius: 4px;
            font-size: 0.75rem;
            margin: 2px;
        }}
        button:hover {{ background: #ff6b6b; }}
        button.secondary {{ background: #0f3460; }}
        button.secondary:hover {{ background: #1a1a2e; }}
        #loading {{
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(22, 33, 62, 0.95);
            padding: 25px 40px;
            border-radius: 8px;
            text-align: center;
            z-index: 1000;
        }}
        #loading.hidden {{ display: none; }}
        .spinner {{
            border: 3px solid #0f3460;
            border-top: 3px solid #e94560;
            border-radius: 50%;
            width: 35px;
            height: 35px;
            animation: spin 1s linear infinite;
            margin: 0 auto 12px;
        }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
        .checkbox-row {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin: 8px 0;
            font-size: 0.8rem;
        }}
        .checkbox-row label {{
            display: flex;
            align-items: center;
            gap: 5px;
            cursor: pointer;
        }}
        #filter-status {{
            font-size: 0.75rem;
            color: #4CAF50;
            margin-top: 8px;
            padding: 6px;
            background: rgba(76, 175, 80, 0.1);
            border-radius: 4px;
            display: none;
        }}
        #filter-status.active {{ display: block; }}
    </style>
</head>
<body>
    <div id="header">
        <h1>{title}</h1>
        <div id="filter-controls">
            <span style="color: #888; font-size: 0.8rem;">Edges:</span>
            <div class="filter-group">
                <label><input type="checkbox" id="filter-runtime" checked><span class="dep-indicator dep-runtime"></span>Runtime</label>
                <label><input type="checkbox" id="filter-build"><span class="dep-indicator dep-build"></span>Build</label>
                <label><input type="checkbox" id="filter-check"><span class="dep-indicator dep-check"></span>Check</label>
            </div>
        </div>
    </div>
    <div id="container">
        <div id="network"></div>
        <div id="sidebar">
            <h3>🔍 Search & Focus</h3>
            <input type="text" id="search-box" placeholder="Search package... (Enter to focus)">

            <h3>🎯 Node Filters</h3>
            <div class="input-row">
                <div class="input-group">
                    <label>Root Package (subtree)</label>
                    <input type="text" id="filter-root" placeholder="e.g. gcc">
                </div>
            </div>
            <div class="input-row">
                <div class="input-group">
                    <label>Min Reverse Deps</label>
                    <input type="number" id="filter-min-rdeps" value="0" min="0">
                </div>
                <div class="input-group">
                    <label>Min Dependencies</label>
                    <input type="number" id="filter-min-deps" value="0" min="0">
                </div>
            </div>
            <div class="input-row">
                <div class="input-group">
                    <label>Repository</label>
                    <select id="filter-repo">
                        <option value="">All</option>
                        <option value="main" selected>main</option>
                        <option value="community">community</option>
                        <option value="testing">testing</option>
                    </select>
                </div>
            </div>
            <div class="checkbox-row">
                <label><input type="checkbox" id="filter-no-orphans"> Hide orphans (no deps & no rdeps)</label>
            </div>
            <div style="margin-top: 10px;">
                <button onclick="applyNodeFilters()">Apply Filters</button>
                <button onclick="resetFilters()" class="secondary">Reset</button>
            </div>
            <div id="filter-status"></div>

            <h3>📦 Package Info</h3>
            <div id="info"><p><em>Click a node to see details</em></p></div>

            <div id="stats">
                <h3>📈 Statistics</h3>
                <p>Total nodes: <span id="total-nodes">{len(nodes)}</span></p>
                <p>Visible nodes: <span id="visible-nodes">{len(nodes)}</span></p>
                <p>Visible edges: <span id="edge-count">0</span></p>
                <p style="margin-top: 6px;">Runtime: <span id="runtime-count">0</span></p>
                <p>Build: <span id="build-count">0</span></p>
                <p>Check: <span id="check-count">0</span></p>
            </div>

            <div class="legend">
                <p style="font-size: 0.7rem; color: #666; margin-bottom: 4px;">Nodes by repo:</p>
                <div class="legend-item"><div class="legend-color" style="background: #4CAF50;"></div>main</div>
                <div class="legend-item"><div class="legend-color" style="background: #2196F3;"></div>community</div>
                <div class="legend-item"><div class="legend-color" style="background: #FF9800;"></div>testing</div>
            </div>

            <div style="margin-top: 12px;">
                <button onclick="network.fit()">Fit View</button>
                <button onclick="togglePhysics()" class="secondary">Toggle Physics</button>
            </div>
        </div>
    </div>
    <div id="loading">
        <div class="spinner"></div>
        <div>Loading {len(nodes)} packages...</div>
    </div>
    <script>
        const allNodes = {json.dumps(nodes, ensure_ascii=False)};
        const allEdges = {json.dumps(edges, ensure_ascii=False)};
        const nodeStats = {json.dumps(node_stats, ensure_ascii=False)};

        // 构建依赖关系索引
        const depsIndex = {{}};  // pkg -> [deps]
        const rdepsIndex = {{}}; // pkg -> [rdeps]
        allEdges.forEach(e => {{
            if (!depsIndex[e.from]) depsIndex[e.from] = [];
            if (!rdepsIndex[e.to]) rdepsIndex[e.to] = [];
            depsIndex[e.from].push(e.to);
            rdepsIndex[e.to].push(e.from);
        }});

        let visibleNodeIds = new Set(allNodes.map(n => n.id));
        const nodes = new vis.DataSet(allNodes);
        const edges = new vis.DataSet([]);

        const container = document.getElementById('network');
        const data = {{ nodes: nodes, edges: edges }};

        const options = {{
            nodes: {{ shape: 'dot', font: {{ size: 8, color: '#fff' }} }},
            edges: {{ smooth: false }},
            physics: {{
                barnesHut: {{
                    gravitationalConstant: -2000,
                    centralGravity: 0.1,
                    springLength: 150,
                    springConstant: 0.01,
                    damping: 0.5
                }},
                stabilization: {{ iterations: 150, updateInterval: 25 }}
            }},
            interaction: {{
                hover: true,
                hideEdgesOnDrag: true,
                hideEdgesOnZoom: true
            }},
            layout: {{ improvedLayout: false }}
        }};

        const network = new vis.Network(container, data, options);
        let physicsEnabled = true;

        network.on('stabilizationIterationsDone', () => {{
            document.getElementById('loading').classList.add('hidden');
            network.setOptions({{ physics: {{ stabilization: false }} }});
        }});

        let edgeFilters = {{ runtime: true, build: false, check: false }};

        // 页面加载时自动应用默认过滤器（main 仓库）
        setTimeout(() => applyNodeFilters(), 100);

        function getSubtree(rootPkg) {{
            // BFS 获取所有依赖子树
            const visited = new Set([rootPkg]);
            const queue = [rootPkg];
            while (queue.length > 0) {{
                const pkg = queue.shift();
                const deps = depsIndex[pkg] || [];
                deps.forEach(dep => {{
                    if (!visited.has(dep)) {{
                        visited.add(dep);
                        queue.push(dep);
                    }}
                }});
            }}
            return visited;
        }}

        function applyNodeFilters() {{
            const rootPkg = document.getElementById('filter-root').value.trim();
            const minRdeps = parseInt(document.getElementById('filter-min-rdeps').value) || 0;
            const minDeps = parseInt(document.getElementById('filter-min-deps').value) || 0;
            const repoFilter = document.getElementById('filter-repo').value;
            const noOrphans = document.getElementById('filter-no-orphans').checked;

            let filteredNodes = new Set(allNodes.map(n => n.id));

            // 应用 root 包过滤 (子树)
            if (rootPkg && nodeStats[rootPkg]) {{
                filteredNodes = getSubtree(rootPkg);
            }} else if (rootPkg && !nodeStats[rootPkg]) {{
                alert('Package "' + rootPkg + '" not found');
                return;
            }}

            // 应用仓库过滤
            if (repoFilter) {{
                filteredNodes = new Set([...filteredNodes].filter(id => nodeStats[id]?.repo === repoFilter));
            }}

            // 应用最小被依赖数过滤
            if (minRdeps > 0) {{
                filteredNodes = new Set([...filteredNodes].filter(id => nodeStats[id]?.rdeps >= minRdeps));
            }}

            // 应用最小依赖数过滤
            if (minDeps > 0) {{
                filteredNodes = new Set([...filteredNodes].filter(id => nodeStats[id]?.deps >= minDeps));
            }}

            // 过滤孤立节点
            if (noOrphans) {{
                filteredNodes = new Set([...filteredNodes].filter(id =>
                    nodeStats[id]?.deps > 0 || nodeStats[id]?.rdeps > 0
                ));
            }}

            visibleNodeIds = filteredNodes;

            // 更新节点显示
            allNodes.forEach(n => {{
                nodes.update({{ id: n.id, hidden: !filteredNodes.has(n.id) }});
            }});

            updateEdges();

            // 显示过滤状态
            const status = document.getElementById('filter-status');
            const filterInfo = [];
            if (rootPkg) filterInfo.push(`Root: ${{rootPkg}}`);
            if (minRdeps > 0) filterInfo.push(`Min rdeps: ${{minRdeps}}`);
            if (minDeps > 0) filterInfo.push(`Min deps: ${{minDeps}}`);
            if (repoFilter) filterInfo.push(`Repo: ${{repoFilter}}`);
            if (noOrphans) filterInfo.push('No orphans');

            if (filterInfo.length > 0) {{
                status.textContent = `✓ ${{filteredNodes.size}} nodes | ${{filterInfo.join(', ')}}`;
                status.classList.add('active');
            }} else {{
                status.classList.remove('active');
            }}

            document.getElementById('visible-nodes').textContent = filteredNodes.size;

            // 如果指定了 root，自动聚焦
            if (rootPkg && nodeStats[rootPkg]) {{
                setTimeout(() => {{
                    network.focus(rootPkg, {{ scale: 1.2, animation: true }});
                    network.selectNodes([rootPkg]);
                }}, 100);
            }} else {{
                setTimeout(() => network.fit(), 100);
            }}
        }}

        function resetFilters() {{
            document.getElementById('filter-root').value = '';
            document.getElementById('filter-min-rdeps').value = '0';
            document.getElementById('filter-min-deps').value = '0';
            document.getElementById('filter-repo').value = '';
            document.getElementById('filter-no-orphans').checked = false;

            visibleNodeIds = new Set(allNodes.map(n => n.id));
            allNodes.forEach(n => {{
                nodes.update({{ id: n.id, hidden: false }});
            }});

            document.getElementById('filter-status').classList.remove('active');
            document.getElementById('visible-nodes').textContent = allNodes.length;

            updateEdges();
            network.fit();
        }}

        function updateEdges() {{
            const filteredEdges = allEdges.filter(e =>
                edgeFilters[e.depType] &&
                visibleNodeIds.has(e.from) &&
                visibleNodeIds.has(e.to)
            );
            edges.clear();
            edges.add(filteredEdges);

            document.getElementById('edge-count').textContent = filteredEdges.length;
            document.getElementById('runtime-count').textContent = filteredEdges.filter(e => e.depType === 'runtime').length;
            document.getElementById('build-count').textContent = filteredEdges.filter(e => e.depType === 'build').length;
            document.getElementById('check-count').textContent = filteredEdges.filter(e => e.depType === 'check').length;
        }}

        document.getElementById('filter-runtime').addEventListener('change', function() {{ edgeFilters.runtime = this.checked; updateEdges(); }});
        document.getElementById('filter-build').addEventListener('change', function() {{ edgeFilters.build = this.checked; updateEdges(); }});
        document.getElementById('filter-check').addEventListener('change', function() {{ edgeFilters.check = this.checked; updateEdges(); }});

        updateEdges();

        network.on('click', params => {{
            if (params.nodes.length > 0) {{
                const nodeId = params.nodes[0];
                const node = nodes.get(nodeId);
                const stats = nodeStats[nodeId];
                let html = node?.title || `<p><strong>${{nodeId}}</strong></p>`;
                if (stats) {{
                    html += `<p style="margin-top:8px;color:#888;">Dependencies: ${{stats.deps}}<br>Reverse deps: ${{stats.rdeps}}</p>`;
                }}
                document.getElementById('info').innerHTML = html;
            }}
        }});

        const searchBox = document.getElementById('search-box');
        searchBox.addEventListener('input', e => {{
            const q = e.target.value.toLowerCase();
            if (q.length >= 2) {{
                const matches = allNodes.filter(n => n.id.toLowerCase().includes(q) && visibleNodeIds.has(n.id)).slice(0, 10);
                if (matches.length > 0) {{
                    network.selectNodes(matches.map(n => n.id));
                }}
            }}
        }});

        searchBox.addEventListener('keydown', e => {{
            if (e.key === 'Enter') {{
                const q = e.target.value.toLowerCase();
                const match = allNodes.find(n => n.id.toLowerCase() === q);
                if (match) {{
                    if (!visibleNodeIds.has(match.id)) {{
                        // 自动显示该节点
                        nodes.update({{ id: match.id, hidden: false }});
                        visibleNodeIds.add(match.id);
                    }}
                    network.selectNodes([match.id]);
                    network.focus(match.id, {{ scale: 2, animation: true }});
                    const stats = nodeStats[match.id];
                    let html = match.title || `<p><strong>${{match.id}}</strong></p>`;
                    if (stats) {{
                        html += `<p style="margin-top:8px;color:#888;">Dependencies: ${{stats.deps}}<br>Reverse deps: ${{stats.rdeps}}</p>`;
                    }}
                    document.getElementById('info').innerHTML = html;
                }}
            }}
        }});

        // 支持输入框回车应用过滤器
        ['filter-root', 'filter-min-rdeps', 'filter-min-deps'].forEach(id => {{
            document.getElementById(id).addEventListener('keydown', e => {{
                if (e.key === 'Enter') applyNodeFilters();
            }});
        }});
        document.getElementById('filter-repo').addEventListener('change', applyNodeFilters);
        document.getElementById('filter-no-orphans').addEventListener('change', applyNodeFilters);

        function togglePhysics() {{
            physicsEnabled = !physicsEnabled;
            network.setOptions({{ physics: {{ enabled: physicsEnabled }} }});
        }}
    </script>
</body>
</html>"""

    def _generate_large_graph_html(self, nodes: list[dict], edges: list[dict], title: str) -> str:
        """生成针对大规模图优化的 HTML 内容"""
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #1a1a2e;
            color: #eee;
        }}
        #header {{
            background: #16213e;
            padding: 10px 20px;
            border-bottom: 1px solid #0f3460;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        #header h1 {{
            font-size: 1.3rem;
            font-weight: 500;
        }}
        #stats {{
            font-size: 0.85rem;
            color: #888;
        }}
        #container {{
            display: flex;
            height: calc(100vh - 50px);
        }}
        #network {{
            flex: 1;
            background: #1a1a2e;
        }}
        #sidebar {{
            width: 280px;
            background: #16213e;
            padding: 15px;
            overflow-y: auto;
            border-left: 1px solid #0f3460;
        }}
        #sidebar h3 {{
            margin-bottom: 10px;
            color: #e94560;
            font-size: 1rem;
        }}
        #search-box {{
            width: 100%;
            padding: 8px;
            margin-bottom: 15px;
            background: #1a1a2e;
            border: 1px solid #0f3460;
            color: #eee;
            border-radius: 4px;
        }}
        #search-box:focus {{
            outline: none;
            border-color: #e94560;
        }}
        #info {{
            font-size: 0.85rem;
            line-height: 1.5;
        }}
        #info p {{
            margin: 6px 0;
        }}
        #info .label {{
            color: #888;
        }}
        #legend {{
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #0f3460;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            margin: 6px 0;
            font-size: 0.85rem;
        }}
        .legend-color {{
            width: 14px;
            height: 14px;
            border-radius: 50%;
            margin-right: 8px;
        }}
        #controls {{
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #0f3460;
        }}
        button {{
            background: #e94560;
            color: white;
            border: none;
            padding: 8px 14px;
            cursor: pointer;
            border-radius: 4px;
            font-size: 0.85rem;
            margin: 4px 4px 4px 0;
        }}
        button:hover {{
            background: #ff6b6b;
        }}
        #loading {{
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(22, 33, 62, 0.95);
            padding: 30px 50px;
            border-radius: 8px;
            text-align: center;
            z-index: 1000;
        }}
        #loading.hidden {{
            display: none;
        }}
        .spinner {{
            border: 3px solid #0f3460;
            border-top: 3px solid #e94560;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }}
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
    </style>
</head>
<body>
    <div id="header">
        <h1>{title}</h1>
        <div id="stats">Nodes: {len(nodes)} | Edges: {len(edges)}</div>
    </div>
    <div id="container">
        <div id="network"></div>
        <div id="sidebar">
            <h3>🔍 Search</h3>
            <input type="text" id="search-box" placeholder="Type package name...">

            <h3>📦 Package Info</h3>
            <div id="info">
                <p><em>Click on a node to see details</em></p>
            </div>

            <div id="legend">
                <h3>📊 Legend</h3>
                <div class="legend-item">
                    <div class="legend-color" style="background: #4CAF50;"></div>
                    <span>main</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #2196F3;"></div>
                    <span>community</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #FF9800;"></div>
                    <span>testing</span>
                </div>
            </div>

            <div id="controls">
                <h3>🎮 Controls</h3>
                <button onclick="network.fit()">Fit View</button>
                <button onclick="togglePhysics()">Toggle Physics</button>
                <button onclick="focusSearch()">Search (Ctrl+F)</button>
            </div>
        </div>
    </div>

    <div id="loading">
        <div class="spinner"></div>
        <div>Loading graph...</div>
        <div style="font-size: 0.8rem; color: #888; margin-top: 10px;">This may take a moment for large graphs</div>
    </div>

    <script>
        const nodes = new vis.DataSet({json.dumps(nodes, ensure_ascii=False)});
        const edges = new vis.DataSet({json.dumps(edges, ensure_ascii=False)});

        const container = document.getElementById('network');
        const data = {{ nodes: nodes, edges: edges }};

        // 针对大规模图优化的配置
        const options = {{
            nodes: {{
                shape: 'dot',
                scaling: {{
                    min: 5,
                    max: 40
                }},
                font: {{
                    size: 8,
                    color: '#ffffff'
                }}
            }},
            edges: {{
                width: 0.5,
                color: {{
                    inherit: false
                }},
                smooth: {{
                    enabled: false  // 禁用平滑曲线提高性能
                }}
            }},
            physics: {{
                enabled: true,
                barnesHut: {{
                    gravitationalConstant: -2000,
                    centralGravity: 0.1,
                    springLength: 150,
                    springConstant: 0.01,
                    damping: 0.5,
                    avoidOverlap: 0.1
                }},
                stabilization: {{
                    enabled: true,
                    iterations: 200,  // 减少迭代次数提高性能
                    updateInterval: 25
                }}
            }},
            interaction: {{
                hover: true,
                tooltipDelay: 200,
                hideEdgesOnDrag: true,  // 拖动时隐藏边提高性能
                hideEdgesOnZoom: true   // 缩放时隐藏边提高性能
            }},
            layout: {{
                improvedLayout: false  // 禁用改进布局算法提高大图性能
            }}
        }};

        const network = new vis.Network(container, data, options);
        let physicsEnabled = true;

        // 稳定化完成后隐藏加载提示
        network.on('stabilizationIterationsDone', function() {{
            document.getElementById('loading').classList.add('hidden');
            network.setOptions({{ physics: {{ stabilization: false }} }});
        }});

        // 点击节点显示信息
        network.on('click', function(params) {{
            if (params.nodes.length > 0) {{
                const nodeId = params.nodes[0];
                const node = nodes.get(nodeId);
                showNodeInfo(node);
                highlightConnected(nodeId);
            }}
        }});

        function showNodeInfo(node) {{
            const info = document.getElementById('info');
            info.innerHTML = `
                <p><strong>${{node.id}}</strong></p>
                <p class="label">Repository:</p>
                <p>${{getRepoFromColor(node.color)}}</p>
                <p class="label">Size (relative):</p>
                <p>${{node.size.toFixed(1)}}</p>
            `;
        }}

        function getRepoFromColor(color) {{
            const colorMap = {{
                '#4CAF50': 'main',
                '#2196F3': 'community',
                '#FF9800': 'testing',
                '#9E9E9E': 'unmaintained',
                '#E0E0E0': 'unknown'
            }};
            return colorMap[color] || 'unknown';
        }}

        function highlightConnected(nodeId) {{
            const connectedNodes = network.getConnectedNodes(nodeId);
            const connectedEdges = network.getConnectedEdges(nodeId);

            // 高亮连接的节点和边
            nodes.forEach(node => {{
                if (node.id === nodeId) {{
                    nodes.update({{ id: node.id, opacity: 1.0 }});
                }} else if (connectedNodes.includes(node.id)) {{
                    nodes.update({{ id: node.id, opacity: 0.8 }});
                }} else {{
                    nodes.update({{ id: node.id, opacity: 0.2 }});
                }}
            }});
        }}

        function togglePhysics() {{
            physicsEnabled = !physicsEnabled;
            network.setOptions({{ physics: {{ enabled: physicsEnabled }} }});
        }}

        // 搜索功能
        const searchBox = document.getElementById('search-box');
        searchBox.addEventListener('input', function(e) {{
            const query = e.target.value.toLowerCase();
            if (query.length >= 2) {{
                const matchingNodes = nodes.get().filter(n =>
                    n.id.toLowerCase().includes(query)
                );
                if (matchingNodes.length > 0 && matchingNodes.length <= 10) {{
                    network.selectNodes(matchingNodes.map(n => n.id));
                    if (matchingNodes.length === 1) {{
                        network.focus(matchingNodes[0].id, {{
                            scale: 1.5,
                            animation: true
                        }});
                    }}
                }}
            }}
        }});

        searchBox.addEventListener('keydown', function(e) {{
            if (e.key === 'Enter') {{
                const query = e.target.value.toLowerCase();
                const exactMatch = nodes.get().find(n => n.id.toLowerCase() === query);
                if (exactMatch) {{
                    network.selectNodes([exactMatch.id]);
                    network.focus(exactMatch.id, {{
                        scale: 2,
                        animation: true
                    }});
                    showNodeInfo(exactMatch);
                }}
            }}
        }});

        function focusSearch() {{
            searchBox.focus();
            searchBox.select();
        }}

        // 快捷键
        document.addEventListener('keydown', function(e) {{
            if ((e.ctrlKey || e.metaKey) && e.key === 'f') {{
                e.preventDefault();
                focusSearch();
            }}
        }});
    </script>
</body>
</html>"""


def test_visualizer():
    """测试可视化器"""
    from .graph import DependencyGraph
    from .parser import PackageInfo

    # 创建测试数据
    packages = {
        "app": PackageInfo(name="app", repo="community", depends=["libfoo", "libbar"]),
        "libfoo": PackageInfo(name="libfoo", repo="main", depends=["libc"]),
        "libbar": PackageInfo(name="libbar", repo="main", depends=["libc", "libfoo"]),
        "libc": PackageInfo(name="libc", repo="main"),
    }

    graph = DependencyGraph(packages)
    viz = Visualizer(graph)

    viz.render_html("app", "/tmp/test-deps.html")
    print("Generated: /tmp/test-deps.html")


if __name__ == "__main__":
    test_visualizer()
