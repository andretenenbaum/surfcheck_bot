import asyncio
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏄‍♂️ Olá! Eu sou o SurfCheckASR_bot.\n"
        "Use /previsao_hoje <pico> ou /previsao_amanha <pico> para receber as condições do mar."
    )

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("Bot rodando...")
    app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
