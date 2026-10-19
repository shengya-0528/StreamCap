import os as _os
import sys as _sys

from loguru import logger

from app.core.runtime.paths import user_data_dir

log_dir = _os.path.join(user_data_dir, "logs")

if getattr(_sys, "frozen", False) and _sys.platform == "win32" and not _os.path.exists(log_dir):
    try:
        _os.makedirs(log_dir, exist_ok=True)
    except PermissionError:
        # 打包运行时若 AppData 无写权限，改用 TEMP 目录
        temp_log_dir = _os.path.join(_os.environ.get("TEMP", _os.path.expanduser("~")), "StreamCap_logs")
        _os.makedirs(temp_log_dir, exist_ok=True)
        logger.add(
            _os.path.join(temp_log_dir, "streamget.log"),
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            filter=lambda i: i["level"].name != "STREAM",
            serialize=False,
            enqueue=use_multiprocessing_queue,
            retention=3,
            rotation="3 MB",
            encoding="utf-8",
        )
use_multiprocessing_queue = not (getattr(_sys, "frozen", False) and _sys.platform == "darwin")
logger.add(
    _os.path.join(log_dir, "streamget.log"),
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    filter=lambda i: i["level"].name != "STREAM",
    serialize=False,
    enqueue=use_multiprocessing_queue,
    retention=3,
    rotation="3 MB",
    encoding="utf-8",
)

logger.level("STREAM", no=22, color="<blue>")
logger.add(
    _os.path.join(log_dir, "play_url.log"),
    level="STREAM",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {message}",
    filter=lambda i: i["level"].name == "STREAM",
    serialize=False,
    enqueue=use_multiprocessing_queue,
    retention=1,
    rotation="500 KB",
    encoding="utf-8",
)
