import os as _os
import sys as _sys
import tempfile as _tempfile
from pathlib import Path as _Path

from loguru import logger

from app.core.runtime.paths import _executable_dir

_program_dir = _executable_dir()

use_multiprocessing_queue = not (getattr(_sys, "frozen", False) and _sys.platform == "darwin")


def _resolve_log_dir() -> _Path | None:
    """Pick the first writable log directory so a locked program dir cannot kill startup."""
    candidates = [_program_dir / "logs"]
    appdata = _os.environ.get("APPDATA")
    if appdata:
        candidates.append(_Path(appdata) / "StreamCap" / "logs")
    candidates.append(_Path(_tempfile.gettempdir()) / "StreamCap_logs")
    for candidate in candidates:
        try:
            _os.makedirs(candidate, exist_ok=True)
        except OSError:
            continue
        probe = candidate / ".write_test"
        try:
            with open(probe, "w", encoding="utf-8") as file:
                file.write("ok")
            _os.remove(probe)
        except OSError:
            continue
        return candidate
    return None


def _add_sink(path: str, **kwargs) -> None:
    """Add a loguru sink, degrading to a synchronous sink when the queue is unavailable.

    A restricted token (for example an image marked with a low integrity label, or a
    process running under a security sandbox) cannot create the named pipe that
    loguru's ``enqueue=True`` needs, which used to abort the whole application with
    ``PermissionError: [WinError 5]`` while importing this module.
    """
    enqueue = bool(kwargs.get("enqueue"))
    attempts = [enqueue, False] if enqueue else [False]
    for enabled in attempts:
        try:
            logger.add(path, **{**kwargs, "enqueue": enabled})
            return
        except Exception:
            continue
    print(f"[logger] file logging disabled, cannot open {path}", file=_sys.stderr)


log_dir = _resolve_log_dir()

if log_dir is not None:
    logger.level("STREAM", no=22, color="<blue>")
    _add_sink(
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
    _add_sink(
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
else:
    print("[logger] no writable log directory, file logging disabled", file=_sys.stderr)
