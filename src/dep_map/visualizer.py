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
