import os
import asyncio
from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated

from bot import Bot
from config import ADMINS, FORCE_MSG, START_MSG, CUSTOM_CAPTION, DISABLE_CHANNEL_BUTTON, PROTECT_CONTENT
from helper_func import subscribed, encode, decode, get_messages
from database.database import add_user, del_user, full_userbase, present_user

# Auto-delete time (in seconds)
SECONDS = int(os.getenv("SECONDS", "10"))  # Default 5 minutes

@Bot.on_message(filters.command('start') & filters.private & subscribed)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    
    if not await present_user(user_id):
        try:
            await add_user(user_id)
        except Exception:
            pass
    
    text = message.text
    if len(text) > 7:
        try:
            base64_string = text.split(" ", 1)[1]
        except IndexError:
            return
        
        string = await decode(base64_string)
        argument = string.split("-")
        
        ids = []
        try:
            if len(argument) == 3:
                start = int(int(argument[1]) / abs(client.db_channel.id))
                end = int(int(argument[2]) / abs(client.db_channel.id))
                ids = list(range(start, end + 1)) if start <= end else list(range(start, end - 1, -1))
            elif len(argument) == 2:
                ids = [int(int(argument[1]) / abs(client.db_channel.id))]
        except ValueError:
            return

        temp_msg = await message.reply("ᴡᴀɪᴛ...")
        
        try:
            messages = await get_messages(client, ids)
        except Exception:
            await message.reply_text("Something went wrong..!")
            return
        
        await temp_msg.delete()

        sent_messages = []
        for msg in messages:
            caption = (CUSTOM_CAPTION.format(previouscaption=msg.caption.html if msg.caption else "", 
                                             filename=msg.document.file_name) 
                       if CUSTOM_CAPTION and msg.document else msg.caption.html if msg.caption else "")

            reply_markup = msg.reply_markup if DISABLE_CHANNEL_BUTTON else None

            try:
                snt_msg = await msg.copy(
                    chat_id=message.from_user.id,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup,
                    protect_content=PROTECT_CONTENT
                )
                await asyncio.sleep(1)
                sent_messages.append(snt_msg)
            except FloodWait as e:
                await asyncio.sleep(e.value)
                continue
            except Exception:
                continue
        
        delete_msg = await message.reply_text("<b>𝖳𝗁𝗂𝗌 𝗏𝗂𝖽𝖾𝗈 𝗂𝗌 𝖽𝖾𝗅𝖾𝗍𝖾𝖽 𝖺𝗎𝗍𝗈𝗆𝖺𝗍𝗂𝖼𝖺𝗅𝗅𝗒 𝗂𝗇 5𝗆𝗂𝗇𝗎𝗍𝖾𝗌..\n 𝖥𝗈𝗋𝗐𝖺𝗋𝖽 𝗂𝗇 𝗒𝗈𝗎𝗋 𝖲𝖺𝗏𝖾𝖽 𝖬𝖾𝗌𝗌𝖺𝗀𝖾𝗌..!!</b>")
        await asyncio.sleep(SECONDS)

        for msg in sent_messages:
            try:
                await msg.delete()
            except Exception:
                continue
        
        try:
            await delete_msg.edit_text(
                f"<b>›› 𝖯𝗋𝗂𝗏𝗂𝗈𝗎𝗌 𝗏𝗂𝖽𝖾𝗈 𝗐𝖺𝗌 𝖽𝖾𝗅𝖾𝗍𝖾𝖽. 𝖨𝖿 𝗒𝗈𝗎 𝗐𝖺𝗇𝗍 \n𝗍𝗁𝖾 𝗌𝖺𝗆𝖾 𝗏𝗂𝖽𝖾𝗈 𝖺𝗀𝖺𝗂𝗇, 𝖼𝗅𝗂𝖼𝗄 𝗈𝗇:</b>",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("📥 Get Video", url=f"https://t.me/{client.username}?start={message.command[1]}")],
                        [InlineKeyboardButton("❌ Close", callback_data="close")]
                    ]
                )
            )
        except Exception:
            pass

@Bot.on_callback_query(filters.regex("close"))
async def close_callback(client, callback_query):
    await callback_query.message.delete()

@Bot.on_message(filters.command('users') & filters.private & filters.user(ADMINS))
async def get_users(client: Bot, message: Message):
    msg = await client.send_message(chat_id=message.chat.id, text="<b>Processing ...</b>")
    users = await full_userbase()
    await msg.edit(f"{len(users)} users are using this bot")

@Bot.on_message(filters.private & filters.command('broadcast') & filters.user(ADMINS))
async def send_text(client: Bot, message: Message):
    if message.reply_to_message:
        query = await full_userbase()
        broadcast_msg = message.reply_to_message
        total, successful, blocked, deleted, unsuccessful = 0, 0, 0, 0, 0
        
        pls_wait = await message.reply("<i>Broadcasting Message... This will take some time</i>")
        
        for chat_id in query:
            try:
                await broadcast_msg.copy(chat_id)
                successful += 1
            except FloodWait as e:
                await asyncio.sleep(e.value)
                successful += 1
            except UserIsBlocked:
                await del_user(chat_id)
                blocked += 1
            except InputUserDeactivated:
                await del_user(chat_id)
                deleted += 1
            except Exception:
                unsuccessful += 1
            
            total += 1
        
        status = (
            f"<b><u>Broadcast Completed</u></b>\n\n"
            f"Total Users: <code>{total}</code>\n"
            f"Successful: <code>{successful}</code>\n"
            f"Blocked Users: <code>{blocked}</code>\n"
            f"Deleted Accounts: <code>{deleted}</code>\n"
            f"Unsuccessful: <code>{unsuccessful}</code>"
        )
        
        await pls_wait.edit(status)

    else:
        msg = await message.reply("<code>Use this command as a reply to any Telegram message.</code>")
        await asyncio.sleep(8)
        await msg.delete()
