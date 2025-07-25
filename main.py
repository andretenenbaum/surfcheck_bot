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
    await update.message.reply_text("\U0001F30A Olá! Eu sou o SurfCheck Bot. Envie /previsao para saber as condições do mar.")

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
    previsoes = await obter_previsao_openmeteo(pico["latitude"], pico["longitude"], dias)

    if not previsoes:
        await update.message.reply_text("Erro ao obter a previsão. Tente novamente mais tarde.")
        return ConversationHandler.END

    resposta = f"\U0001F30A *Previsão para {pico['nome']}*\n\n"
    for previsao in previsoes:
        resposta += f"\U0001F4C5 {previsao['data']}\n"
        resposta += f"Melhor janela: {previsao['melhor_janela']}\n"
        resposta += f"Onda: {previsao['onda']} m ({previsao['direcao_onda']}°)\n"
        resposta += f"Período: {previsao['periodo']} s\n"
        resposta += f"Vento: {previsao['vento']} km/h ({previsao['direcao_vento']}°)\n"
        resposta += f"\u2B50 Condição: {previsao['estrelas']}\n"
        resposta += f"\U0001F4CC Análise: {previsao['comentario']}\n\n"

    await update.message.reply_markdown(resposta)
    return ConversationHandler.END

async def obter_previsao_openmeteo(lat, lon, dias):
    url_marine = "https://marine-api.open-meteo.com/v1/marine"
    url_forecast = "https://api.open-meteo.com/v1/forecast"
    start = dias[0].isoformat()
    end = dias[-1].isoformat()

    try:
        async with httpx.AsyncClient() as client:
            resp_marine = await client.get(url_marine, params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "wave_height,wave_direction,swell_wave_height,swell_wave_period",
                "timezone": "America/Sao_Paulo",
                "start_date": start,
                "end_date": end
            })
            resp_forecast = await client.get(url_forecast, params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "wind_speed_10m,wind_direction_10m",
                "timezone": "America/Sao_Paulo",
                "start_date": start,
                "end_date": end
            })

        resp_marine.raise_for_status()
        resp_forecast.raise_for_status()
        dados_marine = resp_marine.json()
        dados_forecast = resp_forecast.json()

        previsoes = []

        for dia in dias:
            data_str = dia.isoformat()
            horas = dados_marine["hourly"]["time"]
            alturas = dados_marine["hourly"]["swell_wave_height"]
            periodos = dados_marine["hourly"]["swell_wave_period"]
            direcoes_onda = dados_marine["hourly"]["wave_direction"]
            ventos = dados_forecast["hourly"]["wind_speed_10m"]
            direcoes_vento = dados_forecast["hourly"]["wind_direction_10m"]

            indices = [i for i, h in enumerate(horas) if h.startswith(data_str)]
            if not indices:
                continue

            melhor_i = max(indices, key=lambda i: alturas[i] * periodos[i])
            janela = [i for i in indices if 90 <= direcoes_onda[i] <= 150]
            if janela:
                inicio = horas[janela[0]][11:16]
                fim = horas[janela[-1]][11:16]
                melhor_janela = f"{inicio} às {fim}"
            else:
                melhor_janela = "Sem janela ideal"

            altura = round(alturas[melhor_i], 1)
            periodo = round(periodos[melhor_i], 1)
            estrelas_num = min(int(altura * (periodo / 4)), 5)
            estrelas = "⭐️" * estrelas_num

            if estrelas_num <= 2:
                comentario = "Condição fraca para o pico"
            elif estrelas_num == 3:
                comentario = "Condição regular, com potencial"
            else:
                comentario = "Boa condição para o pico"

            previsoes.append({
                "data": dia.strftime("%d/%m/%Y"),
                "melhor_janela": melhor_janela,
                "onda": altura,
                "direcao_onda": int(direcoes_onda[melhor_i]),
                "periodo": periodo,
                "vento": int(ventos[melhor_i]),
                "direcao_vento": int(direcoes_vento[melhor_i]),
                "estrelas": estrelas,
                "comentario": comentario
            })

        return previsoes

    except Exception as e:
        print("❌ Erro na API Open-Meteo:", e)
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
