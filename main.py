import os
import datetime
import httpx
import pytz
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Coordenadas do pico de Itaúna, Saquarema
LATITUDE = -22.93668
LONGITUDE = -42.48337

# Converte grau para direção cardinal
def grau_para_direcao(grau):
    direcoes = ['N', 'NE', 'L', 'SE', 'S', 'SO', 'O', 'NO']
    idx = int((grau + 22.5) % 360 / 45)
    return direcoes[idx]

# Converte altura da onda para texto
def classificar_altura(altura):
    if altura == 0:
        return "Flat"
    elif altura < 0.5:
        return "Mar pequeno"
    elif altura < 1:
        return "Boas condições de tamanho"
    elif altura < 1.5:
        return "Mar com tamanho"
    else:
        return "Mar grande"

# Gera previsão com janela de horário
async def obter_previsao():
    try:
        url = (
            f"https://marine-api.open-meteo.com/v1/marine?latitude={LATITUDE}&longitude={LONGITUDE}"
            f"&daily=wave_height,swell_wave_height,swell_wave_direction,wind_speed_10m,wind_direction_10m"
            f"&timezone=America%2FSao_Paulo&hourly=wave_height,swell_wave_height,swell_wave_direction,wind_speed_10m,wind_direction_10m"
        )
        async with httpx.AsyncClient() as client:
            resposta = await client.get(url)
            dados = resposta.json()

        dias = dados["daily"]
        horas = dados["hourly"]

        previsao = "\n📍 Previsão para Itaúna – Saquarema\n"
        previsao += f"🗓️ De {dias['time'][0]} até {dias['time'][-1]}\n\n"

        for i in range(3):
            data = dias['time'][i]
            altura = dias['wave_height'][i]
            vento = dias['wind_speed_10m'][i]
            direcao_vento = grau_para_direcao(dias['wind_direction_10m'][i])
            swell = grau_para_direcao(dias['swell_wave_direction'][i])
            periodo = 1.2 + i * 0.4  # placeholder

            descricao = classificar_altura(altura)
            estrelas = "⭐" * min(5, max(1, int(altura / 0.5)))

            janela = calcular_melhor_janela(horas, data)

            previsao += f"📅 {data} – {len(estrelas)}{estrelas}\n"
            previsao += f"🌊 Altura: {altura:.2f}m ({descricao}) | 🌬️ Vento: {vento:.1f} km/h ({direcao_vento}) | 🌊 Swell: {swell}\n"
            previsao += f"📈 Período médio: {periodo:.1f}s\n"
            previsao += f"🕐 Melhor horário: {janela}\n"
            previsao += f"🔍 Condições: {descricao.lower()}.\n\n"

        return previsao
    except Exception as e:
        print(f"Erro ao obter previsão: {e}")
        return "Erro ao obter a previsão. Tente novamente mais tarde."

# Determina a melhor janela horária com menor vento
def calcular_melhor_janela(horas, data):
    indices = [i for i, t in enumerate(horas['time']) if t.startswith(data)]
    menor_vento = 999
    melhor_hora = ""
    for i in indices:
        vento = horas['wind_speed_10m'][i]
        if vento < menor_vento:
            menor_vento = vento
            melhor_hora = horas['time'][i][-5:]  # HH:MM
    return melhor_hora if melhor_hora else "não identificado"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🌊 Olá! Eu sou o SurfCheck Bot.\nEnvie /previsao para saber as condições em Itaúna - Saquarema."
    )

async def previsao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = await obter_previsao()
    await update.message.reply_text(msg)

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("previsao", previsao))
    print("✅ Iniciando SurfCheck Bot...")
    app.run_polling()
