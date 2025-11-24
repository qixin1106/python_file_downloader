import os
import re
import json
import hashlib
import threading
from typing import List, Tuple, Optional, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError
from .progress import ProgressManager
from .logger import Logger
from .utils import sanitize_filename, create_directory, get_file_size, calculate_hash


class Downloader:
    def __init__(self,
                 url: str,
                 output_dir: str = ".",
                 num_threads: int = 4,
                 chunk_size: int = 1024 * 1024,
                 max_retries: int = 3,
                 timeout: int = 30,
                 checksum: Optional[str] = None,
                 checksum_algorithm: str = "md5",
                 debug: bool = False):
        self.url = url
        self.output_dir = output_dir
        self.num_threads = max(1, min(num_threads, 10))  # 限制线程数在1-10之间
        self.chunk_size = chunk_size
        self.max_retries = max_retries
        self.timeout = timeout
        self.checksum = checksum
        self.checksum_algorithm = checksum_algorithm.lower()
        self.debug = debug

        self.logger = Logger(debug=self.debug)
        self.progress_manager = ProgressManager()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })

        # 初始化下载信息
        self.file_name: Optional[str] = None
        self.file_size: int = 0
        self.can_resume: bool = False
        self.temp_dir: Optional[str] = None
        self.status_file: Optional[str] = None
        self.chunks: List[Dict] = []

    def _get_file_info(self) -> bool:
        """获取文件信息：文件名、大小、是否支持断点续传"""
        try:
            response = self.session.head(self.url, allow_redirects=True, timeout=self.timeout)
            response.raise_for_status()

            # 获取文件大小
            if "Content-Length" in response.headers:
                self.file_size = int(response.headers["Content-Length"])

            # 检查是否支持Range请求
            self.can_resume = "Accept-Ranges" in response.headers and response.headers["Accept-Ranges"] == "bytes"

            # 获取文件名
            self.file_name = self._extract_filename(response)
            if not self.file_name:
                self.file_name = sanitize_filename(os.path.basename(self.url))

            self.logger.info(f"文件信息获取成功：{self.file_name}")
            self.logger.info(f"文件大小：{self.file_size:,} bytes")
            self.logger.info(f"支持断点续传：{self.can_resume}")

            return True
        except RequestException as e:
            self.logger.error(f"获取文件信息失败：{e}")
            return False

    def _extract_filename(self, response: requests.Response) -> Optional[str]:
        """从响应头中提取文件名"""
        if "Content-Disposition" in response.headers:
            cd = response.headers["Content-Disposition"]
            match = re.search(r'filename[^;=\n]*=((["\']).*?\2|[^;\n]*)', cd)
            if match:
                filename = match.group(1).strip('"\'')
                return sanitize_filename(filename)
        return None

    def _initialize_download(self) -> bool:
        """初始化下载：创建目录、检查文件是否已存在、分割分块"""
        # 创建输出目录
        if not create_directory(self.output_dir):
            self.logger.error(f"无法创建输出目录：{self.output_dir}")
            return False

        # 完整文件路径
        self.file_path = os.path.join(self.output_dir, self.file_name)

        # 检查文件是否已存在且完整
        if os.path.exists(self.file_path):
            local_size = get_file_size(self.file_path)
            if self.file_size > 0 and local_size >= self.file_size:
                self.logger.warning(f"文件已存在且完整：{self.file_path}")
                if self.checksum:
                    self.logger.info(f"正在验证文件完整性...")
                    if self._verify_checksum():
                        self.logger.success("文件校验通过，无需下载")
                    else:
                        self.logger.error("文件校验失败，需要重新下载")
                        os.remove(self.file_path)
                    return False
                return False
            elif self.file_size == 0:
                # 文件大小未知，检查是否有校验和
                if self.checksum:
                    self.logger.info(f"正在验证文件完整性...")
                    if self._verify_checksum():
                        self.logger.success("文件校验通过，无需下载")
                        return False
                # 否则无法确定文件是否完整，继续下载

            # 创建临时目录
            self.temp_dir = os.path.join(self.output_dir, f".{self.file_name}.tmp")
            self.logger.error(f"无法创建临时目录：{self.temp_dir}")
            return False

        # 状态文件路径
        self.status_file = os.path.join(self.temp_dir, "status.json")

        # 分割分块（文件大小为0时不分割）
        if self.file_size > 0 and not self._split_chunks():
            self.logger.error("分块分割失败")
            return False

        return True

    def _split_chunks(self) -> bool:
        """分割文件为多个分块"""
        # 计算分块数量
        if self.file_size == 0:
            # 文件大小未知，使用单线程下载整个文件
            num_chunks = 1
            self.num_threads = 1
            self.logger.info("文件大小未知，将使用单线程下载整个文件")
        else:
            num_chunks = max(1, self.file_size // self.chunk_size)
            if self.file_size % self.chunk_size != 0:
                num_chunks += 1

            # 如果不支持断点续传或文件太小，使用单线程
            if not self.can_resume or num_chunks == 1:
                num_chunks = 1
                self.num_threads = 1

            # 调整线程数不超过分块数
            self.num_threads = min(self.num_threads, num_chunks)

            self.logger.info(f"分块数量：{num_chunks}")
            self.logger.info(f"使用线程数：{self.num_threads}")

        # 分割分块（文件大小为0时不分割）
        if self.file_size > 0:
            self.chunks = []
            for i in range(num_chunks):
                start = i * self.chunk_size
                end = min((i + 1) * self.chunk_size - 1, self.file_size - 1)
                chunk = {
                    "id": i,
                    "start": start,
                    "end": end,
                    "size": end - start + 1,
                    "downloaded": 0,
                    "file_path": os.path.join(self.temp_dir, f"chunk_{i}")
                }
                self.chunks.append(chunk)

        # 加载已下载的分块状态
        self._load_status()

        return True

    def _load_status(self) -> None:
        """从状态文件加载已下载的分块信息"""
        if os.path.exists(self.status_file):
            try:
                with open(self.status_file, "r", encoding="utf-8") as f:
                    status = json.load(f)
                    for chunk in self.chunks:
                        if str(chunk["id"]) in status:
                            chunk["downloaded"] = status[str(chunk["id"])]
                            # 验证临时文件大小是否与已下载大小一致
                            if os.path.exists(chunk["file_path"]):
                                temp_size = get_file_size(chunk["file_path"])
                                if temp_size != chunk["downloaded"]:
                                    chunk["downloaded"] = 0
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(f"加载状态文件失败：{e}")

    def _save_status(self) -> None:
        """保存已下载的分块状态到文件"""
        try:
            status = {}
            for chunk in self.chunks:
                status[str(chunk["id"])] = chunk["downloaded"]
            with open(self.status_file, "w", encoding="utf-8") as f:
                json.dump(status, f, indent=2)
        except IOError as e:
            self.logger.warning(f"保存状态文件失败：{e}")

    def _download_chunk(self, chunk: Dict) -> Tuple[bool, Dict]:
        """下载单个分块"""
        chunk_id = chunk["id"]
        start = chunk["start"]
        end = chunk["end"]
        chunk_size = chunk["size"]
        downloaded = chunk["downloaded"]
        file_path = chunk["file_path"]

        # 如果分块已完成（已知大小情况），直接返回
        if chunk_size > 0 and downloaded >= chunk_size:
            self.logger.debug(f"分块 {chunk_id} 已完成，跳过下载")
            return True, chunk

        # 设置请求头
        headers = {}
        if self.can_resume and chunk_size > 0:
            headers["Range"] = f"bytes={start + downloaded}-{end}"

        retries = 0
        while retries <= self.max_retries:
            try:
                self.logger.debug(f"开始下载分块 {chunk_id}，重试次数：{retries}")
                response = self.session.get(self.url, headers=headers, stream=True, timeout=self.timeout)
                response.raise_for_status()

                # 以追加模式打开文件
                mode = "ab" if downloaded > 0 else "wb"
                with open(file_path, mode) as f:
                    for data in response.iter_content(chunk_size=8192):
                        if data:
                            f.write(data)
                            downloaded += len(data)
                            chunk["downloaded"] = downloaded
                            # 更新进度（对于未知大小的文件，chunk_size 设为已下载大小）
                            self.progress_manager.update_chunk_progress(chunk_id, downloaded, max(chunk_size, downloaded))

                # 验证分块是否完整
                if chunk_size == 0:
                    # 文件大小未知或为0，下载完成
                    self.logger.success(f"分块 {chunk_id} 下载完成（大小未知或为0）")
                    # 更新文件大小
                    if self.file_size == 0:
                        self.file_size = downloaded
                    return True, chunk
                elif downloaded == chunk_size:
                    # 文件大小已知且下载完成
                    self.logger.success(f"分块 {chunk_id} 下载完成")
                    return True, chunk
                else:
                    self.logger.warning(f"分块 {chunk_id} 下载不完整，已下载 {downloaded}/{chunk_size}")

            except (Timeout, ConnectionError) as e:
                self.logger.warning(f"分块 {chunk_id} 下载超时/连接错误：{e}，正在重试...")
            except RequestException as e:
                status_code = e.response.status_code if hasattr(e, 'response') else None
                if status_code in [429, 500, 501, 502, 503, 504]:
                    self.logger.warning(f"分块 {chunk_id} 下载失败（状态码：{status_code}），正在重试...")
                else:
                    self.logger.error(f"分块 {chunk_id} 下载失败：{e}")
                    return False, chunk

            retries += 1
            # 指数退避
            if retries <= self.max_retries:
                import time
                time.sleep(2 ** retries)

        self.logger.error(f"分块 {chunk_id} 下载失败，已达到最大重试次数")
        return False, chunk

    def _merge_chunks(self) -> bool:
        """合并所有分块为最终文件"""
        self.logger.info("开始合并分块...")
        try:
            with open(self.file_path, "wb") as output_file:
                for chunk in self.chunks:
                    chunk_file = chunk["file_path"]
                    if not os.path.exists(chunk_file):
                        self.logger.error(f"分块文件不存在：{chunk_file}")
                        return False

                    with open(chunk_file, "rb") as f:
                        output_file.write(f.read())

            self.logger.success("分块合并完成")
            return True
        except IOError as e:
            self.logger.error(f"合并分块失败：{e}")
            return False

    def _verify_checksum(self) -> bool:
        """验证文件校验和"""
        if not self.checksum:
            return True

        try:
            self.logger.info(f"正在计算文件 {self.checksum_algorithm} 校验和...")
            file_hash = calculate_hash(self.file_path, self.checksum_algorithm)
            self.logger.debug(f"计算得到的校验和：{file_hash}")
            self.logger.debug(f"期望的校验和：{self.checksum}")

            if file_hash.lower() == self.checksum.lower():
                self.logger.success(f"文件 {self.checksum_algorithm} 校验通过")
                return True
            else:
                self.logger.error(f"文件 {self.checksum_algorithm} 校验失败")
                return False
        except Exception as e:
            self.logger.error(f"校验文件失败：{e}")
            return False

    def _cleanup(self) -> None:
        """清理临时文件和目录"""
        try:
            if self.temp_dir and os.path.exists(self.temp_dir):
                for file_name in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, file_name)
                    os.remove(file_path)
                os.rmdir(self.temp_dir)
            self.logger.debug("临时文件清理完成")
        except IOError as e:
            self.logger.warning(f"清理临时文件失败：{e}")

    def download(self) -> bool:
        """开始下载"""
        self.logger.info("开始下载任务...")

        # 获取文件信息
        if not self._get_file_info():
            return False

        # 初始化下载
        if not self._initialize_download():
            return False

        # 处理文件大小为0的情况（直接下载整个文件）
        if self.file_size == 0:
            self.logger.info("文件大小为0，直接下载整个文件")
            # 直接下载整个文件
            try:
                response = self.session.get(self.url, stream=True, timeout=self.timeout)
                response.raise_for_status()
                with open(self.file_path, 'wb') as f:
                    for data in response.iter_content(chunk_size=self.chunk_size):
                        if data:
                            f.write(data)
                self.logger.success("文件下载完成（大小为0或未知）")
                # 验证校验和
                if self.checksum and not self._verify_checksum():
                    return False
                return True
            except RequestException as e:
                self.logger.error(f"下载失败：{e}")
                return False

        # 统计已下载大小
        total_downloaded = sum(chunk["downloaded"] for chunk in self.chunks)
        if total_downloaded >= self.file_size:
            self.logger.warning("所有分块已下载完成，直接合并")
            if self._merge_chunks() and self._verify_checksum():
                self._cleanup()
                return True
            else:
                return False

        # 启动进度显示
        self.progress_manager.start(self.file_size, total_downloaded, self.chunks)

        try:
            # 下载分块
            with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
                future_to_chunk = {executor.submit(self._download_chunk, chunk): chunk for chunk in self.chunks if chunk["downloaded"] < chunk["size"]}

                for future in as_completed(future_to_chunk):
                    success, chunk = future.result()
                    if not success:
                        self.logger.error(f"分块 {chunk['id']} 下载失败，任务终止")
                        self.progress_manager.stop()
                        self._save_status()
                        return False

                    # 保存状态
                    self._save_status()

            # 停止进度显示
            self.progress_manager.stop()

            # 合并分块
            if not self._merge_chunks():
                return False

            # 验证校验和
            if not self._verify_checksum():
                return False

            # 清理临时文件
            self._cleanup()

            self.logger.success(f"文件下载完成：{self.file_path}")
            return True

        except KeyboardInterrupt:
            self.logger.warning("用户中断下载，保存断点状态...")
            self.progress_manager.stop()
            self._save_status()
            return False
        except Exception as e:
            self.logger.error(f"下载过程中发生错误：{e}")
            self.progress_manager.stop()
            self._save_status()
            return False
