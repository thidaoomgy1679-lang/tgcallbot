import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

# Environment variables များ ယူခြင်း
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# API_ID ကို int (ကိန်းဂဏန်း) အဖြစ် အတိအကျ ပြောင်းခြင်း
if API_ID:
    API_ID = int(API_ID)

app = Client("tag_all_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_message(filters.command(["tagall", "all"]) & filters.group)
async def tag_all_members(client, message: Message):
    user = await client.get_chat_member(message.chat.id, message.from_user.id)
    if user.status not in ["administrator", "owner"]:
        await message.reply_text("❌ ဒီ Command ကို Admin များသာ သုံးနိုင်ပါတယ်။")
        return

    text = message.text.split(maxsplit=1)
    custom_msg = text[1] if len(text) > 1 else "📢 အားလုံးကို Tag တွဲခေါ်လိုက်ပါတယ်။"

    usr_mentions = []
    async for member in client.get_chat_members(message.chat.id):
        if member.user.is_bot:
            continue
        usr_mentions.append(f"[{member.user.first_name}](tg://user?id={member.user.id})")
        
        if len(usr_mentions) == 5:
            msg = f"{custom_msg}\n\n" + " ".join(usr_mentions)
            await client.send_message(message.chat.id, msg)
            usr_mentions = []
            await asyncio.sleep(2)

    if usr_mentions:
        msg = f"{custom_msg}\n\n" + " ".join(usr_mentions)
        await client.send_message(message.chat.id, msg)

print("Bot စတင်အလုပ်လုပ်နေပါပြီ...")
app.run()
