import os
import logging
from datetime import datetime
import re
import pytz

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

TOKEN = "8256364719:AAEX1hXws4BrRB2w4TjQQM1yZLra8O_-Y-o"
OWNER_ID = 7820854091
CONV_DIR = "conversations"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

if not os.path.exists(CONV_DIR):
    os.makedirs(CONV_DIR)

users_set = set()


def log_message(user_id: int, sender: str, message: str):
    filename = os.path.join(CONV_DIR, f"{user_id}.txt")
    timestamp = datetime.now(pytz.UTC).strftime("%Y-%m-%d %H:%M")
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {sender}: {message}\n")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id == OWNER_ID:
        keyboard = [
            [InlineKeyboardButton("Send Message", callback_data="send")],
            [InlineKeyboardButton("List Users", callback_data="users")],
            [InlineKeyboardButton("Stats", callback_data="stats")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "👑 Admin Control Panel 👑\nSelect an option below:", reply_markup=reply_markup
        )
    else:
        welcome_text = (
            "👋 Hello! Welcome to the bot.\n"
            "Send me a message and I'll forward it to the owner.\n"
            "You'll receive a reply soon!"
        )
        await update.message.reply_text(welcome_text)


async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message.text

    users_set.add(user.id)

    log_message(user.id, "User", message)

    username = user.username or "NoUsername"
    text = f"📩 New message from @{username} (ID: {user.id}):\n\n{message}"

    # زر Reply مع user_id في callback_data
    keyboard = [
        [InlineKeyboardButton("Reply", callback_data=f"reply_{user.id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=OWNER_ID, text=text, reply_markup=reply_markup
    )

    await update.message.reply_text(
        "✅ Your message has been received and will be replied to shortly."
    )


async def handle_owner_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return

    reply_text = update.message.text
    original_msg = update.message.reply_to_message.text

    match = re.search(r"\(ID: (\d+)\)", original_msg)
    if not match:
        return

    user_id = int(match.group(1))

    try:
        await context.bot.send_message(chat_id=user_id, text=reply_text)
        log_message(user_id, "Owner", reply_text)
        await update.message.reply_text(f"✅ Reply sent to user {user_id}.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error sending reply: {e}")


async def send_message_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != OWNER_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("❗ Usage: /send <user_id> <message>")
        return

    try:
        user_id = int(context.args[0])
        message = " ".join(context.args[1:])
    except ValueError:
        await update.message.reply_text("❗ Please make sure user_id is a number.")
        return

    try:
        await context.bot.send_message(chat_id=user_id, text=message)
        log_message(user_id, "Owner", message)
        await update.message.reply_text(f"✅ Message sent to user {user_id}.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error sending message: {e}")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != OWNER_ID:
        await query.edit_message_text("❌ You are not authorized to use this panel.")
        return

    data = query.data

    if data == "send":
        await query.edit_message_text(
            "📝 Please use the command:\n/send <user_id> <message>"
        )
    elif data == "users":
        if users_set:
            users_list = "\n".join(str(uid) for uid in users_set)
            await query.edit_message_text(f"👥 Users who contacted you:\n{users_list}")
        else:
            await query.edit_message_text("No users have contacted you yet.")
    elif data == "stats":
        total_users = len(users_set)
        await query.edit_message_text(f"📊 Stats:\nTotal users contacted: {total_users}")
    elif data.startswith("reply_"):
        user_id = data.split("_")[1]
        await query.edit_message_text(
            f"✏️ To reply to user {user_id}, use the command:\n/reply {user_id} <your message>"
        )
    else:
        await query.edit_message_text("Unknown option.")


async def reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != OWNER_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("❗ Usage: /reply <user_id> <message>")
        return

    try:
        user_id = int(context.args[0])
        message = " ".join(context.args[1:])
    except ValueError:
        await update.message.reply_text("❗ Please make sure user_id is a number.")
        return

    try:
        await context.bot.send_message(chat_id=user_id, text=message)
        log_message(user_id, "Owner", message)
        await update.message.reply_text(f"✅ Reply sent to user {user_id}.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error sending reply: {e}")


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    if app.job_queue:
        app.job_queue._scheduler.configure(timezone=pytz.UTC)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("send", send_message_command))
    app.add_handler(CommandHandler("reply", reply_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.User(user_id=OWNER_ID), handle_user_message))
    app.add_handler(MessageHandler(filters.TEXT & filters.User(user_id=OWNER_ID), handle_owner_reply))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
