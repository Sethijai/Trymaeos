import datetime
import logging
import os
import time
import asyncio
import json
from PIL import Image
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.localisation import Localisation
from bot import (
    DOWNLOAD_LOCATION, 
    AUTH_USERS,
    DUMP_CHANNEL,
    app  
)
from bot.helper_funcs.ffmpeg import (
    convert_video,
    media_info,
    take_screen_shot
)
from bot.helper_funcs.display_progress import (
    progress_for_pyrogram,
    TimeFormatter,
    humanbytes
)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
LOGGER = logging.getLogger(__name__)

CURRENT_PROCESSES = {}
CHAT_FLOOD = {}
broadcast_ids = {}
bot = app        

async def incoming_start_message_f(bot, update):
    await bot.send_message(
        chat_id=update.chat.id,
        text=Localisation.START_TEXT,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton('Channel', url='tg://settings/Hacked')
                ]
            ]
        ),
        reply_to_message_id=update.id,
    )
    
os.system("wget https://files.catbox.moe/9pj9jf.jpg -O thumb.jpg")
    
async def incoming_compress_message_f(update):
    isAuto = True
    d_start = time.time()
    sent_message = await bot.send_message(
        chat_id=update.chat.id,
        text=Localisation.DOWNLOAD_START,
        reply_to_message_id=update.id
    )
    
    try:
        d_start = time.time()
        status = DOWNLOAD_LOCATION + "/status.json"
        with open(status, 'w') as f:
            statusMsg = {
                'running': True,
                'message': sent_message.id
            }
            json.dump(statusMsg, f, indent=2)
        video = await bot.download_media(
            message=update,  
            progress=progress_for_pyrogram,
            progress_args=(
                bot,
                Localisation.DOWNLOAD_START,
                sent_message,
                d_start
            )
        )
        saved_file_path = video
        LOGGER.info(saved_file_path)  
        LOGGER.info(video)
        if video is None:
            try:
                await sent_message.edit_text(
                    text="Download stopped"
                )
            except:
                pass
            return
    except (ValueError) as e:
        try:
            await sent_message.edit_text(
                text=str(e)
            )
        except:
            pass

    try:
        await sent_message.edit_text(                
            text=Localisation.SAVED_RECVD_DOC_FILE                
        )
    except:
        pass

    if os.path.exists(saved_file_path):
        downloaded_time = TimeFormatter((time.time() - d_start)*1000)
        duration, bitrate = await media_info(saved_file_path)
        if duration is None or bitrate is None:
            try:
                await sent_message.edit_text(                
                    text="<blockquote>⚠️ Getting video meta data failed ⚠️</blockquote>"                
                )
            except:
                pass
            return

        await sent_message.edit_text(                    
            text=Localisation.COMPRESS_START                    
        )
        c_start = time.time()

        o = await convert_video(
               video, 
               DOWNLOAD_LOCATION, 
               duration, 
               bot, 
               sent_message,
               None  # Assuming `chan_msg` is the missing argument, replace with the correct variable if different.
             )

        compressed_time = TimeFormatter((time.time() - c_start)*1000)
        LOGGER.info(o)
        if o == 'stopped':
            return
        if o is not None:

            # Generate thumbnail of the converted video
            thumb_image_path = await take_screen_shot(
                o,  # Path to the converted video
                os.path.dirname(os.path.abspath(o)),
                5  # Capture at 5 seconds
            )

            await sent_message.edit_text(                    
                text=Localisation.UPLOAD_START,                    
            )
            u_start = time.time()
            
            # Extract the file name without extension
            file_name = os.path.basename(o)  # Gets the full file name
            file_name_without_extension = f"<blockquote>{os.path.splitext(file_name)[0]}</blockquote>" # Removes the file extension
            upload = await bot.send_video(
                chat_id=update.chat.id,
                video=o,
                caption=file_name_without_extension,  # Use the file name as the caption
                duration=duration,
                thumb="thumb.jpg",
                #thumb=thumb_image_path,
                width=1280,  # Set the width of the video
                height=720,  # Set the height of the video
                reply_to_message_id=update.id,
                progress=progress_for_pyrogram,
                progress_args=(
                    bot,
                    Localisation.UPLOAD_START,
                    sent_message,
                    u_start
                )
            )
            
            if upload is None:
                try:
                    await sent_message.edit_text(
                        text="Upload stopped"
                    )
                except:
                    pass
                return
            
            uploaded_time = TimeFormatter((time.time() - u_start)*1000)
            await sent_message.delete()

            # Forward the original video to the dump channel and reply with "Original Video"
            original_video = await bot.forward_messages(
                chat_id=DUMP_CHANNEL,
                from_chat_id=update.chat.id,
                message_ids=update.id
            )
            if original_video:
                await bot.send_message(
                    chat_id=DUMP_CHANNEL,
                    text="Original Video",
                    reply_to_message_id=original_video.id
                )

            # Forward the converted video to the dump channel and reply with "Converted Video"
            converted_video = await bot.forward_messages(
                chat_id=DUMP_CHANNEL,
                from_chat_id=upload.chat.id,
                message_ids=upload.id
            )
            if converted_video:
                await bot.send_message(
                    chat_id=DUMP_CHANNEL,
                    text="Converted Video",
                    reply_to_message_id=converted_video.id
                )
            
            try:
                await upload.edit_caption(
                    caption=file_name_without_extension  # Keep the file name as the caption
                )
            except:
                pass
        else:
            try:
                await sent_message.edit_text(                    
                    text="<blockquote>⚠️ Compression failed ⚠️</blockquote>"               
                )
            except:
                pass
    else:
        try:
            await sent_message.edit_text(                    
                text="<blockquote>⚠️ Failed Downloaded path not exist ⚠️</blockquote>"               
            )
        except:
            pass
    
async def incoming_cancel_message_f(bot, update):
    if update.from_user.id not in AUTH_USERS:      
        try:
            await update.message.delete()
        except:
            pass
        return

    status = DOWNLOAD_LOCATION + "/status.json"
    if os.path.exists(status):
        # Read the status to check if there's an ongoing process
        with open(status, 'r') as f:
            statusMsg = json.load(f)
        
        if statusMsg.get('running', False):
            inline_keyboard = []
            ikeyboard = []
            ikeyboard.append(InlineKeyboardButton("Yes 🚫", callback_data=("fuckingdo").encode("UTF-8")))
            ikeyboard.append(InlineKeyboardButton("No 🤗", callback_data=("fuckoff").encode("UTF-8")))
            inline_keyboard.append(ikeyboard)
            reply_markup = InlineKeyboardMarkup(inline_keyboard)
            await update.reply_text("Are you sure? 🚫 This will stop the compression!", reply_markup=reply_markup, quote=True)
        else:
            await bot.send_message(
                chat_id=update.chat.id,
                text="No active compression exists",
                reply_to_message_id=update.id
            )
    else:
        await bot.send_message(
            chat_id=update.chat.id,
            text="No active compression exists",
            reply_to_message_id=update.id
        )
