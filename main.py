import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🌊 Olá! Eu sou o SurfCheck Bot. Envie /previsao para saber as condições do mar.")

# Exemplo de handler para /previsao (ajuste a lógica conforme seu código real)
async def previsao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("📈 Previsão do surf: ondas de 1,5m, vento fraco, swell de sudeste.")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("previsao", previsao))

    app.run_polling()

if __name__ == "__main__":
    main()
