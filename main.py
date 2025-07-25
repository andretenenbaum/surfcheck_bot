import os
import sys
import httpx
import traceback
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Coordenadas do pico de Itaúna – Saquarema
PICOS = {
    "1": {"nome": "Itaúna – Saquarema", "latitude": -22.93668, "longitude": -42.48337}
}

(ESCOLHENDO_PICO, ESCOLHENDO_DIA) = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🌊 Olá! Eu sou o SurfCheck Bot. Envie /previsao para saber as condições do mar.")

async def previsao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    mensagem = "Escolha o pico de surf (digite o número):\n"
    for numero, dados in PICOS.items():
        mensagem += f"{numero}. {dados['nome']}\n"
    await update.message.reply_text(mensagem)
    return ESCOLHENDO_PICO

async def escolher_pico(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    escolha = update.message.text.strip()
    if escolha not in PICOS:
        await update.message.reply_text("Escolha inválida. Por favor, envie um número válido.")
        return ESCOLHENDO_PICO
    context.user_data["pico"] = PICOS[escolha]
    await update.message.reply_text("Deseja previsão para:\n1. Hoje\n2. Amanhã\n3. Próximos 3 dias")
    return ESCOLHENDO_DIA

async def escolher_dia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    escolha = update.message.text.strip()
    hoje = datetime.now().date()

    if escolha == "1":
        dias = [hoje]
    elif escolha == "2":
        dias = [hoje + timedelta(days=1)]
    elif escolha == "3":
        dias = [hoje + timedelta(days=i) for i in range(3)]
    else:
        await update.message.reply_text("Escolha inválida. Envie 1, 2 ou 3.")
        return ESCOLHENDO_DIA

    pico = context.user_data["pico"]
    previsoes = await obter_previsao_completa(pico["latitude"], pico["longitude"], dias)

    if not previsoes:
        await update.message.reply_text("Erro ao obter a previsão. Tente novamente mais tarde.")
        return ConversationHandler.END

    resposta = f"🌊 *Previsão para {pico['nome']}*\n\n"
    for previsao in previsoes:
        resposta += f"📅 {previsao['data']}\n"
        resposta += f"Melhor horário: {previsao['melhor_horario']}\n"
        resposta += f"Onda: {previsao['onda']} m ({previsao['direcao_onda']}°)\n"
        resposta += f"Vento: {previsao['vento']} km/h ({previsao['direcao_vento']}°)\n"
        resposta += f"⭐️ Condição: {previsao['estrelas']} estrelas\n"
        resposta += f"📌 Análise: {previsao['comentario']}\n\n"

    await update.message.reply_markdown(resposta)
    return ConversationHandler.END

async def obter_previsao_completa(lat, lon, dias):
    try:
        start = dias[0].isoformat()
        end = dias[-1].isoformat()

        async with httpx.AsyncClient() as client:
            # Chamada 1: Marine API (ondas)
            marine_url = "https://marine-api.open-meteo.com/v1/marine"
            marine_resp = await client.get(marine_url, params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "wave_height,wave_direction,wind_wave_height,wind_wave_direction",
                "timezone": "America/Sao_Paulo",
                "start_date": start,
                "end_date": end
            })
            marine_resp.raise_for_status()
            marine_data = marine_resp.json()

            # Chamada 2: Forecast API (vento)
            forecast_url = "https://api.open-meteo.com/v1/forecast"
            forecast_resp = await client.get(forecast_url, params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "wind_speed_10m,wind_direction_10m",
                "timezone": "America/Sao_Paulo",
                "start_date": start,
                "end_date": end
            })
            forecast_resp.raise_for_status()
            forecast_data = forecast_resp.json()

        previsoes = []

        for dia in dias:
            data_str = dia.isoformat()

            horas = marine_data["hourly"]["time"]
            ondas = marine_data["hourly"]["wave_height"]
            direcoes_onda = marine_data["hourly"]["wave_direction"]

            ventos = forecast_data["hourly"]["wind_speed_10m"]
            direcoes_vento = forecast_data["hourly"]["wind_direction_10m"]

            indices = [i for i, h in enumerate(horas) if h.startswith(data_str)]
            if not indices:
                continue

            melhor_hora, max_onda = "", 0
            i_best = indices[0]

            for i in indices:
                if ondas[i] > max_onda:
                    max_onda = ondas[i]
                    melhor_hora = horas[i][11:16]
                    i_best = i

            estrelas = int(min(max_onda * 2, 5))
            comentario = "Bom para Itaúna" if 90 <= direcoes_onda[i_best] <= 150 else "Condição fraca para o pico"

            previsoes.append({
                "data": dia.strftime("%d/%m/%Y"),
                "melhor_horario": melhor_hora,
                "onda": round(ondas[i_best], 1),
                "direcao_onda": int(direcoes_onda[i_best]),
                "vento": int(ventos[i_best]),
                "direcao_vento": int(direcoes_vento[i_best]),
                "estrelas": "⭐️" * estrelas,
                "comentario": comentario
            })

        return previsoes

    except Exception as e:
        print("❌ Erro ao consultar as APIs:")
        print(traceback.format_exc())
        return None

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN não está definido. Configure via .env ou Fly Secrets.")
        sys.exit(1)

    print("✅ Iniciando SurfCheck Bot...")
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("previsao", previsao)],
        states={
            ESCOLHENDO_PICO: [MessageHandler(filters.TEXT & ~filters.COMMAND, escolher_pico)],
            ESCOLHENDO_DIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, escolher_dia)],
        },
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.run_polling()
