# dep-map

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Alpine Linux APK 软件包依赖关系图谱工具。用于爬取、解析、分析和可视化 Alpine Linux 软件包的依赖关系。

## ✨ 功能特性

- 🔍 **解析 APKBUILD** - 支持复杂的 bash 变量展开和动态包名
- 📊 **依赖分析** - 支持运行时依赖、构建依赖、检查依赖
- 🌐 **交互式可视化** - 基于 vis.js 的网络图，支持缩放、搜索、过滤
- 🎯 **多种过滤器** - 按仓库、依赖数、子树等多维度过滤
- 🖥️ **Web 界面** - 提供 REST API 和 Web UI
- ⚡ **缓存支持** - 扫描结果自动缓存，加速后续查询

## 📦 安装

### 使用 uv（推荐）

```bash
# 克隆仓库
git clone https://github.com/sanchuanhehe/dep-map.git
cd dep-map

# 使用 uv 安装
uv sync

# 运行
uv run dep-map --help
```

### 使用 pip

```bash
# 克隆仓库
git clone https://github.com/sanchuanhehe/dep-map.git
cd dep-map

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或 .venv\Scripts\activate  # Windows

# 安装
pip install -e .

# 运行
dep-map --help
```

### 开发安装

```bash
# 安装开发依赖
uv sync --all-extras

# 或使用 pip
pip install -e ".[dev]"

# 运行测试
uv run pytest
```

## 🚀 快速开始

### 1. 准备 aports 仓库

```bash
# 克隆 Alpine Linux aports 仓库
git clone --depth 1 https://gitlab.alpinelinux.org/alpine/aports.git
```

### 2. 扫描仓库

```bash
# 扫描 aports 仓库（结果会自动缓存）
uv run dep-map scan /path/to/aports

# 指定要扫描的仓库
uv run dep-map scan /path/to/aports -r main -r community
```

### 3. 查询依赖

```bash
# 查看包信息
uv run dep-map info gcc

# 查看依赖（树形结构）
uv run dep-map deps gcc --tree

# 查看所有递归依赖
uv run dep-map deps gcc -r -d 5

# 查看反向依赖（谁依赖这个包）
uv run dep-map rdeps musl -r
```

### 4. 生成可视化

```bash
# 生成单个包的依赖图
uv run dep-map visualize gcc -o gcc.html

# 生成完整依赖图概览
uv run dep-map overview --all -o full-graph.html

# 只生成 main 仓库的图
uv run dep-map overview --all --repo main -o main.html
```

## 📖 命令详解

### `scan` - 扫描仓库

扫描 aports 仓库并构建依赖图谱。

```bash
uv run dep-map scan <aports_path> [OPTIONS]

Options:
  -r, --repos TEXT   要扫描的仓库（可多次指定，默认: main, community）
  -o, --output PATH  输出 JSON 文件路径
```

**示例：**
```bash
# 扫描所有仓库
uv run dep-map scan ~/aports -r main -r community -r testing

# 导出为 JSON
uv run dep-map scan ~/aports -o packages.json
```

### `info` - 包信息

显示软件包的详细信息。

```bash
uv run dep-map info <package> [OPTIONS]

Options:
  -a, --aports PATH  aports 仓库路径（如有缓存可省略）
```

**示例：**
```bash
uv run dep-map info nginx
uv run dep-map info python3
```

### `deps` - 依赖查询

查询软件包的依赖关系。

```bash
uv run dep-map deps <package> [OPTIONS]

Options:
  -a, --aports PATH               aports 仓库路径
  -r, --recursive                 递归显示所有依赖
  -d, --depth INTEGER             最大递归深度（默认: 3）
  -t, --type [all|runtime|build]  依赖类型
  --tree                          以树形结构显示
```

**示例：**
```bash
# 树形显示依赖
uv run dep-map deps nginx --tree

# 递归显示所有依赖
uv run dep-map deps gcc -r -d 10

# 只显示构建依赖
uv run dep-map deps linux-headers -t build
```

### `rdeps` - 反向依赖

查询哪些包依赖指定的包。

```bash
uv run dep-map rdeps <package> [OPTIONS]

Options:
  -a, --aports PATH    aports 仓库路径
  -r, --recursive      递归显示
  -d, --depth INTEGER  最大递归深度（默认: 3）
```

**示例：**
```bash
# 查看谁依赖 musl
uv run dep-map rdeps musl

# 递归查看
uv run dep-map rdeps openssl -r -d 2
```

### `path` - 依赖路径

查找两个包之间的依赖路径。

```bash
uv run dep-map path <source> <target> [OPTIONS]

Options:
  -a, --aports PATH  aports 仓库路径
```

**示例：**
```bash
# 查找 nginx 到 musl 的依赖路径
uv run dep-map path nginx musl

# 查找 python3 到 openssl 的路径
uv run dep-map path python3 openssl
```

### `visualize` - 单包可视化

生成单个包的依赖关系可视化图。

```bash
uv run dep-map visualize <package> [OPTIONS]

Options:
  -a, --aports PATH               aports 仓库路径
  -o, --output PATH               输出文件路径 [必需]
  -d, --depth INTEGER             最大深度（默认: 3）
  -f, --format [graph|tree|d3]    输出格式
  -r, --include-reverse           包含反向依赖
  -t, --type [runtime|build|all]  依赖类型（默认: runtime）
  --show-all-types                显示所有依赖类型
```

**依赖类型样式：**
| 类型 | 颜色 | 样式 |
|------|------|------|
| Runtime（运行时） | 绿色 | 实线 |
| Build（构建） | 蓝色 | 虚线 |
| Check（检查） | 橙色 | 点线 |

**示例：**
```bash
# 基本可视化
uv run dep-map visualize nginx -o nginx.html

# 包含反向依赖
uv run dep-map visualize openssl -o openssl.html -r

# 显示所有依赖类型
uv run dep-map visualize gcc -o gcc.html --show-all-types

# 增加深度
uv run dep-map visualize python3 -o python3.html -d 5
```

### `overview` - 全局概览

生成完整的依赖图概览，支持交互式过滤。

```bash
uv run dep-map overview [OPTIONS]

Options:
  -a, --aports PATH               aports 仓库路径
  -o, --output PATH               输出 HTML 文件路径
  -n, --max-nodes INTEGER         最大节点数（默认: 300）
  --all                           显示所有节点
  -r, --repo [main|community|testing]  
                                  只包含指定仓库
```

**HTML 交互功能：**

| 功能 | 说明 |
|------|------|
| **Root Package** | 输入包名查看其依赖子树 |
| **Min Reverse Deps** | 过滤被依赖数少于此值的包 |
| **Min Dependencies** | 过滤依赖数少于此值的包 |
| **Repository** | 只显示指定仓库的包 |
| **Hide orphans** | 隐藏孤立包 |
| **Runtime/Build/Check** | 切换显示的依赖类型 |

**示例：**
```bash
# 生成完整图（所有仓库）
uv run dep-map overview --all -o full-graph.html

# 只生成 main 仓库
uv run dep-map overview --all --repo main -o main.html

# 生成前 500 个重要节点
uv run dep-map overview -n 500 -o top500.html
```

### `stats` - 统计信息

显示依赖图的统计信息。

```bash
uv run dep-map stats [OPTIONS]

Options:
  -a, --aports PATH  aports 仓库路径
  --json             输出 JSON 格式
```

**示例：**
```bash
# 查看统计
uv run dep-map stats

# JSON 格式输出
uv run dep-map stats --json
```

### `serve` - Web 服务

启动 Web 界面和 REST API。

```bash
uv run dep-map serve [OPTIONS]

Options:
  -a, --aports PATH   aports 仓库路径
  -p, --port INTEGER  服务端口（默认: 5000）
  -h, --host TEXT     绑定地址（默认: 127.0.0.1）
```

**示例：**
```bash
# 启动 Web 服务
uv run dep-map serve

# 指定端口
uv run dep-map serve -p 8080

# 允许外部访问
uv run dep-map serve -h 0.0.0.0 -p 8080
```

**API 端点：**

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/packages` | GET | 获取所有包列表 |
| `/api/package/<name>` | GET | 获取包详情 |
| `/api/deps/<name>` | GET | 获取依赖 |
| `/api/rdeps/<name>` | GET | 获取反向依赖 |
| `/api/stats` | GET | 获取统计信息 |

## 🔧 配置

### 缓存位置

扫描结果缓存在 `~/.cache/dep-map/packages.json`。

```bash
# 清除缓存
rm -rf ~/.cache/dep-map/

# 强制重新扫描
uv run dep-map scan /path/to/aports
```

## 🧪 测试

```bash
# 运行所有测试
uv run pytest

# 带覆盖率报告
uv run pytest --cov=dep_map --cov-report=html

# 运行特定测试
uv run pytest tests/test_parser.py -v
```

## 📁 项目结构

```
dep-map/
├── src/dep_map/
│   ├── __init__.py
│   ├── cli.py          # 命令行入口
│   ├── parser.py       # APKBUILD 解析器
│   ├── scanner.py      # 仓库扫描器
│   ├── graph.py        # 依赖图数据结构
│   ├── visualizer.py   # 可视化生成器
│   ├── analyzer.py     # 依赖分析器
│   └── web/            # Web 界面
│       ├── app.py
│       └── templates/
├── tests/              # 测试文件
├── pyproject.toml      # 项目配置
└── README.md
```

## 📄 License

MIT License

## �� 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开 Pull Request
