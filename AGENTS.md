# AGENTS.md

本文档为 AI 编程助手（如 GitHub Copilot、Cursor、Claude 等）提供项目上下文和开发指南。

## 项目概述

**dep-map** 是一个 Alpine Linux APK 软件包依赖关系图谱工具，用于爬取、解析、分析和可视化 Alpine Linux 软件包的依赖关系。

## 技术栈

- **语言**: Python 3.10+
- **包管理**: uv (推荐) 或 pip
- **构建系统**: hatchling
- **核心依赖**:
  - `networkx` - 图数据结构和算法
  - `click` - CLI 框架
  - `flask` - Web 服务
  - `pyvis` - 网络可视化
  - `rich` - 终端美化输出
  - `jinja2` - 模板引擎

## 项目结构

```
dep-map/
├── src/dep_map/          # 主源码目录
│   ├── __init__.py       # 包初始化
│   ├── cli.py            # 命令行入口 (click)
│   ├── parser.py         # APKBUILD 文件解析器
│   ├── scanner.py        # aports 仓库扫描器
│   ├── graph.py          # 依赖图数据结构 (networkx)
│   ├── analyzer.py       # 依赖分析器
│   ├── visualizer.py     # 可视化生成器
│   └── web/              # Web 界面
│       ├── __init__.py
│       └── app.py        # Flask 应用
├── tests/                # 测试文件
│   ├── test_parser.py
│   └── test_graph.py
├── examples/             # 示例脚本
├── pyproject.toml        # 项目配置
└── README.md
```

## 开发命令

```bash
# 安装依赖
uv sync --all-extras

# 运行 lint 检查 (只检查 src/ 和 tests/)
uv run ruff check src/ tests/

# 运行格式检查
uv run ruff format --check src/ tests/

# 自动修复格式
uv run ruff format src/ tests/

# 运行类型检查
uv run mypy src/dep_map --ignore-missing-imports

# 运行测试
uv run pytest tests/ -v

# 运行测试（带覆盖率）
uv run pytest tests/ --cov=dep_map --cov-report=html

# 构建包
uv build

# 运行 CLI
uv run dep-map --help
```

## 代码风格

- 使用 **ruff** 进行 lint 和格式化
- 行长度限制: 100 字符
- 目标 Python 版本: 3.10
- 启用的 ruff 规则: E, F, I, W, UP, B, C4, SIM
- import 排序: isort 风格，`dep_map` 为 first-party

## 核心模块说明

### parser.py
解析 Alpine Linux 的 APKBUILD 文件，支持:
- Bash 变量展开
- 动态包名解析
- 依赖提取 (depends, makedepends, checkdepends)

### scanner.py
扫描 aports 仓库目录，批量解析所有 APKBUILD 文件。

### graph.py
基于 networkx 的依赖图数据结构:
- 节点: 软件包
- 边: 依赖关系 (runtime, build, check)
- 支持正向/反向依赖查询

### analyzer.py
依赖分析功能:
- 递归依赖解析
- 依赖路径查找
- 循环依赖检测

### visualizer.py
生成交互式 HTML 可视化，基于 vis.js。

### cli.py
Click 框架的命令行接口，子命令包括:
- `scan` - 扫描仓库
- `info` - 查看包信息
- `deps` - 查询依赖
- `rdeps` - 查询反向依赖
- `path` - 查找依赖路径
- `visualize` - 生成可视化
- `overview` - 全局概览
- `stats` - 统计信息
- `serve` - 启动 Web 服务

## CI/CD

GitHub Actions 工作流 (`.github/workflows/ci.yml`):
- 多 Python 版本测试 (3.10, 3.11, 3.12, 3.13)
- ruff lint 和格式检查
- mypy 类型检查
- pytest 测试和覆盖率
- 包构建验证

## 注意事项

1. **只检查 src/ 和 tests/ 目录** - 避免检查整个工作区（可能包含 aports 等大型外部仓库）
2. **缓存位置**: `~/.cache/dep-map/packages.json`
3. **aports 仓库**: 需要单独克隆 Alpine Linux 官方 aports 仓库作为数据源
4. **测试数据**: 测试文件在 `tests/` 目录，使用 pytest 框架

## 常见任务

### 添加新的 CLI 命令
1. 在 `src/dep_map/cli.py` 中添加新的 `@cli.command()` 函数
2. 使用 `click` 装饰器定义参数和选项
3. 添加对应的测试用例

### 修改依赖图结构
1. 修改 `src/dep_map/graph.py` 中的 `DependencyGraph` 类
2. 更新相关的序列化/反序列化逻辑
3. 确保可视化器兼容新结构

### 添加新的依赖类型
1. 在 `parser.py` 中添加解析逻辑
2. 在 `graph.py` 中更新边类型
3. 在 `visualizer.py` 中添加对应的样式
