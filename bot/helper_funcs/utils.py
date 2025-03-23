import logging
import os
import asyncio
from pyrogram.types import Message
from bot import data
from bot.plugins.incoming_message_fn import incoming_compress_message_f

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
LOGGER = logging.getLogger(__name__)

async def add_task(message: Message):
    """Add task to queue."""
    try:
        os.system('rm -rf /app/downloads/*')
        await incoming_compress_message_f(message)
    except Exception as e:
        LOGGER.error(f"Error in add_task: {e}")
    await on_task_complete()

async def on_task_complete():
    """Move to the next task in the queue."""
    try:
        if data:
            del data[0]
        if data:
            await add_task(data[0])
    except Exception as e:
        LOGGER.error(f"Error in on_task_complete: {e}")
