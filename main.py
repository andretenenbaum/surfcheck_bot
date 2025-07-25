import os
import sys
import httpx
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
    previsoes = await obter_previsao_openmeteo(pico["latitude"], pico["longitude"], dias)

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

async def obter_previsao_openmeteo(lat, lon, dias):
    url = "https://marine-api.open-meteo.com/v1/marine"
    start = dias[0].isoformat()
    end = dias[-1].isoformat()

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "wave_height,wave_direction,wind_speed,wind_direction",
                "timezone": "America/Sao_Paulo",
                "start_date": start,
                "end_date": end
            })

        resp.raise_for_status()
        dados = resp.json()
        previsoes = []

        for dia in dias:
            data_str = dia.isoformat()
            horarios = dados["hourly"]["time"]
            alturas = dados["hourly"]["wave_height"]
            direcoes = dados["hourly"]["wave_direction"]
            ventos = dados["hourly"]["wind_speed"]
            vento_dir = dados["hourly"]["wind_direction"]

            indices = [i for i, h in enumerate(horarios) if h.startswith(data_str)]
            if not indices:
                continue

            melhor_hora, max_altura = "", 0
            for i in indices:
                if alturas[i] > max_altura:
                    max_altura = alturas[i]
                    melhor_hora = horarios[i][11:16]

            i_best = indices[alturas.index(max_altura)]
            estrelas = int(min(max_altura * 2, 5))
            comentario = "Bom para Itaúna" if 90 <= direcoes[i_best] <= 150 else "Condição fraca para o pico"

            previsoes.append({
                "data": dia.strftime("%d/%m/%Y"),
                "melhor_horario": melhor_hora,
                "onda": round(alturas[i_best], 1),
                "direcao_onda": int(direcoes[i_best]),
                "vento": int(ventos[i_best]),
                "direcao_vento": int(vento_dir[i_best]),
                "estrelas": "⭐️" * estrelas,
                "comentario": comentario
            })

        return previsoes

    except Exception as e:
        print("❌ Erro na API Open-Meteo:", e)
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
