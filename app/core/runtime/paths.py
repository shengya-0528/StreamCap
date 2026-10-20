import os
import shutil
import sys
from pathlib import Path

APP_NAME = "StreamCap"
EXECUTABLE_SUFFIX = ".exe" if sys.platform == "win32" else ""


def _executable_dir() -> Path:
    executable = sys.executable if getattr(sys, "frozen", False) else sys.argv[0]
    return Path(executable).resolve().parent


def _macos_bundle_contents_dir(executable_dir: Path) -> Path | None:
    contents_dir = executable_dir.parent
    app_dir = contents_dir.parent
    if (
        getattr(sys, "frozen", False)
        and sys.platform == "darwin"
        and executable_dir.name == "MacOS"
        and contents_dir.name == "Contents"
        and app_dir.suffix == ".app"
    ):
        return contents_dir
    return None


_EXECUTABLE_DIR = _executable_dir()
_CONTENTS_DIR = _macos_bundle_contents_dir(_EXECUTABLE_DIR)

if _CONTENTS_DIR is not None:
    resource_dir = _CONTENTS_DIR / "Resources"
    user_data_dir = Path.home() / "Library" / "Application Support" / APP_NAME
elif getattr(sys, "frozen", False) and sys.platform == "win32":
    internal_dir = _EXECUTABLE_DIR / "_internal"
    resource_dir = internal_dir if internal_dir.is_dir() else _EXECUTABLE_DIR
    user_data_dir = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / APP_NAME
else:
    resource_dir = _EXECUTABLE_DIR
    user_data_dir = _EXECUTABLE_DIR

if getattr(sys, "frozen", False) and sys.platform == "win32":
    default_recordings_dir = _EXECUTABLE_DIR / "downloads"
else:
    default_recordings_dir = user_data_dir / "downloads"


def _copy_missing_tree(source: Path, target: Path) -> None:
    """Copy bundled defaults into the user data directory without touching existing files.

    ``shutil.copytree(..., dirs_exist_ok=True)`` used to overwrite the user's own
    ``user_settings.json`` on every launch, which made every change look unsaved.
    Only files that are still missing are seeded from the bundle now.
    """
    if not source.is_dir():
        return
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError:
        return
    for item in source.iterdir():
        destination = target / item.name
        if item.is_dir():
            _copy_missing_tree(item, destination)
            continue
        if destination.exists():
            continue
        try:
            shutil.copy2(item, destination)
        except OSError:
            # A read-only or locked leftover must never abort startup.
            continue


def prepare_user_data_dir() -> None:
    """Seed the writable user data directory with bundled defaults (existing files win)."""
    try:
        user_data_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return
    if user_data_dir == resource_dir:
        return

    for directory in ("config", "locales"):
        _copy_missing_tree(resource_dir / directory, user_data_dir / directory)

    prepare_bundled_ffmpeg()
    prepare_bundled_node()


def prepare_bundled_ffmpeg() -> None:
    # ffmpeg 打包后在 _EXECUTABLE_DIR 同级目录，不是在 resource_dir(_internal) 下
    # FFmpeg 已从 7z 解压到 _EXECUTABLE_DIR/ffmpeg-2026-10-19-git-2344518cc5-essentials_build/
    source_executable = _EXECUTABLE_DIR / "ffmpeg-2026-10-19-git-2344518cc5-essentials_build" / "bin" / f"ffmpeg{EXECUTABLE_SUFFIX}"
    if not source_executable.is_file():
        source_executable = resource_dir / "ffmpeg" / f"ffmpeg{EXECUTABLE_SUFFIX}"
    target_dir = user_data_dir / "ffmpeg"
    target_executable = target_dir / f"ffmpeg{EXECUTABLE_SUFFIX}"
    if not source_executable.is_file() or target_executable.exists():
        return
    if shutil.which("ffmpeg"):
        return

    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_executable, target_executable)
    if sys.platform != "win32":
        target_executable.chmod(target_executable.stat().st_mode | 0o755)


def prepare_bundled_node() -> None:
    # node 打包后在 _EXECUTABLE_DIR 同级目录
    source_executable = _EXECUTABLE_DIR / "node" / f"node{EXECUTABLE_SUFFIX}"
    if not source_executable.is_file():
        source_executable = resource_dir / "node" / f"node{EXECUTABLE_SUFFIX}"
    target_dir = user_data_dir / "node"
    target_executable = target_dir / f"node{EXECUTABLE_SUFFIX}"
    if not source_executable.is_file() or target_executable.exists():
        return
    if shutil.which("node"):
        return

    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_executable, target_executable)
    if sys.platform != "win32":
        target_executable.chmod(target_executable.stat().st_mode | 0o755)


def prepend_user_bin_dirs() -> None:
    for directory in (user_data_dir / "ffmpeg", user_data_dir / "node"):
        if directory.is_dir():
            os.environ["PATH"] = str(directory) + os.pathsep + os.environ.get("PATH", "")
