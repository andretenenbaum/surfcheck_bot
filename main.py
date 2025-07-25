import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv
import asyncio
import sys

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🌊 Olá! Eu sou o SurfCheck Bot. Envie /previsao para saber as condições do mar."
    )

async def previsao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Previsão do surf: ondas de 1,5m, vento fraco, swell de sudeste."
    )

async def main() -> None:
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN não está definido. Configure via .env ou Fly Secrets.")
        sys.exit(1)

    print("✅ Iniciando SurfCheck Bot...")

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("previsao", previsao))

    await application.run_polling()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
