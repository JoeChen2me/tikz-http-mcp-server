import os
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

IMAGES_DIR = Path("/app/images")
# 图片保留时间：1天
RETENTION_DAYS = 1

def clean_old_images():
    logger.info(f"开始清理 {IMAGES_DIR} 目录下的旧图片...")
    if not IMAGES_DIR.exists():
        logger.warning(f"图片目录 {IMAGES_DIR} 不存在，跳过清理。")
        return

    deleted_count = 0
    now = datetime.now()
    cutoff_time = now - timedelta(days=RETENTION_DAYS)

    for filepath in IMAGES_DIR.iterdir():
        if filepath.is_file() and filepath.suffix == ".png":
            try:
                # 获取文件的修改时间
                mod_timestamp = filepath.stat().st_mtime
                mod_datetime = datetime.fromtimestamp(mod_timestamp)

                if mod_datetime < cutoff_time:
                    os.remove(filepath)
                    deleted_count += 1
                    logger.info(f"已删除过期图片: {filepath}")
            except Exception as e:
                logger.error(f"处理文件 {filepath} 失败: {e}")

    logger.info(f"清理完成。共删除 {deleted_count} 张过期图片。")

if __name__ == "__main__":
    # 首次启动时立即清理一次
    clean_old_images()

    # 每隔24小时运行一次清理（86400秒）
    while True:
        time.sleep(86400)  # 24 * 60 * 60 seconds
        clean_old_images()
