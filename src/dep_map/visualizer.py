"""
依赖关系可视化模块

生成交互式依赖关系图。
"""

import json
import os
from typing import Optional, List, Dict, Any
from pathlib import Path

from .graph import DependencyGraph, DependencyType


class Visualizer:
    """依赖关系可视化器"""
    
    # 节点颜色配置
    REPO_COLORS = {
        "main": "#4CAF50",       # 绿色
        "community": "#2196F3",  # 蓝色
        "testing": "#FF9800",    # 橙色
        "unmaintained": "#9E9E9E",  # 灰色
        "unknown": "#E0E0E0",    # 浅灰
    }
    
    DEP_TYPE_COLORS = {
        "runtime": "#4CAF50",    # 绿色
        "build": "#2196F3",      # 蓝色
        "check": "#FF9800",      # 橙色
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
        dep_type: DependencyType = DependencyType.ALL,
        max_depth: int = 3,
        include_reverse: bool = False,
        title: Optional[str] = None
    ):
        """
        渲染为交互式 HTML 文件
        
        Args:
            package: 中心软件包
            output_path: 输出文件路径
            dep_type: 依赖类型
            max_depth: 最大深度
            include_reverse: 是否包含反向依赖
            title: 页面标题
        """
        # 收集需要显示的节点
        nodes_to_show = {package}
        
        # 添加依赖
        deps = self.graph.get_dependencies(
            package, 
            dep_type=dep_type, 
            recursive=True, 
            max_depth=max_depth
        )
        nodes_to_show.update(deps)
        
        # 添加反向依赖
        if include_reverse:
            rdeps = self.graph.get_reverse_dependencies(
                package,
                dep_type=dep_type,
                recursive=True,
                max_depth=max_depth
            )
            nodes_to_show.update(rdeps)
        
        # 构建节点和边数据
        nodes_data = []
        edges_data = []
        
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
        
        # 添加边
        for node in nodes_to_show:
            for dep in self.graph.get_dependencies(node, dep_type=dep_type):
                if dep in nodes_to_show:
                    edges_data.append({
                        "from": node,
                        "to": dep,
                        "arrows": "to",
                        "color": {"color": "#888888", "opacity": 0.6},
                    })
        
        # 生成 HTML
        html_content = self._generate_visjs_html(
            nodes_data, 
            edges_data,
            title=title or f"Dependency Graph: {package}"
        )
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def render_d3_html(
        self,
        package: str,
        output_path: str,
        dep_type: DependencyType = DependencyType.ALL,
        max_depth: int = 3,
        title: Optional[str] = None
    ):
        """
        使用 D3.js 渲染为交互式 HTML 文件（力导向图）
        """
        # 收集节点
        nodes_to_show = {package}
        deps = self.graph.get_dependencies(
            package, 
            dep_type=dep_type, 
            recursive=True, 
            max_depth=max_depth
        )
        nodes_to_show.update(deps)
        
        # 构建数据
        nodes = []
        links = []
        
        for i, node in enumerate(nodes_to_show):
            pkg_info = self.graph.packages.get(node)
            repo = pkg_info.repo if pkg_info else "unknown"
            
            nodes.append({
                "id": node,
                "group": repo,
                "isCenter": node == package,
            })
        
        for node in nodes_to_show:
            for dep in self.graph.get_dependencies(node, dep_type=dep_type):
                if dep in nodes_to_show:
                    links.append({
                        "source": node,
                        "target": dep,
                    })
        
        # 生成 HTML
        html_content = self._generate_d3_html(
            nodes, 
            links,
            title=title or f"Dependency Graph: {package}"
        )
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def render_tree_html(
        self,
        package: str,
        output_path: str,
        dep_type: DependencyType = DependencyType.ALL,
        max_depth: int = 4,
        title: Optional[str] = None
    ):
        """
        渲染为树形结构 HTML
        """
        tree_data = self.graph.get_dependency_tree(package, dep_type, max_depth)
        
        html_content = self._generate_tree_html(
            tree_data,
            title=title or f"Dependency Tree: {package}"
        )
        
        with open(output_path, 'w', encoding='utf-8') as f:
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
    
    def _generate_visjs_html(
        self, 
        nodes: List[dict], 
        edges: List[dict],
        title: str
    ) -> str:
        """生成 vis.js HTML 内容"""
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
</html>'''
    
    def _generate_d3_html(
        self, 
        nodes: List[dict], 
        links: List[dict],
        title: str
    ) -> str:
        """生成 D3.js HTML 内容"""
        return f'''<!DOCTYPE html>
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
</html>'''
    
    def _generate_tree_html(self, tree_data: dict, title: str) -> str:
        """生成树形结构 HTML 内容"""
        return f'''<!DOCTYPE html>
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
</html>'''
    
    def render_full_graph_html(
        self,
        output_path: str,
        max_nodes: int = 500,
        title: str = "Full Dependency Graph"
    ):
        """
        渲染完整的依赖图（带性能优化）
        """
        # 选择最重要的节点（被依赖最多的）
        most_depended = self.graph.get_most_depended(max_nodes)
        nodes_to_show = set(pkg for pkg, _ in most_depended)
        
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
            
            nodes_data.append(node_data)
        
        # 只添加节点之间的边
        for node in nodes_to_show:
            for dep in self.graph.get_dependencies(node):
                if dep in nodes_to_show:
                    edges_data.append({
                        "from": node,
                        "to": dep,
                        "arrows": "to",
                        "color": {"color": "#444444", "opacity": 0.3},
                    })
        
        html_content = self._generate_visjs_html(nodes_data, edges_data, title)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def render_complete_graph_html(
        self,
        output_path: str,
        title: str = "Complete Dependency Graph"
    ):
        """
        渲染包含所有节点的完整依赖图
        
        使用优化的渲染方式以支持大规模图谱显示。
        """
        all_packages = list(self.graph.packages.keys())
        
        # 收集节点和边的数据
        nodes_data = []
        edges_data = []
        
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
                "size": min(5 + rdep_count / 10, 40),  # 根据被依赖数调整大小
                "font": {"size": 8},  # 更小的字体
            }
            
            if pkg_info:
                node_data["title"] = self._make_tooltip(pkg_info)
            
            nodes_data.append(node_data)
        
        # 添加所有边
        for node in all_packages:
            for dep in self.graph.get_dependencies(node):
                if dep in self.graph.packages:
                    edges_data.append({
                        "from": node,
                        "to": dep,
                        "arrows": "to",
                        "color": {"color": "#444444", "opacity": 0.2},
                    })
        
        # 使用优化的 HTML 模板
        html_content = self._generate_large_graph_html(nodes_data, edges_data, title)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _generate_large_graph_html(
        self, 
        nodes: List[dict], 
        edges: List[dict],
        title: str
    ) -> str:
        """生成针对大规模图优化的 HTML 内容"""
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
</html>'''


def test_visualizer():
    """测试可视化器"""
    from .parser import PackageInfo
    from .graph import DependencyGraph
    
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
