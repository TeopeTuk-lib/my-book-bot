import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! 📚\nВведите название книги или автора:")

async def search_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    if len(query) < 2:
        await update.message.reply_text("Введите хотя бы 2 символа.")
        return

    try:
        resp = requests.post(APPS_SCRIPT_URL, json={"action": "search", "query": query})
        data = resp.json()
        books = data.get("results", [])
    except:
        await update.message.reply_text("Ошибка подключения к библиотеке.")
        return

    if not books:
        await update.message.reply_text("Книги не найдены 😕")
        return

    buttons = []
    for b in books[:10]:
        buttons.append([InlineKeyboardButton(f"{b['title']} — {b['author']}", callback_data=f"book_{b['id']}")])
    
    await update.message.reply_text("Выберите книгу:", reply_markup=InlineKeyboardMarkup(buttons))

async def book_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    book_id = query.data.split("_")[1]
    user = query.from_user.first_name

    try:
        resp = requests.post(APPS_SCRIPT_URL, json={"action": "book", "bookId": book_id, "userName": user})
        result = resp.json()
    except:
        await query.edit_message_text("Ошибка бронирования.")
        return

    if result.get("success"):
        await query.edit_message_text(f"✅ Забронировано: *{result['title']}*", parse_mode="Markdown")
    else:
        await query.edit_message_text("❌ Книга уже забронирована или не найдена.")

if __name__ == "__main__":
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_books))
    app.add_handler(CallbackQueryHandler(book_handler))
    app.run_polling()
