import logging
import asyncio
import os
import time
import re
import subprocess
import math
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.helper_funcs.display_progress import TimeFormatter
from bot.localisation import Localisation
from bot import (
    FINISHED_PROGRESS_STR,
    UN_FINISHED_PROGRESS_STR,
    DOWNLOAD_LOCATION,
    crf,
    resolution,
    audio_b,
    preset,
    codec,
    watermark,
    pid_list
)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
LOGGER = logging.getLogger(__name__)

def sanitize_filename(filename):
    """Sanitize file names by replacing special characters and spaces."""
    return re.sub(r'[^\w\-_.]', '_', filename)

async def convert_video(video_file, output_directory, total_time, bot, message, chan_msg):
    """Convert video using FFmpeg."""
    try:
        filename = os.path.basename(video_file)
        extension = filename.split(".")[-1]
        out_name = sanitize_filename(filename.replace(f".{extension}", "[Encoded].mkv"))

        progress = os.path.join(output_directory, "progress.txt")
        with open(progress, 'w') as f:
            pass

        safe_resolution = resolution[0].replace("×", "x")
        LOGGER.info(f"Using resolution: {safe_resolution}")

        ffmpeg_command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "info",
            "-progress", progress,
            "-i", video_file,
            "-c:v", codec[0],
            "-crf", crf[0],
            "-s", safe_resolution,
            "-preset", preset[0],
            "-c:a", "libopus",
            "-b:a", audio_b[0],
            "-y",
            os.path.join(output_directory, out_name)
        ]

        LOGGER.info(f"Starting FFmpeg command: {' '.join(ffmpeg_command)}")

        process = await asyncio.create_subprocess_exec(
            *ffmpeg_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        pid_list.insert(0, process.pid)
        LOGGER.info(f"FFmpeg process started with PID: {process.pid}")

        # Monitor progress
        while True:
            if process.poll() is not None:
                break
            await asyncio.sleep(3)

            if os.path.exists(progress):
                with open(progress, 'r') as f:
                    text = f.read()
                    frame = re.findall("frame=(\d+)", text)
                    time_in_us = re.findall("out_time_ms=(\d+)", text)
                    speed = re.findall("speed=(\d+\.?\d*)", text)

                    if frame and time_in_us and speed:
                        elapsed_time = int(time_in_us[-1]) / 1_000_000
                        percentage = min(100, math.floor(elapsed_time * 100 / total_time))

                        progress_str = f"📈 <b>Progress:</b> {percentage}%\n" \
                                       f"[{FINISHED_PROGRESS_STR * (percentage // 10)}{UN_FINISHED_PROGRESS_STR * (10 - percentage // 10)}]"
                        stats = f"<blockquote>🗳 <b>Encoding in Progress</b>\n\n" \
                                f"⌚ <b>Time Left:</b> {TimeFormatter((total_time - elapsed_time) * 1000)}\n\n" \
                                f"{progress_str}\n</blockquote>"

                        try:
                            await message.edit_text(
                                text=stats,
                                reply_markup=InlineKeyboardMarkup(
                                    [[InlineKeyboardButton('❌ Cancel ❌', callback_data='fuckingdo')]]
                                )
                            )
                        except Exception as e:
                            LOGGER.error(f"Error updating progress: {e}")

        stdout, stderr = await process.communicate()
        LOGGER.info(f"FFmpeg stdout: {stdout.decode().strip()}")
        LOGGER.info(f"FFmpeg stderr: {stderr.decode().strip()}")

        if process.returncode != 0:
            LOGGER.error(f"FFmpeg failed with return code {process.returncode}")
            return None

        output_file = os.path.join(output_directory, out_name)
        return output_file if os.path.exists(output_file) else None

    except Exception as e:
        LOGGER.error(f"Error in convert_video: {e}")
        return None

async def media_info(saved_file_path):
    """Get media information using FFmpeg."""
    process = subprocess.Popen(
        [
            'ffmpeg',
            "-hide_banner",
            '-i',
            saved_file_path
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    stdout, _ = process.communicate()
    output = stdout.decode().strip()
    duration = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", output)
    bitrate = re.search(r"bitrate:\s*(\d+)", output)

    if duration:
        hours = int(duration.group(1))
        minutes = int(duration.group(2))
        seconds = math.floor(float(duration.group(3)))
        total_seconds = (hours * 3600) + (minutes * 60) + seconds
    else:
        total_seconds = None

    return total_seconds, bitrate.group(1) if bitrate else None

async def take_screen_shot(video_file, output_directory, ttl):
    """Take a screenshot from the video."""
    output_file = os.path.join(output_directory, str(time.time()) + ".jpg")

    if video_file.upper().endswith(("MKV", "MP4", "WEBM")):
        cmd = [
            "ffmpeg",
            "-ss", str(ttl),
            "-i", video_file,
            "-vframes", "1",
            output_file
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.communicate()

    return output_file if os.path.exists(output_file) else None