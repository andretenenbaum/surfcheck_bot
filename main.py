import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv
import asyncio

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    await update.message.reply_text(
        "Olá! Eu sou o SurfCheck Bot. Envie /previsao para saber as condições do mar."
    )

async def previsao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /previsao command."""
    await update.message.reply_text(
        "Previsão do surf: ondas de 1,5m, vento fraco, swell de sudeste."
    )

async def main() -> None:
    """Start the bot and handle commands."""
    # Ensure BOT_TOKEN is set to avoid runtime errors
    if not BOT_TOKEN:
        print(
            "BOT_TOKEN is not set. Please configure it via environment variable or Fly secret."
        )
        return

    application = Application.builder().token(BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("previsao", previsao))

    # Run the bot using long polling
    await application.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
