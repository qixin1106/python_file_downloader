# 多线程大文件下载工具

一个基于 Python 3.10+ 开发的多线程大文件下载工具，支持断点续传、进度显示、文件校验等功能。

## 功能特性

### 基础下载
- 支持 HTTP/HTTPS 协议
- 处理中文/特殊字符文件名
- 允许自定义保存目录（目录不存在时自动创建）
- 解决文件名冲突
- 默认 1MB 分块下载，支持用户自定义分块大小

### 多线程高效下载
- 默认 4 线程（可自定义，限制 1-10 线程）
- 基于 ThreadPoolExecutor 实现分块并行下载
- 服务器不支持 Range 请求时自动降级为单线程
- 每个线程独立下载临时切片文件，下载完成后合并为最终文件

### 断点续传
- 通过状态文件记录已完成切片
- 重启工具后仅下载未完成部分
- 支持单个切片续传（检测临时文件大小，通过 Range 请求续传剩余内容）
- 本地文件大小≥服务器文件大小时，提示文件完整无需重复下载

### 进度与日志可视化
- 双进度展示
  - 全局进度条：显示总大小、已下载占比、平均速度、剩余时间
  - 切片进度详情：每秒刷新，显示切片 ID、已下载/切片大小、瞬时速度，不刷屏
- 分级日志输出（普通/成功/警告/错误/调试日志，带时间戳）
- 通过 colorama 实现颜色区分

### 完整性与异常处理
- 支持 MD5/SHA256 等多种校验算法（用户传入校验值时自动对比）
- 对 429/500-504 状态码、网络超时、连接错误自动重试（默认 3 次，支持自定义）
- 加入指数退避策略
- 捕获网络异常、文件 I/O 异常等
- 用户按 Ctrl+C 时优雅退出，保存断点状态并提示续传

### 命令行交互
- 支持 URL 必选参数
- 支持输出目录、线程数、重试次数、分块大小、校验和、校验算法、调试日志等可选参数
- 提供清晰示例命令

## 安装依赖

本项目使用 uv 工具管理依赖。

```bash
# 安装依赖
uv sync
```

## 使用方法

### 基本用法

```bash
python main.py https://example.com/large_file.zip
```

### 常用选项

```bash
# 指定保存目录和线程数
python main.py -o ~/Downloads -t 8 https://example.com/large_file.zip

# 自定义分块大小和重试次数
python main.py -c 2MB -r 5 https://example.com/large_file.zip

# 验证文件完整性
python main.py --checksum 1a2b3c4d5e6f7g8h9i0j --checksum-algorithm sha256 https://example.com/large_file.zip

# 启用调试模式
python main.py -d https://example.com/large_file.zip

# 自定义超时时间
python main.py --timeout 60 https://example.com/large_file.zip
```

### 所有选项

```
usage: main.py [-h] [-o OUTPUT_DIR] [-t THREADS] [-r RETRIES] [-c CHUNK_SIZE] [--checksum CHECKSUM] [--checksum-algorithm {md5,sha1,sha224,sha256,sha384,sha512}] [-d] [--timeout TIMEOUT] url

多线程大文件下载工具，支持断点续传、进度显示和校验功能

positional arguments:
  url                   要下载的文件URL（支持HTTP/HTTPS协议）

options:
  -h, --help            show this help message and exit
  -o OUTPUT_DIR, --output-dir OUTPUT_DIR
                        文件保存目录（默认：当前目录）
  -t THREADS, --threads THREADS
                        下载线程数（1-10，默认：4）
  -r RETRIES, --retries RETRIES
                        最大重试次数（默认：3）
  -c CHUNK_SIZE, --chunk-size CHUNK_SIZE
                        分块大小（支持KB/MB/GB，默认：1MB）
  --checksum CHECKSUM   文件校验和（用于验证文件完整性）
  --checksum-algorithm {md5,sha1,sha224,sha256,sha384,sha512}
                        校验和算法（默认：md5）
  -d, --debug           启用调试模式，显示详细日志
  --timeout TIMEOUT     请求超时时间（秒，默认：30）
```

## 项目结构

```
python-downloader/
├── main.py              # 主入口文件
├── downloader/          # 核心模块目录
│   ├── __init__.py      # 包初始化文件
│   ├── core.py          # 下载核心逻辑
│   ├── config.py        # 配置和命令行参数解析
│   ├── logger.py        # 日志管理
│   ├── progress.py      # 进度显示
│   └── utils.py         # 工具函数
├── pyproject.toml       # 项目配置
├── uv.lock              # uv 依赖锁定文件
└── README.md            # 项目说明文档
```

## 技术实现

### 分层架构设计

1. **核心层 (core.py)**：实现下载核心逻辑，包括文件信息获取、分块管理、多线程下载、文件合并等
2. **配置层 (config.py)**：处理命令行参数解析和验证
3. **日志层 (logger.py)**：实现分级日志输出和颜色区分
4. **进度层 (progress.py)**：管理下载进度显示
5. **工具层 (utils.py)**：提供各种辅助功能函数

### 关键技术点

- **多线程下载**：使用 ThreadPoolExecutor 实现并行下载
- **断点续传**：通过 Range 请求和状态文件实现
- **进度显示**：使用 tqdm 库实现全局进度条，自定义线程实现分块进度详情
- **异常处理**：全面捕获网络异常、文件 I/O 异常等
- **文件校验**：支持多种哈希算法验证文件完整性

## 开发要求

- Python 3.10+
- uv 依赖管理工具

## 许可证

MIT License
