import os
import logging
import httpx
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Estados do ConversationHandler
ESCOLHER_PICO, ESCOLHER_DIA = range(2)

# Configuração do log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Picos disponíveis
picos = {
    "1": {
        "nome": "Itaúna – Saquarema",
        "latitude": -22.93668,
        "longitude": -42.48337
    }
}

# Start do bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌊 Olá! Eu sou o SurfCheck Bot.\n\nDigite /previsao para saber as condições do surf."
    )

# Comando /previsao
async def previsao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[f"{k}"] for k in picos.keys()]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Qual pico você deseja consultar?", reply_markup=reply_markup)
    return ESCOLHER_PICO

# Usuário escolhe o pico
async def escolher_pico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    escolha = update.message.text.strip()
    if escolha not in picos:
        await update.message.reply_text("Escolha inválida. Tente novamente com /previsao.")
        return ConversationHandler.END
    context.user_data["pico"] = picos[escolha]
    keyboard = [["1. Hoje"], ["2. Amanhã"], ["3. Próximos 3 dias"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Para quando você deseja a previsão?", reply_markup=reply_markup)
    return ESCOLHER_DIA

# Usuário escolhe o período da previsão
async def escolher_dia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    escolha = update.message.text.strip()
    hoje = datetime.utcnow().date()
    if escolha.startswith("1"):
        start_date = hoje
        end_date = hoje
    elif escolha.startswith("2"):
        start_date = hoje + timedelta(days=1)
        end_date = start_date
    elif escolha.startswith("3"):
        start_date = hoje + timedelta(days=1)
        end_date = start_date + timedelta(days=2)
    else:
        await update.message.reply_text("Escolha inválida. Tente novamente com /previsao.")
        return ConversationHandler.END

    pico = context.user_data["pico"]
    try:
        # Chamada à API Open-Meteo
        url = (
            "https://marine-api.open-meteo.com/v1/marine"
            f"?latitude={pico['latitude']}&longitude={pico['longitude']}"
            "&hourly=wave_height,wave_direction,wind_speed,wind_direction,swells,swells_direction"
            "&daily=wave_height_max,swells_period_max"
            f"&start_date={start_date}&end_date={end_date}&timezone=UTC"
        )
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        # Verifica se veio daily data
        if "daily" not in data:
            raise ValueError("Dados diários ausentes")

        # Gera a previsão básica
        texto = f"📍 Previsão para {pico['nome']} de {start_date.strftime('%d/%m')} até {end_date.strftime('%d/%m')}:\n"
        for i, dia in enumerate(data["daily"]["time"]):
            altura = data["daily"]["wave_height_max"][i]
            periodo = data["daily"]["swells_period_max"][i]
            texto += f"\n📅 {dia}:\n🌊 Altura máx: {altura} m\n⏱️ Período do swell: {periodo} s\n"
        await update.message.reply_text(texto)

    except Exception as e:
        logger.error(f"Erro ao obter previsão: {e}")
        await update.message.reply_text("Erro ao obter a previsão. Tente novamente mais tarde.")
    return ConversationHandler.END

# Fallback
async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operação cancelada.")
    return ConversationHandler.END

# App
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("previsao", previsao)],
        states={
            ESCOLHER_PICO: [MessageHandler(filters.TEXT & ~filters.COMMAND, escolher_pico)],
            ESCOLHER_DIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, escolher_dia)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.run_polling()
