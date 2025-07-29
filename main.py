import os
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv
import httpx
import logging

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

user_states = {}

PICOS = {
    "1": {
        "nome": "Itaúna – Saquarema",
        "latitude": -22.93668,
        "longitude": -42.48337
    }
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🌊 Olá! Eu sou o SurfCheck Bot.\nEnvie /previsao para saber as condições em Itaúna - Saquarema.")

async def previsao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_states[user_id] = {"state": "awaiting_spot"}
    mensagem = "🌊 Qual pico você deseja consultar?\n"
    for key, pico in PICOS.items():
        mensagem += f"{key}. {pico['nome']}\n"
    await update.message.reply_text(mensagem)

async def handle_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = update.message.text.strip()
    state = user_states.get(user_id, {}).get("state")

    if state == "awaiting_spot":
        if text in PICOS:
            user_states[user_id]["spot"] = text
            user_states[user_id]["state"] = "awaiting_day"
            await update.message.reply_text(
                "📅 Deseja a previsão para:\n1. Hoje\n2. Amanhã\n3. Próximos 3 dias"
            )
        else:
            await update.message.reply_text("❌ Pico inválido. Tente novamente.")
    elif state == "awaiting_day":
        if text in ["1", "2", "3"]:
            user_states[user_id]["day_option"] = text
            await obter_previsao(update, context)
            user_states.pop(user_id)
        else:
            await update.message.reply_text("❌ Opção inválida. Escolha 1, 2 ou 3.")

async def obter_previsao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    data = user_states[user_id]
    pico = PICOS[data["spot"]]
    latitude = pico["latitude"]
    longitude = pico["longitude"]
    nome_pico = pico["nome"]
    option = data["day_option"]

    if option == "1":  # Hoje
        start_date = end_date = datetime.utcnow().date()
    elif option == "2":  # Amanhã
        start_date = end_date = datetime.utcnow().date() + timedelta(days=1)
    else:  # Próximos 3 dias (amanhã em diante)
        start_date = datetime.utcnow().date() + timedelta(days=1)
        end_date = start_date + timedelta(days=2)

    url = (
        f"https://marine-api.open-meteo.com/v1/marine?"
        f"latitude={latitude}&longitude={longitude}"
        f"&hourly=wave_height,wave_direction,wind_speed,wind_direction,swells,swells_direction"
        f"&daily=wave_height_max,swells_period_max"
        f"&start_date={start_date}&end_date={end_date}&timezone=UTC"
    )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            dados = response.json()

        if "daily" not in dados or not dados["daily"]["wave_height_max"]:
            raise ValueError("Dados diários ausentes")

        mensagem = f"📍 Previsão para *{nome_pico}* de {start_date} a {end_date}:\n"
        for i, dia in enumerate(dados["daily"]["time"]):
            altura = dados["daily"]["wave_height_max"][i]
            periodo = dados["daily"].get("swells_period_max", ["-"])[i]
            mensagem += f"\n📅 {dia} — Altura máx: {altura:.1f}m | Período: {periodo}s"

        await update.message.reply_text(mensagem, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Erro ao obter previsão: {e}")
        await update.message.reply_text("⚠️ Erro ao obter a previsão. Tente novamente mais tarde.")

def main() -> None:
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("previsao", previsao))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_response))
    app.run_polling()

if __name__ == "__main__":
    main()
