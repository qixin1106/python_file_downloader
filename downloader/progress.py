import time
import threading
from typing import List, Dict
from tqdm import tqdm
from colorama import Fore, Style


class ProgressManager:
    def __init__(self):
        self.stop_event = threading.Event()
        self.progress_thread = None
        self.global_progress = None
        self.chunk_progresses = None
        self.start_time = None

    def start(self, total_size: int, initial_downloaded: int, chunks: List[Dict]):
        """启动进度显示"""
        self.start_time = time.time()
        self.stop_event.clear()

        # 创建全局进度条
        if total_size > 0:
            # 文件大小已知
            self.global_progress = tqdm(
                total=total_size,
                initial=initial_downloaded,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                desc="全局进度",
                bar_format="{l_bar}%s{bar}%s{r_bar}" % (Fore.GREEN, Style.RESET_ALL)
            )
        else:
            # 文件大小未知，使用动态进度条
            self.global_progress = tqdm(
                total=1,
                initial=initial_downloaded,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                desc="全局进度",
                bar_format="{l_bar}%s{bar}%s{r_bar}" % (Fore.GREEN, Style.RESET_ALL)
            )

        # 创建分块进度字典
        self.chunk_progresses = {}
        for chunk in chunks:
            self.chunk_progresses[chunk['id']] = {
                'downloaded': chunk['downloaded'],
                'size': chunk['size'],
                'last_downloaded': chunk['downloaded'],
                'last_time': time.time()
            }

        # 启动进度更新线程
        self.progress_thread = threading.Thread(target=self._update_progress, daemon=True)
        self.progress_thread.start()

    def stop(self):
        """停止进度显示"""
        self.stop_event.set()
        if self.progress_thread and self.progress_thread.is_alive():
            self.progress_thread.join(timeout=1)
        if self.global_progress:
            self.global_progress.close()

    def update_chunk_progress(self, chunk_id: int, downloaded: int, size: int):
        """更新分块进度"""
        if chunk_id in self.chunk_progresses:
            self.chunk_progresses[chunk_id].update({
                'downloaded': downloaded,
                'size': size
            })

    def _update_progress(self):
        """更新进度的线程函数"""
        while not self.stop_event.is_set():
            # 更新全局进度
            if self.global_progress is not None:
                total_downloaded = sum(p['downloaded'] for p in self.chunk_progresses.values())
                self.global_progress.n = total_downloaded
                
                # 如果文件大小未知，动态更新总大小
                if self.global_progress.total is None or self.global_progress.total <= total_downloaded:
                    self.global_progress.total = total_downloaded + 1
                
                self.global_progress.refresh()

            # 更新分块进度详情
            self._print_chunk_details()

            # 每秒刷新一次
            time.sleep(1)

    def _print_chunk_details(self):
        """打印分块进度详情"""
        # 清除当前行
        print("\033[K", end="")
        print("分块进度详情:", end="")

        # 计算每个分块的瞬时速度
        current_time = time.time()
        for chunk_id, progress in self.chunk_progresses.items():
            downloaded = progress['downloaded']
            size = progress['size']
            last_downloaded = progress['last_downloaded']
            last_time = progress['last_time']

            # 计算瞬时速度 (bytes/s)
            time_diff = current_time - last_time
            if time_diff > 0:
                speed = (downloaded - last_downloaded) / time_diff
                speed_str = self._format_speed(speed)
            else:
                speed_str = "0 B/s"

            # 更新上次下载量和时间
            progress['last_downloaded'] = downloaded
            progress['last_time'] = current_time

            # 计算进度百分比
            if size > 0:
                percentage = (downloaded / size) * 100
            else:
                percentage = 100

            # 显示分块进度
            status = f" #{chunk_id}: {percentage:.1f}% ({self._format_size(downloaded)}/{self._format_size(size)}) {speed_str}"
            print(status, end="")

        # 光标回到行首
        print("\r", end="", flush=True)

    @staticmethod
    def _format_size(size: int) -> str:
        """格式化文件大小"""
        if size == 0:
            return "0 B"
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        i = 0
        while size >= 1024 and i < len(units) - 1:
            size /= 1024
            i += 1
        return f"{size:.1f} {units[i]}"

    @staticmethod
    def _format_speed(speed: float) -> str:
        """格式化速度"""
        if speed == 0:
            return "0 B/s"
        units = ['B/s', 'KB/s', 'MB/s', 'GB/s']
        i = 0
        while speed >= 1024 and i < len(units) - 1:
            speed /= 1024
            i += 1
        return f"{speed:.1f} {units[i]}"

    def get_remaining_time(self, total_size: int, downloaded: int) -> str:
        """计算剩余时间"""
        if downloaded == 0 or total_size == 0:
            return "--:--:--"

        elapsed_time = time.time() - self.start_time
        speed = downloaded / elapsed_time
        remaining_size = total_size - downloaded

        if speed == 0:
            return "--:--:--"

        remaining_seconds = int(remaining_size / speed)
        hours, remainder = divmod(remaining_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}" 
