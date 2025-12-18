# Alpine Linux APK 依赖关系图谱工具

一个用于爬取、处理和可视化 Alpine Linux apk 软件包依赖关系的工具。

## 功能特性

- 🔍 **依赖爬取**: 从 aports 仓库解析 APKBUILD 文件
- 🔗 **图谱构建**: 构建软件包依赖关系图谱
- 📊 **可视化**: 生成交互式依赖关系图
- 🌐 **Web界面**: 提供交互式 Web 界面浏览依赖
- 📈 **统计分析**: 分析依赖深度、被依赖次数等指标

## 安装

### 使用 uv（推荐）

```bash
# 安装 uv（如果还没有安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 克隆项目
cd dep-map

# 同步依赖并创建虚拟环境
uv sync

# 安装开发依赖
uv sync --dev

# 运行命令
uv run dep-map --help
```

### 使用 pip

```bash
cd dep-map
pip install -e .
```

## 使用方法

### 命令行工具

```bash
# 扫描 aports 仓库并生成依赖图谱
dep-map scan /path/to/aports

# 查询特定包的依赖
dep-map deps curl

# 查询被依赖关系（反向依赖）
dep-map rdeps openssl

# 生成可视化图
dep-map visualize curl --output curl-deps.html

# 启动 Web 界面
dep-map serve --port 8080
```

### Python API

```python
from dep_map import AportsScanner, DependencyGraph, Visualizer

# 扫描 aports 仓库
scanner = AportsScanner('/path/to/aports')
packages = scanner.scan()

# 构建依赖图
graph = DependencyGraph(packages)

# 获取依赖信息
deps = graph.get_dependencies('curl')
rdeps = graph.get_reverse_dependencies('curl')

# 可视化
viz = Visualizer(graph)
viz.render_html('curl', 'curl-deps.html')
```

## 项目结构

```
dep-map/
├── README.md
├── pyproject.toml
├── src/
│   └── dep_map/
│       ├── __init__.py
│       ├── parser.py        # APKBUILD 解析器
│       ├── scanner.py       # aports 仓库扫描器
│       ├── graph.py         # 依赖图谱构建
│       ├── visualizer.py    # 可视化模块
│       ├── analyzer.py      # 统计分析模块
│       ├── web/             # Web 界面
│       │   ├── __init__.py
│       │   ├── app.py
│       │   ├── static/
│       │   └── templates/
│       └── cli.py           # 命令行入口
└── tests/
```

## 依赖

- Python >= 3.10
- networkx - 图处理
- click - 命令行界面
- flask - Web 界面
- pyvis - 可视化
- rich - 终端美化输出

## 开发

```bash
# 安装开发依赖
uv sync --dev

# 运行测试
uv run pytest

# 代码检查和格式化
uv run ruff check .
uv run ruff format .

# 类型检查
uv run mypy src/
```

## License

MIT License
