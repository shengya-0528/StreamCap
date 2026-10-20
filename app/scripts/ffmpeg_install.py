import asyncio
import os
import platform
import re
import subprocess
import zipfile
from pathlib import Path

import httpx

from ..core.runtime.paths import EXECUTABLE_SUFFIX, resource_dir, user_data_dir
from ..utils.logger import logger
from ..utils.utils import get_startup_info

current_platform = platform.system()
execute_dir = str(user_data_dir)
ffmpeg_path = os.path.join(execute_dir, "ffmpeg")
startupinfo = get_startup_info()


async def unzip_file(zip_path: str | Path, extract_to: str | Path, delete: bool = True) -> None:
    if not os.path.exists(extract_to):
        os.makedirs(extract_to, exist_ok=True)

    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, _sync_unzip, zip_path, extract_to)
        logger.debug(f"Compressed file decompression completed: {zip_path}")
    except Exception as e:
        logger.error(f"Failed to decompress the compressed file: {e}")
        raise Exception("Failed to decompress the compressed file")

    if delete and os.path.exists(zip_path):
        os.remove(zip_path)


def _sync_unzip(zip_path: str | Path, extract_to: str | Path) -> None:
    if not zipfile.is_zipfile(zip_path):
        os.remove(zip_path)
        logger.error(f"The file is not a valid ZIP file: {zip_path}")
        raise ValueError("The file is not a valid ZIP file")

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)


async def get_lanzou_download_link(url: str, password: str | None = None, headers: dict | None = None) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url, headers=headers)
            html_str = response.text
            sign = re.search("var \\w+ = '([A-Za-z0-9_\\-+/]{80,})';", html_str).group(1)

            data = {
                "action": "downprocess",
                "p": password,
                "sign": sign,
                "kd": "1",
            }

            response = await client.post(
                "https://wweb.lanzoum.com/ajaxm.php?file=219989236", headers=headers, data=data
            )
            json_data = response.json()
            download_url = json_data["dom"] + "/file/" + json_data["url"]
            response = await client.get(download_url, headers=headers, follow_redirects=True)
            return str(response.url)
    except Exception as e:
        logger.error(f"Failed to obtain ffmpeg download address. {e}")


async def install_ffmpeg_windows(update_progress):
    try:
        logger.warning("ffmpeg is not installed.")
        logger.debug("Installing the latest version of ffmpeg for Windows...")
        await update_progress(0.1, "Get FFmpeg installation resources")
        headers = {
            "content-type": "application/x-www-form-urlencoded",
            "accept-language": "zh-CN,zh;q=0.9",
            "origin": "https://wweb.lanzoum.com",
            "referer": "https://wweb.lanzoum.com/iHAc22ly3r3g",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
            " Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
            "x-requested-with": "XMLHttpRequest",
        }
        ffmpeg_url = await get_lanzou_download_link("https://wweb.lanzoum.com/iHAc22ly3r3g", "eots", headers)
        if ffmpeg_url:
            full_file_name = "ffmpeg_latest_build_20250124.zip"
            version = "v20250124"
            zip_file_path = Path(execute_dir) / full_file_name
            if Path(zip_file_path).exists():
                await update_progress(0.8, "FFmpeg installation file already exists")
                logger.debug("ffmpeg installation file already exists, start install...")
            else:
                await update_progress(0.2, "Start downloading FFmpeg installation package")
                logger.debug(f"FFmpeg Download ({version}): {ffmpeg_url}")
                async with (
                    httpx.AsyncClient(follow_redirects=True) as client,
                    client.stream("GET", ffmpeg_url, headers=headers) as resp,
                ):
                    total_size = int(resp.headers.get("Content-Length", 0))
                    if resp.status_code != 200 and total_size != 0:
                        logger.error("FFmpeg package resources cannot be accessed")
                        raise Exception("The resource address cannot be accessed")

                    downloaded = 0
                    with open(zip_file_path, "wb") as f:
                        async for chunk in resp.aiter_bytes():
                            f.write(chunk)
                            downloaded += len(chunk)

                            progress = 0.2 + 0.6 * (downloaded / total_size)
                            await update_progress(
                                round(progress, 2), f"Downloading... {downloaded // 1024}KB/{total_size // 1024}KB"
                            )

            await update_progress(0.8, "Extracting and cleaning installation files")
            await unzip_file(zip_file_path, execute_dir)
            await update_progress(0.9, "Configuring FFmpeg environment variables")
            os.environ["PATH"] = ffmpeg_path + os.pathsep + os.environ.get("PATH")
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, startupinfo=startupinfo)
            if result.returncode == 0:
                logger.success("FFmpeg installation was successful")
                return True
            else:
                logger.error("ffmpeg installation failed. Please manually install ffmpeg by yourself")
                raise Exception("Please restart the program")
        else:
            logger.error("Please manually install ffmpeg by yourself")
            raise Exception("Failed to obtain the FFmpeg download address")
    except Exception as e:
        raise RuntimeError(f"FFmpeg install failed, {e}") from None


async def install_ffmpeg_mac(update_progress):
    logger.warning("FFmpeg is not installed.")
    logger.debug("Installing the stable version of ffmpeg for macOS...")
    await update_progress(0.1, "Get FFmpeg installation resources")
    await asyncio.sleep(2)
    await update_progress(0.3, "Please be patient and wait...")
    timeout = 300
    try:
        result = subprocess.run(
            ["brew", "install", "ffmpeg"], capture_output=True, startupinfo=startupinfo, timeout=timeout
        )
        if result.returncode == 0:
            logger.success("FFmpeg installation was successful. Restart for changes to take effect.")
            return True
        else:
            logger.error("FFmpeg installation failed")
            raise Exception("Please manually install FFmpeg by yourself")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install ffmpeg using Homebrew. {e}")
        logger.error("Please install ffmpeg manually or check your Homebrew installation.")
        raise Exception("Please check if Homebrew has been installed") from None
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise Exception(e) from None


async def install_ffmpeg_linux(update_progress):
    is_rhs = True
    timeout = 180

    try:
        logger.warning("ffmpeg is not installed.")
        logger.debug("Trying to install the stable version of ffmpeg")
        await update_progress(0.1, "Get FFmpeg installation resources")
        try:
            result = subprocess.run(
                ["yum", "-y", "update"], capture_output=True, startupinfo=startupinfo, timeout=timeout
            )
            if result.returncode != 0:
                logger.error("Failed to update package lists using yum.")
                return False

            result = subprocess.run(
                ["yum", "install", "-y", "ffmpeg"], capture_output=True, startupinfo=startupinfo, timeout=timeout
            )
            if result.returncode == 0:
                logger.success("ffmpeg installation was successful using yum. Restart for changes to take effect.")
                return True
            logger.error(result.stderr.decode("utf-8").strip())
        except subprocess.TimeoutExpired:
            logger.error("Command execution timed out. Please try to manually install ffmpeg.")
            raise Exception("Command execution timed out after {} seconds".format(timeout))
    except FileNotFoundError:
        logger.error("yum command not found, trying to install using apt...")
        is_rhs = False
    except Exception as e:
        logger.error(f"An error occurred while trying to install ffmpeg using yum: {e}")

    if not is_rhs:
        try:
            logger.debug("Trying to install the stable version of ffmpeg for Linux using apt...")
            try:
                result = subprocess.run(
                    ["apt", "update"], capture_output=True, startupinfo=startupinfo, timeout=timeout
                )
                if result.returncode != 0:
                    logger.error("Failed to update package lists using apt")
                    return False

                result = subprocess.run(
                    ["apt", "install", "-y", "ffmpeg"], capture_output=True, startupinfo=startupinfo, timeout=timeout
                )
                if result.returncode == 0:
                    logger.success("ffmpeg installation was successful using apt. Restart for changes to take effect.")
                    return True
                else:
                    logger.error(result.stderr.decode("utf-8").strip())
            except subprocess.TimeoutExpired:
                logger.error("Command execution timed out. Please try to manually install ffmpeg.")
                raise Exception("Command execution timed out after {} seconds".format(timeout))
        except FileNotFoundError:
            logger.error("apt command not found, unable to install ffmpeg. Please manually install ffmpeg by yourself")
        except Exception as e:
            logger.error(f"An error occurred while trying to install ffmpeg using apt: {e}")
    logger.error("Manual installation of ffmpeg is required. Please manually install ffmpeg by yourself.")
    raise Exception("Please manually install FFmpeg by yourself")


async def install_ffmpeg(update_progress) -> bool:
    if current_platform == "Windows":
        return await install_ffmpeg_windows(update_progress)
    elif current_platform == "Linux":
        return await install_ffmpeg_linux(update_progress)
    elif current_platform == "Darwin":
        return await install_ffmpeg_mac(update_progress)
    else:
        logger.warning(
            f"ffmpeg auto installation is not supported on this platform: {current_platform}. Please "
            f"install ffmpeg manually."
        )
    return False


def update_env_path():
    current_env_path = os.environ.get("PATH")
    if current_platform != "Windows":
        path_list = ["/usr/bin/", "/usr/local/bin", "/opt/homebrew/bin"]
        current_env_path_list = current_env_path.split(os.pathsep)
        env_path = [path for path in path_list if path not in set(current_env_path_list)]
        ffmpeg_env_path = os.pathsep.join([ffmpeg_path] + env_path + current_env_path_list)
    else:
        ffmpeg_env_path = ffmpeg_path + os.pathsep + current_env_path

    os.environ["PATH"] = ffmpeg_env_path


def _bundled_ffmpeg_candidates() -> list[Path]:
    """按优先级列出 ffmpeg 可执行文件：用户目录 -> 打包内置 (_internal/ffmpeg)。"""
    exe_name = f"ffmpeg{EXECUTABLE_SUFFIX}"
    candidates = [Path(ffmpeg_path) / exe_name]
    bundled = Path(resource_dir) / "ffmpeg" / exe_name
    if bundled.parent != Path(ffmpeg_path):
        candidates.append(bundled)
    return candidates


def _probe_ffmpeg(command: str) -> str | None:
    try:
        result = subprocess.run([command, "-version"], capture_output=True, startupinfo=startupinfo, text=True)
    except FileNotFoundError as e:
        logger.info(e)
        return None
    except OSError as e:
        logger.error(f"OSError occurred: {e}.")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return None
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    logger.debug((result.stderr or "").strip())
    return None


async def check_ffmpeg_installed() -> bool:
    update_env_path()
    version_info = _probe_ffmpeg("ffmpeg")
    if version_info:
        logger.info(". ".join(version_info.splitlines()[:2]))
        return True

    # PATH 里找不到时，直接探测打包内置的 ffmpeg，避免明明带了却误报「未安装」
    for candidate in _bundled_ffmpeg_candidates():
        if not candidate.is_file():
            continue
        version_info = _probe_ffmpeg(str(candidate))
        if version_info:
            os.environ["PATH"] = str(candidate.parent) + os.pathsep + os.environ.get("PATH", "")
            logger.info(f"Using bundled ffmpeg: {candidate}")
            logger.info(". ".join(version_info.splitlines()[:2]))
            return True

    logger.warning("ffmpeg is not installed.")
    return False
