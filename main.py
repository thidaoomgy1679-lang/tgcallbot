import os
import re
import asyncio
import nest_asyncio
from pyrogram import Client, filters
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    InlineQuery, InlineQueryResultPhoto, ChosenInlineResult
)
from pyrogram.errors import UserIsBlocked, PeerIdInvalid

nest_asyncio.apply()

# Environment Variables
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# ⚠️ ဒီနေရာမှာ သင့် Telegram User ID ကိန်းဂဏန်း အမှန်ထည့်ပါ (ဥပမာ: 8900371852)
OWNER_ID = 8900371852

app = Client("aura_character_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Data Stores (Database အဖြစ် Memory သုံးထားပါသည်)
cards_db = {}     # {card_id: {"photo_id": ..., "text": ...}}
users_db = set()  # {user_id1, user_id2, ...}
blocked_users = set()

# ---------------------------------------------------------
# 1. Channel ထဲသို့ Post ရောက်လာပါက အလိုအလျောက် သိမ်းဆည်းခြင်း
# ---------------------------------------------------------
@app.on_channel_post(filters.photo)
async def auto_save_card(client, message: Message):
    caption = message.caption or ""
    
    # Text ထဲမှ ID, Name, Rarity, Anime တို့ကို Extract လုပ်ခြင်း
    id_match = re.search(r"🆔\s*ID:\s*(\d+)", caption)
    name_match = re.search(r"👤\s*Name:\s*([^\n]+)", caption)
    rarity_match = re.search(r"🏷\s*Rarity:\s*([^\n]+)", caption)
    anime_match = re.search(r"🌴\s*Anime:\s*([^\n]+)", caption)

    if id_match:
        card_id = id_match.group(1).strip()
        name = name_match.group(1).strip() if name_match else "Unknown"
        rarity = rarity_match.group(1).strip() if rarity_match else "Unknown"
        anime = anime_match.group(1).strip() if anime_match else "Unknown"

        # Card Text ပြန်လည် ပုံဖော်ခြင်း
        clean_text = (
            f"👤 Name: {name}\n"
            f"🆔 ID: {card_id}\n"
            f"🏷 Rarity: {rarity}\n"
            f"🌴 Anime: {anime}"
        )

        cards_db[card_id] = {
            "photo_id": message.photo.file_id,
            "text": clean_text,
            "name": name,
            "anime": anime
        }
        print(f"✅ Saved Card ID: {card_id} - {name}")

# ---------------------------------------------------------
# 2. User Command များ (/start, /search, /check)
# ---------------------------------------------------------
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(client, message: Message):
    user = message.from_user
    users_db.add(user.id)
    if user.id in blocked_users:
        blocked_users.remove(user.id)

    # Owner ထံ သုံးစွဲသူအသစ် အကြောင်းကြားစာ ပို့ခြင်း
    if user.id != OWNER_ID:
        try:
            await client.send_message(
                OWNER_ID,
                f"🔔 **User အသစ် Bot ကို /start နှိပ်လိုက်ပါပြီ!**\n\n"
                f"👤 Name: {user.first_name} {user.last_name or ''}\n"
                f"🆔 User ID: `{user.id}`\n"
                f"🔗 Username: @{user.username if user.username else 'မရှိပါ'}"
            )
        except Exception:
            pass

    start_text = (
        "Aura Character Bot မှ ကြိုဆိုပါတယ်။\n\n"
        "/search ကိုအသုံးပြု၍ ကဒ်များအား ကြည့်ရှုပေးပါ။"
    )
    await message.reply_text(start_text)

@app.on_message(filters.command("search"))
async def search_cmd(client, message: Message):
    bot_user = await client.get_me()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Search Characters", switch_inline_query_current_chat="")]
    ])
    await message.reply_text("အောက်ပါ Button ကိုနှိပ်၍ ကဒ်များ ရှာဖွေပါ-", reply_markup=keyboard)

@app.on_message(filters.command("check"))
async def check_cmd(client, message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply_text("❌ ကျေးဇူးပြု၍ Card ID ရိုက်ထည့်ပါ (ဥပမာ - `/check 530`)")
        return

    card_id = args[1].strip()
    if card_id in cards_db:
        card = cards_db[card_id]
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 ကဒ်ဝယ်ယူရန်", url="https://t.me/NF_SPEED_1")],
            [InlineKeyboardButton("📢 Main Channel", url="https://t.me/+GKS5bRAjh9I4MWU1")]
        ])
        await message.reply_photo(
            photo=card["photo_id"],
            caption=card["text"],
            reply_markup=keyboard
        )
    else:
        await message.reply_text("❌ ရှာဖွေသော Card ID မတွေ့ရှိပါ။")

# ---------------------------------------------------------
# 3. Inline Query (မီးခိုးရောင် ခလုတ်နှိပ်၍ ပုံများ ရွေးချယ်ခြင်း)
# ---------------------------------------------------------
@app.on_inline_query()
async def inline_search(client, inline_query: InlineQuery):
    query = inline_query.query.lower().strip()
    results = []

    for card_id, card in cards_db.items():
        if not query or query in card_id or query in card["name"].lower() or query in card["anime"].lower():
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 ကဒ်ဝယ်ယူရန်", url="https://t.me/NF_SPEED_1")],
                [InlineKeyboardButton("📢 Main Channel", url="https://t.me/+GKS5bRAjh9I4MWU1")]
            ])
            results.append(
                InlineQueryResultPhoto(
                    photo_url=card["photo_id"],
                    caption=card["text"],
                    title=f"{card['name']} (ID: {card_id})",
                    description=f"Anime: {card['anime']}",
                    reply_markup=keyboard
                )
            )
            if len(results) >= 50: # Limit max inline results
                break

    await inline_query.answer(results, cache_time=1)

# ---------------------------------------------------------
# 4. Owner Commands (/stats, /broadcast)
# ---------------------------------------------------------
@app.on_message(filters.command("stats") & filters.user(OWNER_ID))
async def stats_cmd(client, message: Message):
    total = len(users_db)
    blocked = len(blocked_users)
    active = total - blocked
    
    stats_msg = (
        "📊 **Bot သုံးစွဲသူ စာရင်းအင်းများ**\n\n"
        f"👥 စုစုပေါင်း User: `{total}`\n"
        f"✅ Active Users: `{active}`\n"
        f"🚫 Block စာရင်း: `{blocked}`\n"
        f"🃏 သိမ်းဆည်းထားသော ကဒ် အရေအတွက်: `{len(cards_db)}`"
    )
    await message.reply_text(stats_msg)

@app.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def broadcast_cmd(client, message: Message):
    if not message.reply_to_message:
        await message.reply_text("❌ Broadcast ပို့လိုသော စာ/ပုံ/Video ကို Reply ပြန်၍ `/broadcast` ဟု ရိုက်ပါ")
        return

    to_broadcast = message.reply_to_message
    success = 0
    failed = 0

    status_msg = await message.reply_text("📢 Broadcast စတင် ပို့ဆောင်နေပါပြီ...")

    for user_id in list(users_db):
        try:
            await to_broadcast.copy(chat_id=user_id)
            success += 1
            await asyncio.sleep(0.05) # Rate limit
        except (UserIsBlocked, PeerIdInvalid):
            blocked_users.add(user_id)
            failed += 1
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"✅ **Broadcast ပို့ဆောင်ပြီးပါပြီ!**\n\n"
        f"🎉 အောင်မြင်သည်: `{success}`\n"
        f"❌ ကျရှုံး/Block: `{failed}`"
    )

# ---------------------------------------------------------
# 5. Menu Commands (အပြာရောင် ဘောင်လေး) တပ်ဆင်ခြင်း
# ---------------------------------------------------------
async def set_bot_commands():
    from pyrogram.types import BotCommand
    commands = [
        BotCommand("start", "Bot ကို စတင်အသုံးပြုရန်"),
        BotCommand("search", "ကဒ်များ ရှာဖွေရန်"),
        BotCommand("check", "Card ID ဖြင့် ရှာရန် (e.g. /check 530)"),
        BotCommand("stats", "Owner မနဖြေင့် Stats ကြည့်ရန်"),
        BotCommand("broadcast", "Owner မနဖြေင့် ကြော်ညာပို့ရန်")
    ]
    await app.set_bot_commands(commands)

print("Aura Character Bot စတင်အလုပ်လုပ်နေပါပြီ...")

async def main():
    await app.start()
    await set_bot_commands()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
