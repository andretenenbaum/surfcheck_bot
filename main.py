import os
import datetime
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Utilitários
DIRECOES = ['N', 'NE', 'L', 'SE', 'S', 'SO', 'O', 'NO']

def graus_para_direcao(graus):
    idx = round(((graus % 360) / 45)) % 8
    return DIRECOES[idx]

def formatar_mare(mare_data):
    if not mare_data or 'high_tide' not in mare_data or 'low_tide' not in mare_data:
        return "Dados de maré indisponíveis"
    try:
        cheia = mare_data['high_tide'][0]['time'][-5:]
        vazia = mare_data['low_tide'][0]['time'][-5:]
        altura_cheia = mare_data['high_tide'][0]['height']
        altura_vazia = mare_data['low_tide'][0]['height']
        variacao = round(abs(altura_cheia - altura_vazia), 2)
        return f"Maré cheia: {cheia}, Maré vazia: {vazia}, Variação: {variacao}m"
    except:
        return "Erro ao processar marés"

# Ponto fixo de Itaúna - Saquarema
LATITUDE = -22.93668
LONGITUDE = -42.48337

async def obter_previsao_completa(data):
    try:
        # Previsão marítima (altura e direção do swell)
        url_marine = f"https://marine-api.open-meteo.com/v1/marine?latitude={LATITUDE}&longitude={LONGITUDE}&hourly=wave_height,wave_direction,wind_wave_height,wind_wave_direction&timezone=America/Sao_Paulo&start_date={data}&end_date={data}"

        # Vento
        url_vento = f"https://api.open-meteo.com/v1/forecast?latitude={LATITUDE}&longitude={LONGITUDE}&hourly=wind_speed_10m,wind_direction_10m&timezone=America/Sao_Paulo&start_date={data}&end_date={data}"

        # Marés
        url_mare = f"https://marine-api.open-meteo.com/v1/marine?latitude={LATITUDE}&longitude={LONGITUDE}&daily=high_tide,low_tide&timezone=America/Sao_Paulo&start_date={data}&end_date={data}"

        async with httpx.AsyncClient(timeout=10) as client:
            resp_marine, resp_vento, resp_mare = await client.get(url_marine), await client.get(url_vento), await client.get(url_mare)
            dados_marine = resp_marine.json()
            dados_vento = resp_vento.json()
            dados_mare = resp_mare.json()

        alturas = dados_marine['hourly']['wave_height']
        direcoes_swell = dados_marine['hourly']['wave_direction']
        direcoes_swell_txt = graus_para_direcao(sum(direcoes_swell) / len(direcoes_swell))
        altura_media = round(sum(alturas) / len(alturas), 1)

        direcoes_vento = dados_vento['hourly']['wind_direction_10m']
        direcao_vento_txt = graus_para_direcao(sum(direcoes_vento) / len(direcoes_vento))

        texto_mare = formatar_mare(dados_mare.get('daily', {}))

        resposta = (
            f"🌊 **Previsão para {data} em Itaúna - Saquarema**\n\n"
            f"Altura média das ondas: {altura_media}m\n"
            f"Direção do swell: {direcoes_swell_txt}\n"
            f"Direção do vento: {direcao_vento_txt}\n"
            f"{texto_mare}"
        )
        return resposta
    except Exception as e:
        print(f"Erro ao obter dados: {e}")
        return "❌ Erro ao obter a previsão. Tente novamente mais tarde."

# Comandos
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🌊 Olá! Eu sou o SurfCheck Bot.\nEnvie /previsao para saber as condições em Itaúna - Saquarema."
    )

async def previsao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    opcoes = "Escolha o período da previsão:\n1. Hoje\n2. Amanhã\n3. Próximos 3 dias"
    await update.message.reply_text(opcoes)
    return 1

async def receber_opcao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    opcao = update.message.text.strip()
    hoje = datetime.date.today()
    if opcao == "1":
        resposta = await obter_previsao_completa(hoje.isoformat())
        await update.message.reply_text(resposta)
    elif opcao == "2":
        resposta = await obter_previsao_completa((hoje + datetime.timedelta(days=1)).isoformat())
        await update.message.reply_text(resposta)
    elif opcao == "3":
        for i in range(3):
            data = (hoje + datetime.timedelta(days=i)).isoformat()
            resposta = await obter_previsao_completa(data)
            await update.message.reply_text(resposta)
    else:
        await update.message.reply_text("Opção inválida. Envie /previsao para tentar novamente.")
    return ConversationHandler.END

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("previsao", previsao)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_opcao)]
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    print("✅ Iniciando SurfCheck Bot...")
    app.run_polling()
