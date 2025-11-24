import argparse
import os
from typing import Optional, Dict
from .utils import validate_url


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="多线程大文件下载工具，支持断点续传、进度显示和校验功能"
    )

    # 必选参数
    parser.add_argument(
        "url",
        type=str,
        help="要下载的文件URL（支持HTTP/HTTPS协议）"
    )

    # 可选参数
    parser.add_argument(
        "-o", "--output-dir",
        type=str,
        default=".",
        help="文件保存目录（默认：当前目录）"
    )

    parser.add_argument(
        "-t", "--threads",
        type=int,
        default=4,
        help="下载线程数（1-10，默认：4）"
    )

    parser.add_argument(
        "-r", "--retries",
        type=int,
        default=3,
        help="最大重试次数（默认：3）"
    )

    parser.add_argument(
        "-c", "--chunk-size",
        type=str,
        default="1MB",
        help="分块大小（支持KB/MB/GB，默认：1MB）"
    )

    parser.add_argument(
        "--checksum",
        type=str,
        help="文件校验和（用于验证文件完整性）"
    )

    parser.add_argument(
        "--checksum-algorithm",
        type=str,
        choices=["md5", "sha1", "sha224", "sha256", "sha384", "sha512"],
        default="md5",
        help="校验和算法（默认：md5）"
    )

    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="启用调试模式，显示详细日志"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="请求超时时间（秒，默认：30）"
    )

    # 添加示例
    parser.epilog = """示例：
  1. 基本下载：
     python main.py https://example.com/large_file.zip

  2. 指定保存目录和线程数：
     python main.py -o ~/Downloads -t 8 https://example.com/large_file.zip

  3. 自定义分块大小和重试次数：
     python main.py -c 2MB -r 5 https://example.com/large_file.zip

  4. 验证文件完整性：
     python main.py --checksum 1a2b3c4d5e6f7g8h9i0j --checksum-algorithm sha256 https://example.com/large_file.zip

  5. 启用调试模式：
     python main.py -d https://example.com/large_file.zip
"""

    args = parser.parse_args()
    return args


def validate_args(args: argparse.Namespace) -> Dict[str, any]:
    """验证和处理命令行参数"""
    validated = {}

    # 验证URL
    if not validate_url(args.url):
        raise ValueError("无效的URL格式")
    validated["url"] = args.url

    # 验证输出目录
    output_dir = os.path.abspath(args.output_dir)
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
        except OSError as e:
            raise ValueError(f"无法创建输出目录：{e}")
    validated["output_dir"] = output_dir

    # 验证线程数
    threads = max(1, min(args.threads, 10))
    if threads != args.threads:
        print(f"线程数调整为有效范围（1-10）：{threads}")
    validated["num_threads"] = threads

    # 验证重试次数
    retries = max(0, args.retries)
    validated["max_retries"] = retries

    # 处理分块大小
    chunk_size = parse_size(args.chunk_size)
    if chunk_size <= 0:
        raise ValueError(f"无效的分块大小：{args.chunk_size}")
    validated["chunk_size"] = chunk_size

    # 验证校验和
    if args.checksum:
        validated["checksum"] = args.checksum
        validated["checksum_algorithm"] = args.checksum_algorithm
    else:
        validated["checksum"] = None
        validated["checksum_algorithm"] = args.checksum_algorithm

    # 验证超时时间
    timeout = max(1, args.timeout)
    validated["timeout"] = timeout

    validated["debug"] = args.debug

    return validated


def parse_size(size_str: str) -> int:
    """解析大小字符串为字节数"""
    size_str = size_str.strip().upper()
    units = {
        "B": 1,
        "KB": 1024,
        "MB": 1024 * 1024,
        "GB": 1024 * 1024 * 1024,
        "TB": 1024 * 1024 * 1024 * 1024
    }

    # 提取数字和单位
    import re
    match = re.match(r'^(\d+(\.\d+)?)([KMGTB]?B)$', size_str)
    if not match:
        raise ValueError(f"无法解析大小字符串：{size_str}")

    size = float(match.group(1))
    unit = match.group(3)

    return int(size * units[unit])


def get_config() -> Dict[str, any]:
    """获取配置"""
    args = parse_args()
    return validate_args(args)
