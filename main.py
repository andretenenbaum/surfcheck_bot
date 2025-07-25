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
        resposta += f"Melhor janela: {previsao['melhor_janela']}\n"
        resposta += f"Onda: {previsao['onda']} m ({previsao['direcao_onda']}°)\n"
        resposta += f"Vento: {previsao['vento']} km/h ({previsao['direcao_vento']}°)\n"
        resposta += f"⭐️ Condição: {previsao['estrelas']}\n"
        resposta += f"📌 Análise: {previsao['comentario']}\n\n"

    await update.message.reply_markdown(resposta)
    return ConversationHandler.END

async def obter_previsao_completa(lat, lon, dias):
    try:
        start = dias[0].isoformat()
        end = dias[-1].isoformat()

        async with httpx.AsyncClient() as client:
            marine_url = "https://marine-api.open-meteo.com/v1/marine"
            forecast_url = "https://api.open-meteo.com/v1/forecast"

            marine_resp = await client.get(marine_url, params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "wave_height,wave_direction,wind_wave_height,wind_wave_direction",
                "timezone": "America/Sao_Paulo",
                "start_date": start,
                "end_date": end
            })
            forecast_resp = await client.get(forecast_url, params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "wind_speed_10m,wind_direction_10m",
                "timezone": "America/Sao_Paulo",
                "start_date": start,
                "end_date": end
            })

        marine_resp.raise_for_status()
        forecast_resp.raise_for_status()
        m = marine_resp.json()["hourly"]
        f = forecast_resp.json()["hourly"]

        previsoes = []
        for dia in dias:
            data_str = dia.isoformat()
            indices = [i for i, t in enumerate(m["time"]) if t.startswith(data_str)]
            if not indices:
                continue

            melhor_janela = calcular_melhor_janela(indices, m["wave_height"], m["wave_direction"], f["wind_speed_10m"], f["wind_direction_10m"])
            i_best = indices[max(range(len(indices)), key=lambda i: m["wave_height"][indices[i]])]

            estrelas, comentario = avaliar_condicoes(
                m["wave_height"][i_best],
                m["wave_direction"][i_best],
                f["wind_speed_10m"][i_best],
                f["wind_direction_10m"][i_best],
                m["wind_wave_height"][i_best]
            )

            previsoes.append({
                "data": dia.strftime("%d/%m/%Y"),
                "melhor_janela": melhor_janela,
                "onda": round(m["wave_height"][i_best], 1),
                "direcao_onda": int(m["wave_direction"][i_best]),
                "vento": int(f["wind_speed_10m"][i_best]),
                "direcao_vento": int(f["wind_direction_10m"][i_best]),
                "estrelas": estrelas,
                "comentario": comentario
            })

        return previsoes

    except Exception as e:
        print("❌ Erro ao consultar as APIs:")
        print(traceback.format_exc())
        return None

def avaliar_condicoes(onda, dir_onda, vento, dir_vento, energia):
    estrelas = 0
    comentario = "Condição fraca para o pico"

    if onda >= 1.0:
        estrelas += 1
    if 90 <= dir_onda <= 140:
        estrelas += 1
    if vento < 10 and (dir_vento <= 45 or dir_vento >= 315):
        estrelas += 1
    if energia > 0.3:
        estrelas += 1
    if onda >= 1.5 and energia >= 0.5:
        estrelas += 1

    if estrelas >= 4:
        comentario = "Boa condição para o pico"
    elif estrelas == 3:
        comentario = "Condição regular, com potencial"

    return "⭐️" * estrelas, comentario

def calcular_melhor_janela(indices, ondas, dir_ondas, ventos, dir_ventos):
    janela = []
    for i in indices:
        if ondas[i] < 0.8:
            continue
        if not (90 <= dir_ondas[i] <= 140):
            continue
        if ventos[i] > 12 or not (dir_ventos[i] <= 45 or dir_ventos[i] >= 315):
            continue
        hora = f"{i%24:02d}:00"
        janela.append(hora)

    if not janela:
        return "Sem janela ideal"
    return f"{janela[0]} às {janela[-1]}" if len(janela) > 1 else janela[0]

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
