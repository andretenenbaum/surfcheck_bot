import os
import logging
from datetime import datetime, timedelta
import pytz
import httpx
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

picos = {
    "1": {
        "nome": "Itaúna – Saquarema",
        "latitude": -22.93668,
        "longitude": -42.48337
    }
}

keyboard_picos = [["1"]]
keyboard_periodos = [["1", "2", "3"]]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🌊 Olá! Eu sou o SurfCheck Bot.\nEnvie /previsao para saber as condições em Itaúna - Saquarema.")

async def previsao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Qual pico você deseja consultar?", reply_markup=ReplyKeyboardMarkup(keyboard_picos, one_time_keyboard=True, resize_keyboard=True))
    context.user_data['awaiting_pico'] = True

async def processar_resposta(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    texto = update.message.text

    if context.user_data.get('awaiting_pico'):
        if texto in picos:
            context.user_data['pico'] = texto
            context.user_data['awaiting_pico'] = False
            await update.message.reply_text("Deseja a previsão para:\n1. Hoje\n2. Amanhã\n3. Próximos 3 dias", reply_markup=ReplyKeyboardMarkup(keyboard_periodos, one_time_keyboard=True, resize_keyboard=True))
            context.user_data['awaiting_periodo'] = True
        else:
            await update.message.reply_text("Pico inválido. Tente novamente.")

    elif context.user_data.get('awaiting_periodo'):
        if texto in ["1", "2", "3"]:
            context.user_data['awaiting_periodo'] = False
            await obter_previsao(update, context, int(texto))
        else:
            await update.message.reply_text("Opção inválida. Tente novamente.")

async def obter_previsao(update: Update, context: ContextTypes.DEFAULT_TYPE, dias: int) -> None:
    pico_id = context.user_data.get('pico')
    if not pico_id:
        await update.message.reply_text("Pico não identificado. Envie /previsao novamente.")
        return

    pico = picos[pico_id]
    latitude = pico['latitude']
    longitude = pico['longitude']
    nome_pico = pico['nome']

    try:
        hoje = datetime.utcnow().date()
        if dias == 3:
            inicio = (hoje + timedelta(days=1)).isoformat()
            fim = (hoje + timedelta(days=3)).isoformat()
        else:
            inicio = hoje.isoformat() if dias == 1 else (hoje + timedelta(days=1)).isoformat()
            fim = inicio

        url = (
            f"https://marine-api.open-meteo.com/v1/marine?latitude={latitude}&longitude={longitude}"
            f"&hourly=wave_height,wave_direction,wind_speed,wind_direction,swells,swells_direction"
            f"&daily=wave_height_max,swells_period_max"
            f"&tide=true"
            f"&start_date={inicio}&end_date={fim}&timezone=UTC"
        )

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            data = response.json()

        if 'daily' not in data or 'wave_height_max' not in data['daily']:
            raise ValueError("Dados diários ausentes")

        texto = f"📍 Previsão para {nome_pico}\n🗓️ De {inicio} até {fim}\n"
        br_tz = pytz.timezone("America/Sao_Paulo")

        for i, dia in enumerate(data['daily']['time']):
            altura = data['daily']['wave_height_max'][i]
            periodo = data['daily']['swells_period_max'][i]
            condicao = avaliar_condicao(altura)
            estrelas = classificar_ondas(altura)

            texto += f"\n📅 {dia} – {estrelas}⭐"
            texto += f"\n🌊 Altura: {altura:.2f}m"
            texto += f" | 🌬️ Vento: {data['hourly']['wind_speed'][i*24]:.1f} km/h ({converter_direcao(data['hourly']['wind_direction'][i*24])})"
            texto += f" | 🌊 Swell: {converter_direcao(data['hourly']['swells_direction'][i*24])}"
            texto += f"\n📈 Período médio: {periodo:.1f}s"

            try:
                mares_dia = [t for t in data['tide']['extremes'] if t['timestamp'].startswith(dia)]
                if mares_dia:
                    cheia = next((m for m in mares_dia if m['type'] == 'high'), None)
                    vazia = next((m for m in mares_dia if m['type'] == 'low'), None)
                    if cheia and vazia:
                        hora_cheia = datetime.fromisoformat(cheia['timestamp']).astimezone(br_tz).strftime("%H:%M")
                        hora_vazia = datetime.fromisoformat(vazia['timestamp']).astimezone(br_tz).strftime("%H:%M")
                        diferenca = abs(cheia['height'] - vazia['height'])
                        texto += f"\n🌊 Maré: cheia às {hora_cheia}, vazia às {hora_vazia}, variação de {diferenca:.2f}m"
            except Exception as e:
                logging.warning(f"Falha ao obter maré: {e}")
                texto += "\n🌊 Maré: dados indisponíveis no momento."

            texto += f"\n🔍 {condicao}\n"

        await update.message.reply_text(texto)

    except Exception as e:
        logging.error(f"Erro ao obter previsão: {e}")
        await update.message.reply_text("Erro ao obter a previsão. Tente novamente mais tarde.")

def classificar_ondas(altura):
    if altura == 0:
        return 0
    elif altura < 0.5:
        return 1
    elif altura < 1:
        return 2
    elif altura < 1.5:
        return 3
    elif altura < 2:
        return 4
    else:
        return 5

def avaliar_condicao(altura):
    if altura == 0:
        return "Flat, sem ondas."
    elif altura < 0.5:
        return "Condições fracas, mar pequeno."
    elif altura < 1:
        return "Boas condições para iniciantes."
    elif altura < 1.5:
        return "Ondas com bom tamanho, atenção à formação."
    elif altura < 2:
        return "Mar grande, ideal para experientes."
    else:
        return "Ondas pesadas, apenas para os mais preparados."

def converter_direcao(graus):
    direcoes = ['N', 'NE', 'L', 'SE', 'S', 'SO', 'O', 'NO']
    idx = round(graus % 360 / 45) % 8
    return direcoes[idx]

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("previsao", previsao))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, processar_resposta))

    print("✅ Iniciando SurfCheck Bot...")
    app.run_polling()

if __name__ == '__main__':
    main()
