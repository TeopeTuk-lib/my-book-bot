import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from flask import Flask, request, jsonify

# === Настройки ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")

# Flask app
flask_app = Flask(__name__)

# Telegram bot
bot_app = Application.builder().token(TELEGRAM_TOKEN).build()

# --- Обработчики бота ---
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
    except Exception as e:
        print("Ошибка поиска:", e)
        await update.message.reply_text("❌ Ошибка подключения к библиотеке.")
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
    book_id = query.data.split("_", 1)[1]
    user_name = query.from_user.first_name

    try:
        resp = requests.post(APPS_SCRIPT_URL, json={
            "action": "book",
            "bookId": book_id,
            "userName": user_name
        })
        result = resp.json()
    except Exception as e:
        print("Ошибка бронирования:", e)
        await query.edit_message_text("❌ Ошибка при бронировании.")
        return

    if result.get("success"):
        await query.edit_message_text(f"✅ Вы забронировали:\n\n📘 *{result['title']}*\n\nСпасибо!", parse_mode="Markdown")
    elif result.get("error") == "already_booked":
        await query.edit_message_text("❌ Эта книга уже забронирована!")
    else:
        await query.edit_message_text("Книга не найдена.")

# Регистрация обработчиков
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_books))
bot_app.add_handler(CallbackQueryHandler(book_handler))

# Запуск бота один раз при старте
@flask_app.before_first_request
def init_bot():
    bot_app.run_polling(drop_pending_updates=True, close_loop=False)

# Webhook endpoint
@flask_app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def telegram_webhook():
    update = request.get_json()
    bot_app.update_queue.put_nowait(Update.de_json(update, bot_app.bot))
    return jsonify({"ok": True})

# Health check
@flask_app.route("/")
def home():
    return "Telegram book bot is running!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)
