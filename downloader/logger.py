import logging
import sys
from datetime import datetime
from colorama import Fore, Style, init

# 初始化colorama
init(autoreset=True)


class Logger:
    def __init__(self, debug: bool = False):
        self.logger = logging.getLogger("downloader")
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)

        # 移除现有的处理器，避免重复输出
        self.logger.handlers.clear()

        # 创建控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG if debug else logging.INFO)

        # 创建格式化器
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(formatter)

        # 添加处理器
        self.logger.addHandler(console_handler)

    def debug(self, message: str):
        """调试日志"""
        self.logger.debug(f"{Fore.BLUE}[DEBUG]{Style.RESET_ALL} {message}")

    def info(self, message: str):
        """普通信息日志"""
        self.logger.info(f"{Fore.WHITE}[INFO]{Style.RESET_ALL} {message}")

    def success(self, message: str):
        """成功日志"""
        self.logger.info(f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL} {message}")

    def warning(self, message: str):
        """警告日志"""
        self.logger.warning(f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL} {message}")

    def error(self, message: str):
        """错误日志"""
        self.logger.error(f"{Fore.RED}[ERROR]{Style.RESET_ALL} {message}")

    def critical(self, message: str):
        """严重错误日志"""
        self.logger.critical(f"{Fore.MAGENTA}[CRITICAL]{Style.RESET_ALL} {message}")
