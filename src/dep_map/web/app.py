"""
Flask Web 应用

提供交互式 Web 界面浏览依赖关系。
"""

from flask import Flask, jsonify, render_template_string, request

from ..analyzer import DependencyAnalyzer
from ..graph import DependencyGraph, DependencyType


def create_app(graph: DependencyGraph) -> Flask:
    """创建 Flask 应用"""
    app = Flask(__name__)
    DependencyAnalyzer(graph)

    # HTML 模板
    INDEX_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Alpine Linux 依赖关系图谱</title>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #0f0f1a;
            color: #e0e0e0;
            height: 100vh;
            overflow: hidden;
        }

        .container {
            display: flex;
            height: 100vh;
        }

        /* 侧边栏 */
        .sidebar {
            width: 350px;
            background: #1a1a2e;
            border-right: 1px solid #2a2a4a;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .sidebar-header {
            padding: 20px;
            background: #16213e;
            border-bottom: 1px solid #2a2a4a;
        }

        .sidebar-header h1 {
            font-size: 1.3rem;
            font-weight: 600;
            color: #fff;
            margin-bottom: 5px;
        }

        .sidebar-header p {
            font-size: 0.85rem;
            color: #888;
        }

        /* 搜索框 */
        .search-box {
            padding: 15px 20px;
            border-bottom: 1px solid #2a2a4a;
        }

        .search-input {
            width: 100%;
            padding: 12px 15px;
            border: 1px solid #3a3a5a;
            border-radius: 8px;
            background: #0f0f1a;
            color: #fff;
            font-size: 0.95rem;
        }

        .search-input:focus {
            outline: none;
            border-color: #e94560;
            box-shadow: 0 0 0 3px rgba(233, 69, 96, 0.2);
        }

        .search-results {
            max-height: 200px;
            overflow-y: auto;
            margin-top: 10px;
        }

        .search-result-item {
            padding: 8px 12px;
            cursor: pointer;
            border-radius: 4px;
            font-size: 0.9rem;
        }

        .search-result-item:hover {
            background: #2a2a4a;
        }

        .search-result-item .repo {
            font-size: 0.75rem;
            color: #888;
            margin-left: 8px;
        }

        /* 信息面板 */
        .info-panel {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
        }

        .package-info {
            display: none;
        }

        .package-info.active {
            display: block;
        }

        .package-name {
            font-size: 1.4rem;
            font-weight: 600;
            color: #fff;
            margin-bottom: 5px;
        }

        .package-version {
            color: #888;
            font-size: 0.9rem;
            margin-bottom: 15px;
        }

        .package-desc {
            color: #aaa;
            font-size: 0.9rem;
            line-height: 1.5;
            margin-bottom: 20px;
        }

        .info-section {
            margin-bottom: 20px;
        }

        .info-section h3 {
            font-size: 0.85rem;
            text-transform: uppercase;
            color: #e94560;
            margin-bottom: 10px;
            letter-spacing: 0.5px;
        }

        .stat-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }

        .stat-item {
            background: #0f0f1a;
            padding: 12px;
            border-radius: 8px;
        }

        .stat-value {
            font-size: 1.5rem;
            font-weight: 600;
            color: #fff;
        }

        .stat-label {
            font-size: 0.75rem;
            color: #888;
            margin-top: 3px;
        }

        .dep-list {
            max-height: 150px;
            overflow-y: auto;
        }

        .dep-item {
            padding: 6px 10px;
            background: #0f0f1a;
            border-radius: 4px;
            margin-bottom: 5px;
            font-size: 0.85rem;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .dep-item:hover {
            background: #2a2a4a;
        }

        .dep-item .repo-tag {
            font-size: 0.7rem;
            padding: 2px 6px;
            border-radius: 3px;
            background: #2a2a4a;
        }

        /* 按钮 */
        .btn-group {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }

        .btn {
            flex: 1;
            padding: 10px;
            border: none;
            border-radius: 6px;
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.2s;
        }

        .btn-primary {
            background: #e94560;
            color: #fff;
        }

        .btn-primary:hover {
            background: #ff6b6b;
        }

        .btn-secondary {
            background: #2a2a4a;
            color: #fff;
        }

        .btn-secondary:hover {
            background: #3a3a5a;
        }

        /* 主内容区 */
        .main-content {
            flex: 1;
            display: flex;
            flex-direction: column;
        }

        .toolbar {
            padding: 10px 20px;
            background: #1a1a2e;
            border-bottom: 1px solid #2a2a4a;
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .toolbar select {
            padding: 8px 12px;
            border: 1px solid #3a3a5a;
            border-radius: 6px;
            background: #0f0f1a;
            color: #fff;
            font-size: 0.9rem;
        }

        .toolbar label {
            font-size: 0.85rem;
            color: #888;
        }

        #network {
            flex: 1;
            background: #0f0f1a;
        }

        /* 图例 */
        .legend {
            position: absolute;
            bottom: 20px;
            right: 20px;
            background: rgba(26, 26, 46, 0.95);
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #2a2a4a;
        }

        .legend-title {
            font-size: 0.8rem;
            color: #888;
            margin-bottom: 10px;
        }

        .legend-item {
            display: flex;
            align-items: center;
            margin-bottom: 8px;
            font-size: 0.85rem;
        }

        .legend-color {
            width: 14px;
            height: 14px;
            border-radius: 50%;
            margin-right: 10px;
        }

        /* 欢迎信息 */
        .welcome-message {
            text-align: center;
            color: #666;
            padding: 40px;
        }

        .welcome-message h2 {
            font-size: 1.2rem;
            margin-bottom: 10px;
            color: #888;
        }

        /* 统计面板 */
        .stats-panel {
            padding: 20px;
        }

        .stats-panel h2 {
            font-size: 1rem;
            margin-bottom: 15px;
            color: #e94560;
        }

        /* 滚动条样式 */
        ::-webkit-scrollbar {
            width: 8px;
        }

        ::-webkit-scrollbar-track {
            background: #0f0f1a;
        }

        ::-webkit-scrollbar-thumb {
            background: #3a3a5a;
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: #4a4a6a;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <div class="sidebar-header">
                <h1>🏔️ Alpine 依赖图谱</h1>
                <p>{{ total_packages }} 个软件包</p>
            </div>

            <div class="search-box">
                <input type="text" class="search-input" id="searchInput" placeholder="搜索软件包...">
                <div class="search-results" id="searchResults"></div>
            </div>

            <div class="info-panel">
                <div class="welcome-message" id="welcomeMessage">
                    <h2>👋 欢迎使用</h2>
                    <p>在上方搜索框输入包名开始探索依赖关系</p>
                </div>

                <div class="package-info" id="packageInfo">
                    <div class="package-name" id="pkgName"></div>
                    <div class="package-version" id="pkgVersion"></div>
                    <div class="package-desc" id="pkgDesc"></div>

                    <div class="info-section">
                        <h3>统计</h3>
                        <div class="stat-grid">
                            <div class="stat-item">
                                <div class="stat-value" id="statDeps">-</div>
                                <div class="stat-label">依赖数</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value" id="statRdeps">-</div>
                                <div class="stat-label">被依赖</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value" id="statTotalDeps">-</div>
                                <div class="stat-label">递归依赖</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value" id="statRepo">-</div>
                                <div class="stat-label">仓库</div>
                            </div>
                        </div>
                    </div>

                    <div class="info-section">
                        <h3>直接依赖</h3>
                        <div class="dep-list" id="depsList"></div>
                    </div>

                    <div class="info-section">
                        <h3>被这些包依赖</h3>
                        <div class="dep-list" id="rdepsList"></div>
                    </div>

                    <div class="btn-group">
                        <button class="btn btn-primary" onclick="expandDeps()">展开依赖</button>
                        <button class="btn btn-secondary" onclick="expandRdeps()">展开被依赖</button>
                    </div>
                </div>

                <div class="stats-panel" id="statsPanel" style="display: none;">
                    <h2>全局统计</h2>
                    <div class="stat-grid" id="globalStats"></div>
                </div>
            </div>
        </div>

        <div class="main-content">
            <div class="toolbar">
                <label>深度:</label>
                <select id="depthSelect">
                    <option value="1">1</option>
                    <option value="2" selected>2</option>
                    <option value="3">3</option>
                    <option value="4">4</option>
                </select>

                <label>依赖类型:</label>
                <select id="typeSelect">
                    <option value="all">全部</option>
                    <option value="runtime">运行时</option>
                    <option value="build">构建</option>
                </select>

                <button class="btn btn-secondary" onclick="resetView()">重置视图</button>
                <button class="btn btn-secondary" onclick="showStats()">全局统计</button>
            </div>

            <div id="network"></div>

            <div class="legend">
                <div class="legend-title">图例</div>
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
        </div>
    </div>

    <script>
        const REPO_COLORS = {
            'main': '#4CAF50',
            'community': '#2196F3',
            'testing': '#FF9800',
            'unmaintained': '#9E9E9E',
            'unknown': '#E0E0E0'
        };

        let network = null;
        let currentPackage = null;
        let nodes = new vis.DataSet([]);
        let edges = new vis.DataSet([]);

        // 初始化网络图
        function initNetwork() {
            const container = document.getElementById('network');
            const data = { nodes: nodes, edges: edges };
            const options = {
                nodes: {
                    shape: 'dot',
                    borderWidth: 2,
                    shadow: true,
                    font: { color: '#ffffff', size: 12 }
                },
                edges: {
                    width: 1,
                    arrows: 'to',
                    color: { color: '#555555', opacity: 0.6 },
                    smooth: { type: 'continuous' }
                },
                physics: {
                    enabled: true,
                    barnesHut: {
                        gravitationalConstant: -5000,
                        centralGravity: 0.3,
                        springLength: 100,
                        springConstant: 0.04,
                        damping: 0.09
                    }
                },
                interaction: {
                    hover: true,
                    tooltipDelay: 200
                }
            };

            network = new vis.Network(container, data, options);

            network.on('click', function(params) {
                if (params.nodes.length > 0) {
                    loadPackage(params.nodes[0]);
                }
            });
        }

        // 搜索功能
        const searchInput = document.getElementById('searchInput');
        const searchResults = document.getElementById('searchResults');
        let searchTimeout = null;

        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            const query = this.value.trim();

            if (query.length < 2) {
                searchResults.innerHTML = '';
                return;
            }

            searchTimeout = setTimeout(() => {
                fetch(`/api/search?q=${encodeURIComponent(query)}`)
                    .then(res => res.json())
                    .then(data => {
                        searchResults.innerHTML = data.results.map(pkg => `
                            <div class="search-result-item" onclick="loadPackage('${pkg.name}')">
                                ${pkg.name}
                                <span class="repo">${pkg.repo}</span>
                            </div>
                        `).join('');
                    });
            }, 200);
        });

        // 加载软件包
        function loadPackage(name) {
            currentPackage = name;
            searchInput.value = name;
            searchResults.innerHTML = '';

            fetch(`/api/package/${encodeURIComponent(name)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.error) {
                        alert(data.error);
                        return;
                    }

                    // 显示信息面板
                    document.getElementById('welcomeMessage').style.display = 'none';
                    document.getElementById('statsPanel').style.display = 'none';
                    document.getElementById('packageInfo').classList.add('active');

                    // 填充信息
                    document.getElementById('pkgName').textContent = data.name;
                    document.getElementById('pkgVersion').textContent = `${data.version}`;
                    document.getElementById('pkgDesc').textContent = data.description || '无描述';

                    document.getElementById('statDeps').textContent = data.deps_count;
                    document.getElementById('statRdeps').textContent = data.rdeps_count;
                    document.getElementById('statTotalDeps').textContent = data.total_deps_count;
                    document.getElementById('statRepo').textContent = data.repo || 'N/A';

                    // 依赖列表
                    document.getElementById('depsList').innerHTML = data.deps.map(d => `
                        <div class="dep-item" onclick="loadPackage('${d.name}')">
                            ${d.name}
                            <span class="repo-tag">${d.repo || 'N/A'}</span>
                        </div>
                    `).join('') || '<div style="color: #666; padding: 10px;">无依赖</div>';

                    // 被依赖列表
                    document.getElementById('rdepsList').innerHTML = data.rdeps.slice(0, 20).map(d => `
                        <div class="dep-item" onclick="loadPackage('${d.name}')">
                            ${d.name}
                            <span class="repo-tag">${d.repo || 'N/A'}</span>
                        </div>
                    `).join('') || '<div style="color: #666; padding: 10px;">无</div>';

                    if (data.rdeps.length > 20) {
                        document.getElementById('rdepsList').innerHTML += `
                            <div style="color: #888; padding: 10px; text-align: center;">
                                还有 ${data.rdeps.length - 20} 个...
                            </div>
                        `;
                    }

                    // 更新图
                    updateGraph(name);
                });
        }

        // 更新图
        function updateGraph(centerPkg) {
            const depth = document.getElementById('depthSelect').value;
            const depType = document.getElementById('typeSelect').value;

            fetch(`/api/graph/${encodeURIComponent(centerPkg)}?depth=${depth}&type=${depType}`)
                .then(res => res.json())
                .then(data => {
                    nodes.clear();
                    edges.clear();

                    nodes.add(data.nodes.map(n => ({
                        id: n.id,
                        label: n.id,
                        color: REPO_COLORS[n.repo] || REPO_COLORS.unknown,
                        size: n.id === centerPkg ? 25 : 15,
                        font: { size: n.id === centerPkg ? 14 : 10 }
                    })));

                    edges.add(data.edges.map(e => ({
                        from: e.from,
                        to: e.to
                    })));

                    network.fit();
                });
        }

        // 展开依赖
        function expandDeps() {
            if (currentPackage) {
                document.getElementById('depthSelect').value = '3';
                updateGraph(currentPackage);
            }
        }

        // 展开被依赖
        function expandRdeps() {
            if (currentPackage) {
                fetch(`/api/rdeps-graph/${encodeURIComponent(currentPackage)}?depth=2`)
                    .then(res => res.json())
                    .then(data => {
                        nodes.clear();
                        edges.clear();

                        nodes.add(data.nodes.map(n => ({
                            id: n.id,
                            label: n.id,
                            color: REPO_COLORS[n.repo] || REPO_COLORS.unknown,
                            size: n.id === currentPackage ? 25 : 15
                        })));

                        edges.add(data.edges.map(e => ({
                            from: e.from,
                            to: e.to
                        })));

                        network.fit();
                    });
            }
        }

        // 重置视图
        function resetView() {
            nodes.clear();
            edges.clear();
            currentPackage = null;
            searchInput.value = '';
            document.getElementById('packageInfo').classList.remove('active');
            document.getElementById('statsPanel').style.display = 'none';
            document.getElementById('welcomeMessage').style.display = 'block';
        }

        // 显示全局统计
        function showStats() {
            document.getElementById('welcomeMessage').style.display = 'none';
            document.getElementById('packageInfo').classList.remove('active');
            document.getElementById('statsPanel').style.display = 'block';

            fetch('/api/stats')
                .then(res => res.json())
                .then(data => {
                    document.getElementById('globalStats').innerHTML = `
                        <div class="stat-item">
                            <div class="stat-value">${data.total_packages}</div>
                            <div class="stat-label">总包数</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${data.total_edges}</div>
                            <div class="stat-label">依赖边</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${data.main_count || 0}</div>
                            <div class="stat-label">main</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${data.community_count || 0}</div>
                            <div class="stat-label">community</div>
                        </div>
                    `;

                    // 显示最被依赖的包
                    fetch('/api/most-depended?n=10')
                        .then(res => res.json())
                        .then(topData => {
                            const topHtml = topData.packages.map((p, i) => `
                                <div class="dep-item" onclick="loadPackage('${p.name}')">
                                    #${i+1} ${p.name}
                                    <span class="repo-tag">${p.count} deps</span>
                                </div>
                            `).join('');

                            document.getElementById('globalStats').innerHTML += `
                                <div style="grid-column: span 2; margin-top: 15px;">
                                    <h3 style="color: #e94560; font-size: 0.85rem; margin-bottom: 10px;">被依赖最多</h3>
                                    ${topHtml}
                                </div>
                            `;
                        });
                });
        }

        // 监听设置变化
        document.getElementById('depthSelect').addEventListener('change', () => {
            if (currentPackage) updateGraph(currentPackage);
        });

        document.getElementById('typeSelect').addEventListener('change', () => {
            if (currentPackage) updateGraph(currentPackage);
        });

        // 初始化
        initNetwork();
    </script>
</body>
</html>
"""

    @app.route("/")
    def index():
        return render_template_string(INDEX_HTML, total_packages=len(graph.packages))

    @app.route("/api/search")
    def api_search():
        query = request.args.get("q", "").lower()
        if len(query) < 2:
            return jsonify({"results": []})

        results = []
        for name, pkg in graph.packages.items():
            if query in name.lower():
                results.append(
                    {
                        "name": name,
                        "repo": pkg.repo,
                    }
                )
                if len(results) >= 20:
                    break

        return jsonify({"results": results})

    @app.route("/api/package/<name>")
    def api_package(name: str):
        if name not in graph.packages:
            return jsonify({"error": "Package not found"}), 404

        pkg = graph.packages[name]
        deps = graph.get_dependencies(name)
        rdeps = graph.get_reverse_dependencies(name)
        total_deps = graph.get_dependencies(name, recursive=True)

        return jsonify(
            {
                "name": pkg.name,
                "version": f"{pkg.version}-r{pkg.release}",
                "description": pkg.description,
                "repo": pkg.repo,
                "url": pkg.url,
                "license": pkg.license,
                "deps_count": len(deps),
                "rdeps_count": len(rdeps),
                "total_deps_count": len(total_deps),
                "deps": [
                    {"name": d, "repo": graph.packages[d].repo if d in graph.packages else None}
                    for d in deps
                ],
                "rdeps": [
                    {"name": d, "repo": graph.packages[d].repo if d in graph.packages else None}
                    for d in rdeps
                ],
            }
        )

    @app.route("/api/graph/<name>")
    def api_graph(name: str):
        if name not in graph.packages:
            return jsonify({"error": "Package not found"}), 404

        depth = int(request.args.get("depth", 2))
        dep_type_str = request.args.get("type", "all")

        dep_type = {
            "all": DependencyType.ALL,
            "runtime": DependencyType.RUNTIME,
            "build": DependencyType.BUILD,
        }.get(dep_type_str, DependencyType.ALL)

        # 收集节点
        nodes_set = {name}
        deps = graph.get_dependencies(name, dep_type=dep_type, recursive=True, max_depth=depth)
        nodes_set.update(deps)

        nodes = []
        edges = []

        for node in nodes_set:
            pkg = graph.packages.get(node)
            nodes.append(
                {
                    "id": node,
                    "repo": pkg.repo if pkg else "unknown",
                }
            )

        for node in nodes_set:
            for dep in graph.get_dependencies(node, dep_type=dep_type):
                if dep in nodes_set:
                    edges.append({"from": node, "to": dep})

        return jsonify({"nodes": nodes, "edges": edges})

    @app.route("/api/rdeps-graph/<name>")
    def api_rdeps_graph(name: str):
        if name not in graph.packages:
            return jsonify({"error": "Package not found"}), 404

        depth = int(request.args.get("depth", 2))

        # 收集反向依赖节点
        nodes_set = {name}
        rdeps = graph.get_reverse_dependencies(name, recursive=True, max_depth=depth)
        nodes_set.update(rdeps)

        nodes = []
        edges = []

        for node in nodes_set:
            pkg = graph.packages.get(node)
            nodes.append(
                {
                    "id": node,
                    "repo": pkg.repo if pkg else "unknown",
                }
            )

        for node in nodes_set:
            if node != name:
                for dep in graph.get_dependencies(node):
                    if dep in nodes_set:
                        edges.append({"from": node, "to": dep})

        return jsonify({"nodes": nodes, "edges": edges})

    @app.route("/api/stats")
    def api_stats():
        stats = graph.get_statistics()

        repo_counts = {}
        for pkg in graph.packages.values():
            repo = pkg.repo or "unknown"
            repo_counts[repo] = repo_counts.get(repo, 0) + 1

        return jsonify(
            {
                "total_packages": stats["nodes"],
                "total_edges": stats["edges"],
                "main_count": repo_counts.get("main", 0),
                "community_count": repo_counts.get("community", 0),
                "testing_count": repo_counts.get("testing", 0),
            }
        )

    @app.route("/api/most-depended")
    def api_most_depended():
        n = int(request.args.get("n", 20))
        most_depended = graph.get_most_depended(n)

        return jsonify(
            {"packages": [{"name": name, "count": count} for name, count in most_depended]}
        )

    return app
