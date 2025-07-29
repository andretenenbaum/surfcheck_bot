
import os
import logging
import httpx
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

CHOOSING_LOCATION, CHOOSING_DAY = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply = "🌊 Bem-vindo ao SurfCheckASR!\nEscolha o pico de surf para consultar a previsão:\n1. Itaúna (Saquarema)"
    await update.message.reply_text(reply)
    return CHOOSING_LOCATION

async def choose_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    location_choice = update.message.text.strip()
    if location_choice != "1":
        await update.message.reply_text("Escolha inválida. Envie apenas o número correspondente.")
        return CHOOSING_LOCATION

    context.user_data["location"] = "Itaúna"
    reply = "Para qual período você quer a previsão?\n1. Hoje\n2. Amanhã\n3. Próximos 3 dias"
    await update.message.reply_text(reply)
    return CHOOSING_DAY

async def show_forecast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    day_choice = update.message.text.strip()

    if day_choice == "1":
        start_date = end_date = datetime.utcnow().date()
    elif day_choice == "2":
        start_date = end_date = datetime.utcnow().date() + timedelta(days=1)
    elif day_choice == "3":
        start_date = datetime.utcnow().date() + timedelta(days=1)
        end_date = start_date + timedelta(days=2)
    else:
        await update.message.reply_text("Escolha inválida. Envie 1, 2 ou 3.")
        return CHOOSING_DAY

    try:
        forecast = await fetch_forecast(start_date, end_date)
        await update.message.reply_text(forecast)
    except Exception as e:
        logging.error(f"Erro ao obter previsão: {e}")
        await update.message.reply_text("Erro ao obter a previsão. Tente novamente mais tarde.")
    return ConversationHandler.END

async def fetch_forecast(start_date, end_date) -> str:
    url = (
        "https://marine-api.open-meteo.com/v1/marine?"
        "latitude=-22.93668&longitude=-42.48337"
        "&hourly=wave_height,wave_direction,wind_speed,wind_direction,swells,swells_direction"
        "&daily=wave_height_max,swells_period_max"
        f"&start_date={start_date}&end_date={end_date}&timezone=UTC"
    )
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

    if "daily" not in data or not data["daily"].get("wave_height_max"):
        raise ValueError("Dados diários ausentes")

    dias = data["daily"]["time"]
    alturas = data["daily"]["wave_height_max"]
    periodos = data["daily"]["swells_period_max"]

    boletim = "📊 Previsão de Surf para Itaúna:\n"
    for i in range(len(dias)):
        data_fmt = datetime.strptime(dias[i], "%Y-%m-%d").strftime("%d/%m")
        altura = alturas[i]
        periodo = periodos[i]
        if altura == 0:
            cond = "Flat"
            estrelas = "⭑"
        elif altura < 0.5:
            cond = "Mar pequeno"
            estrelas = "⭑⭑"
        elif altura < 1:
            cond = "Boas condições de tamanho"
            estrelas = "⭑⭑⭑"
        elif altura < 1.5:
            cond = "Mar com tamanho"
            estrelas = "⭑⭑⭑⭑"
        else:
            cond = "Mar grande"
            estrelas = "⭑⭑⭑⭑⭑"

        boletim += f"\n📅 {data_fmt}\n🌊 Altura: {altura:.1f}m | Período: {periodo:.1f}s\n📝 Condição: {cond} {estrelas}\n"

    return boletim

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Previsão cancelada. Envie /previsao para começar novamente.")
    return ConversationHandler.END

def main() -> None:
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("previsao", start)],
        states={
            CHOOSING_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_day)],
            CHOOSING_DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, show_forecast)],
        },
        fallbacks=[CommandHandler("cancelar", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    app.run_polling()

if __name__ == "__main__":
    main()
