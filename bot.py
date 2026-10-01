import os
import json
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
GAME_URL = os.environ.get("GAME_URL", "")

DB = "scores.db"

def init_db():
    with sqlite3.connect(DB) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                score INTEGER NOT NULL DEFAULT 0
            )
        """)

def save_score(user_id, username, score):
    with sqlite3.connect(DB) as con:
        con.execute("""
            INSERT INTO scores(user_id, username, score)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                score=MAX(scores.score, excluded.score)
        """, (user_id, username or "Игрок", int(score)))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not GAME_URL:
        await update.message.reply_text("Игра пока не настроена.")
        return
    keyboard = [
        [InlineKeyboardButton("🎮 Играть", web_app=WebAppInfo(url=GAME_URL))],
        [InlineKeyboardButton("🏆 Топ игроков", callback_data="top")]
    ]
    await update.message.reply_text(
        "🎮 Добро пожаловать!\n\nНажми «Играть», чтобы начать.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with sqlite3.connect(DB) as con:
        rows = con.execute(
            "SELECT username, score FROM scores ORDER BY score DESC LIMIT 10"
        ).fetchall()
    if not rows:
        text = "🏆 Пока результатов нет."
    else:
        text = "🏆 Топ игроков:\n\n" + "\n".join(
            f"{i}. {name} — {score}" for i, (name, score) in enumerate(rows, 1)
        )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(text)
    else:
        await update.message.reply_text(text)

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = json.loads(update.effective_message.web_app_data.data)
        score = int(data.get("score", 0))
        user = update.effective_user
        save_score(user.id, user.username or user.first_name, score)
        await update.effective_message.reply_text(f"🎯 Результат сохранён: {score}")
    except Exception:
        await update.effective_message.reply_text("Не удалось сохранить результат.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start — открыть игру\n/top — таблица лидеров\n/help — помощь"
    )

def main():
    if not BOT_TOKEN:
        raise RuntimeError("Не задан BOT_TOKEN")
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(top, pattern="^top$"))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    app.run_polling()

if __name__ == "__main__":
    main()
