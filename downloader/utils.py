import os
import re
import hashlib
from typing import Optional


def sanitize_filename(filename: str) -> str:
    """清理文件名中的特殊字符"""
    # 定义不允许的字符
    illegal_chars = r'[<>:"/\\|?*]'
    # 替换不允许的字符为下划线
    sanitized = re.sub(illegal_chars, '_', filename)
    # 去除前后的空格和点
    sanitized = sanitized.strip('. ')
    # 确保文件名不为空
    if not sanitized:
        sanitized = "unnamed_file"
    return sanitized


def create_directory(directory: str) -> bool:
    """创建目录，如果目录不存在"""
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except OSError as e:
        print(f"创建目录失败：{e}")
        return False


def get_file_size(file_path: str) -> int:
    """获取文件大小"""
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0


def calculate_hash(file_path: str, algorithm: str = "md5") -> str:
    """计算文件的哈希值"""
    hash_algorithms = {
        "md5": hashlib.md5,
        "sha1": hashlib.sha1,
        "sha224": hashlib.sha224,
        "sha256": hashlib.sha256,
        "sha384": hashlib.sha384,
        "sha512": hashlib.sha512
    }

    if algorithm not in hash_algorithms:
        raise ValueError(f"不支持的哈希算法：{algorithm}")

    hash_func = hash_algorithms[algorithm]()
    block_size = 65536  # 64KB

    try:
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(block_size), b""):
                hash_func.update(block)
        return hash_func.hexdigest()
    except OSError as e:
        raise IOError(f"读取文件失败：{e}")


def format_file_size(size: int) -> str:
    """格式化文件大小为可读格式"""
    if size == 0:
        return "0 B"
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{size:.1f} {units[i]}"


def format_seconds(seconds: int) -> str:
    """格式化秒数为 HH:MM:SS 格式"""
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def validate_url(url: str) -> bool:
    """验证URL是否合法"""
    # 简单的URL验证正则表达式
    url_pattern = re.compile(
        r'^(https?:\/\/)?'  # 协议
        r'((([a-z\d]([a-z\d-]*[a-z\d])*)\.)+[a-z]{2,}|'  # 域名
        r'((\d{1,3}\.){3}\d{1,3}))'  # IP地址
        r'(\:\d+)?(\/[-a-z\d%_.~+]*)*'  # 端口和路径
        r'(\?[;&a-z\d%_.~+=-]*)?'  # 查询参数
        r'(\#[-a-z\d_]*)?$',  # 锚点
        re.IGNORECASE
    )
    return bool(url_pattern.match(url))


def get_file_extension(url: str) -> str:
    """从URL获取文件扩展名"""
    path = url.split('?')[0].split('#')[0]
    ext = os.path.splitext(path)[1].lower()
    return ext if ext else ""
