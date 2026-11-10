import html
import logging
from decimal import Decimal, InvalidOperation

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler, ContextTypes,
    ConversationHandler, MessageHandler, filters,
)
from sqlalchemy import select

from .config import get_settings
from .db import SessionLocal
from .models import User, Item
from . import repository as repo

log = logging.getLogger(__name__)
settings = get_settings()
TITLE, DESCRIPTION, CATEGORY, CONDITION, PRICE, CITY, PHOTO = range(7)


def money(value):
    return f"{Decimal(value):,.2f} ETB"


def menu(user_id):
    rows = [
        [InlineKeyboardButton("🛍 ገበያ ይመልከቱ", callback_data="feed:0")],
        [InlineKeyboardButton("➕ እቃ ይለጥፉ", callback_data="post")],
        [InlineKeyboardButton("📦 የእኔ እቃዎች", callback_data="mine")],
        [InlineKeyboardButton("🤝 ደላሎች", callback_data="brokers")],
    ]
    if user_id in settings.admins:
        rows.append([InlineKeyboardButton("🛡 Admin", callback_data="admin")])
    return InlineKeyboardMarkup(rows)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with SessionLocal() as db:
        user = repo.upsert_user(db, update.effective_user)
    await update.effective_message.reply_text(
        f"ሰላም {html.escape(update.effective_user.first_name or 'ደንበኛ')}! 👋\n"
        "ወደ ገበያ አገናኝ በደህና መጡ።\n\n"
        "እቃዎችን ይመልከቱ፣ ይለጥፉ ወይም ሻጮችን ያግኙ።",
        parse_mode=ParseMode.HTML, reply_markup=menu(user.telegram_id),
    )
    return ConversationHandler.END


async def post_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with SessionLocal() as db:
        repo.upsert_user(db, update.effective_user)
    context.user_data["listing"] = {}
    await update.effective_message.reply_text(
        "የእቃውን ስም ያስገቡ (ከ3-120 ቁምፊ)። /cancel ለማቋረጥ።"
    )
    return TITLE


async def title_step(update, context):
    value = update.message.text.strip()
    if not 3 <= len(value) <= 120:
        await update.message.reply_text("ስሙ ከ3 እስከ 120 ቁምፊ ይሁን።")
        return TITLE
    context.user_data["listing"]["title"] = value
    await update.message.reply_text("የእቃውን መግለጫ ያስገቡ (እስከ 1500 ቁምፊ)።")
    return DESCRIPTION


async def description_step(update, context):
    value = update.message.text.strip()
    if len(value) > 1500:
        await update.message.reply_text("መግለጫው ከ1500 ቁምፊ በታች ይሁን።")
        return DESCRIPTION
    context.user_data["listing"]["description"] = value
    await update.message.reply_text("የእቃውን ምድብ ያስገቡ። ምሳሌ: Electronics, Vehicle, Home")
    return CATEGORY


async def category_step(update, context):
    context.user_data["listing"]["category"] = update.message.text.strip()[:64]
    keyboard = [[
        InlineKeyboardButton("🟢 አዲስ", callback_data="condition:new"),
        InlineKeyboardButton("🟡 ያገለገለ", callback_data="condition:used"),
    ]]
    await update.message.reply_text("የእቃውን ሁኔታ ይምረጡ።", reply_markup=InlineKeyboardMarkup(keyboard))
    return CONDITION


async def condition_step(update, context):
    q = update.callback_query
    await q.answer()
    context.user_data["listing"]["condition"] = q.data.split(":")[1]
    await q.edit_message_text("ዋጋውን በETB ያስገቡ (ቁጥር ብቻ)። ምሳሌ: 12500")
    return PRICE


async def price_step(update, context):
    try:
        amount = Decimal(update.message.text.strip().replace(",", ""))
        if not amount.is_finite() or amount <= 0 or amount > Decimal("9999999999"):
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        await update.message.reply_text("ትክክለኛ የETB ዋጋ ያስገቡ።")
        return PRICE
    context.user_data["listing"]["price"] = str(amount.quantize(Decimal("0.01")))
    await update.message.reply_text("ከተማዎን/አካባቢዎን ያስገቡ።")
    return CITY


async def city_step(update, context):
    context.user_data["listing"]["city"] = update.message.text.strip()[:80]
    await update.message.reply_text("የእቃውን ፎቶ ይላኩ። ፎቶ ከሌለ /skip ይጻፉ።")
    return PHOTO


async def photo_step(update, context):
    if update.message.photo:
        context.user_data["listing"]["photo_file_id"] = update.message.photo[-1].file_id
    elif update.message.text and update.message.text.strip() == "/skip":
        context.user_data["listing"]["photo_file_id"] = None
    else:
        await update.message.reply_text("ፎቶ ይላኩ ወይም /skip ይጻፉ።")
        return PHOTO

    with SessionLocal() as db:
        seller = db.scalar(select(User).where(User.telegram_id == update.effective_user.id))
        item = repo.create_item(db, seller, context.user_data["listing"])
        repo.audit(db, update.effective_user.id, "item_submitted", "item", item.id)
    context.user_data.pop("listing", None)
    await update.message.reply_text(
        f"✅ ማስታወቂያዎ ተቀብሏል።\nየእቃ ቁጥር: #{item.id}\n"
        "ከAdmin ማረጋገጫ በኋላ በገበያ ላይ ይታያል።",
        reply_markup=menu(update.effective_user.id),
    )
    # Notify admins about moderation queue.
    for admin_id in settings.admins:
        try:
            await context.bot.send_message(
                admin_id,
                f"🆕 አዲስ እቃ ለማረጋገጥ\n#{item.id} {html.escape(item.title)}\n"
                f"{money(item.price)} · {html.escape(item.city)}",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ Approve", callback_data=f"approve:{item.id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject:{item.id}"),
                ]]),
            )
        except Exception:
            log.exception("Could not notify admin %s", admin_id)
    return ConversationHandler.END


async def cancel(update, context):
    context.user_data.pop("listing", None)
    await update.effective_message.reply_text("የእቃ መለጠፍ ሂደት ተቋርጧል።")
    return ConversationHandler.END


async def feed(update, context, offset):
    q = update.callback_query
    with SessionLocal() as db:
        items = repo.list_active_items(db, offset, 5)
        for item in items:
            seller = db.get(User, item.seller_id)
            text = (
                f"📦 <b>{html.escape(item.title)}</b>\n"
                f"{html.escape(item.description[:700])}\n"
                f"💰 {money(item.price)}\n"
                f"📍 {html.escape(item.city)} · "
                f"{'አዲስ' if item.condition == 'new' else 'ያገለገለ'}\n"
                f"👤 {html.escape(seller.first_name)} · #{item.id}"
            )
            rows = [[
                InlineKeyboardButton("❤️", callback_data=f"like:{item.id}"),
                InlineKeyboardButton("👎", callback_data=f"dislike:{item.id}"),
            ]]
            if seller.username:
                rows.append([InlineKeyboardButton("✉️ ሻጩን ያነጋግሩ", url=f"https://t.me/{seller.username}")])
            else:
                rows.append([InlineKeyboardButton("✉️ ሻጩን ያነጋግሩ", url=f"tg://user?id={seller.telegram_id}")])
            markup = InlineKeyboardMarkup(rows)
            if item.photo_file_id:
                try:
                    await q.message.reply_photo(item.photo_file_id, caption=text, parse_mode=ParseMode.HTML, reply_markup=markup)
                except Exception:
                    await q.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)
            else:
                await q.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)
    nav = []
    if offset:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"feed:{max(0, offset-5)}"))
    if len(items) == 5:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"feed:{offset+5}"))
    nav.append(InlineKeyboardButton("🏠", callback_data="home"))
    await q.message.reply_text("የገበያ ዝርዝር", reply_markup=InlineKeyboardMarkup([nav]))


async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data
    with SessionLocal() as db:
        user = repo.upsert_user(db, q.from_user)
        if data == "home":
            await q.answer()
            await q.message.reply_text("ዋና ምናሌ", reply_markup=menu(user.telegram_id))
        elif data.startswith("feed:"):
            await q.answer()
            await feed(update, context, max(0, int(data.split(":")[1])))
        elif data.startswith(("like:", "dislike:")):
            action, item_id = data.split(":")
            ok = repo.set_reaction(db, user, int(item_id), action)
            await q.answer("ምላሽዎ ተመዝግቧል።" if ok else "እቃው አይገኝም።", show_alert=True)
        elif data == "post":
            await q.answer()
            await q.message.reply_text("እቃ ለመለጠፍ /post ይጻፉ።")
        elif data == "mine":
            await q.answer()
            mine = list(db.scalars(select(Item).where(Item.seller_id == user.id).order_by(Item.id.desc()).limit(10)))
            if not mine:
                await q.message.reply_text("ገና የለጠፉት እቃ የለም።")
            else:
                lines = [f"#{x.id} {html.escape(x.title)} — {x.status}" for x in mine]
                await q.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
        elif data == "brokers":
            await q.answer()
            await q.message.reply_text(
                "🤝 የደላሎች ዝርዝር በAdmin ከተረጋገጡ በኋላ ይታያል።\n"
                "አሁን የደላላ ማስታወቂያ ለመጨመር ድጋፍን ያነጋግሩ።"
            )
        elif data in ("admin",) or data.startswith(("approve:", "reject:")):
            if user.telegram_id not in settings.admins:
                await q.answer("ፈቃድ የለዎትም።", show_alert=True)
                return
            if data == "admin":
                from .repository import stats
                s = stats(db)
                await q.answer()
                await q.message.reply_text(
                    f"🛡 Admin Dashboard\nUsers: {s['users']}\nPending: {s['pending']}\n"
                    f"Active: {s['active']}\nPayments: {s['payments']}\n"
                    "/admin · /pending"
                )
            else:
                action, raw_id = data.split(":")
                item = db.get(Item, int(raw_id))
                if not item or item.status != "pending":
                    await q.answer("እቃው አልተገኘም ወይም ቀድሞ ተወስኗል።", show_alert=True)
                    return
                item.status = "active" if action == "approve" else "rejected"
                repo.audit(db, user.telegram_id, action, "item", item.id)
                db.commit()
                await q.answer("ተሳክቷል።", show_alert=True)
                await q.message.edit_reply_markup(reply_markup=None)
                try:
                    await context.bot.send_message(
                        (await db.get_bind().run_sync(lambda sync: None)) if False else
                        db.scalar(select(User.telegram_id).where(User.id == item.seller_id)),
                        f"የእቃዎ #{item.id} " + ("ተፈቅዷል።" if action == "approve" else "አልተፈቀደም።")
                    )
                except Exception:
                    log.exception("Seller notification failed")


def build_application():
    app = Application.builder().token(settings.bot_token).build()
    listing = ConversationHandler(
        entry_points=[CommandHandler("post", post_start)],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, title_step)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description_step)],
            CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, category_step)],
            CONDITION: [CallbackQueryHandler(condition_step, pattern=r"^condition:(new|used)$")],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, price_step)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, city_step)],
            PHOTO: [
                MessageHandler(filters.PHOTO, photo_step),
                CommandHandler("skip", photo_step),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(listing)
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(callbacks))
    return app
