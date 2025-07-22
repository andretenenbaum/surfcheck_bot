import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Configuração básica de logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏄 Olá! O bot do surf está no ar!")

# Função principal
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Adiciona os handlers
    app.add_handler(CommandHandler("start", start))

    # Inicia o bot
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
