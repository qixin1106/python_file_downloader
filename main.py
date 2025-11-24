from downloader import Downloader, get_config
from downloader.logger import Logger


def main():
    try:
        # 获取配置
        config = get_config()

        # 创建下载器
        downloader = Downloader(
            url=config["url"],
            output_dir=config["output_dir"],
            num_threads=config["num_threads"],
            chunk_size=config["chunk_size"],
            max_retries=config["max_retries"],
            timeout=config["timeout"],
            checksum=config["checksum"],
            checksum_algorithm=config["checksum_algorithm"],
            debug=config["debug"]
        )

        # 开始下载
        success = downloader.download()

        if success:
            print("\n下载成功！")
            return 0
        else:
            print("\n下载失败！")
            return 1

    except KeyboardInterrupt:
        print("\n用户中断程序")
        return 1
    except ValueError as e:
        print(f"参数错误：{e}")
        return 1
    except Exception as e:
        print(f"程序运行错误：{e}")
        return 1


if __name__ == "__main__":
    exit(main())
