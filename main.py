import os
import datetime
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")

DIRECTIONS = ['N', 'NE', 'L', 'SE', 'S', 'SO', 'O', 'NO']

def graus_para_direcao(graus):
    idx = round(graus / 45) % 8
    return DIRECTIONS[idx]

def classificar_surf(altura, periodo, vento, direcao_vento, direcao_swell):
    if altura < 0.5 or periodo < 6:
        return 1, "Condições fracas, mar pequeno ou desorganizado."
    elif altura < 1.0 and periodo < 8:
        return 2, "Condições regulares, com ondas pequenas e alguma formação."
    elif altura < 1.5 and periodo < 10:
        return 3, "Surf ok, com ondas divertidas e razoável formação."
    elif altura < 2.0 or periodo < 12:
        return 4, "Boas condições, com ondas maiores e mais potentes."
    else:
        return 5, "Excelente dia de surf, com ondas potentes e bem formadas!"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🌊 Olá! Eu sou o SurfCheck Bot.\n"
        "Envie /previsao para saber as condições em Itaúna - Saquarema."
    )

async def previsao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Qual dia deseja a previsão?\n1. Hoje\n2. Amanhã\n3. Próximos 3 dias")
    return 1

async def processar_previsao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    escolha = update.message.text.strip()

    if escolha not in ["1", "2", "3"]:
        await update.message.reply_text("Por favor, envie 1, 2 ou 3 para escolher o dia da previsão.")
        return 1

    dias = {"1": 0, "2": 1, "3": 3}[escolha]
    hoje = datetime.date.today()
    data_inicio = hoje + datetime.timedelta(days=0 if dias == 0 else 1)
    data_fim = hoje + datetime.timedelta(days=dias)

    try:
        previsao = await obter_previsao(data_inicio, data_fim)
        await update.message.reply_text(previsao)
    except Exception as e:
        print(e)
        await update.message.reply_text("Erro ao obter a previsão. Tente novamente mais tarde.")

    return ConversationHandler.END

async def obter_previsao(inicio: datetime.date, fim: datetime.date) -> str:
    lat, lon = -22.93668, -42.48337
    base_url_marine = (
        f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}"
        f"&hourly=wave_height,wind_wave_height,wind_wave_direction,wave_direction"
        f"&timezone=America/Sao_Paulo&start_date={inicio}&end_date={fim}"
    )
    base_url_forecast = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        f"&hourly=wind_speed_10m,wind_direction_10m"
        f"&timezone=America/Sao_Paulo&start_date={inicio}&end_date={fim}"
    )

    async with httpx.AsyncClient() as client:
        r1 = await client.get(base_url_marine)
        r2 = await client.get(base_url_forecast)
        data1 = r1.json()
        data2 = r2.json()

    texto = f"📍 Previsão para Itaúna – Saquarema\n🗓️ De {inicio.strftime('%d/%m')} até {fim.strftime('%d/%m')}\n\n"
    horarios = data1["hourly"]["time"]
    alturas = data1["hourly"]["wave_height"]
    periodos = data1["hourly"]["wind_wave_height"]
    swell_dir = data1["hourly"]["wave_direction"]
    vento_dir = data2["hourly"]["wind_direction_10m"]
    vento_speed = data2["hourly"]["wind_speed_10m"]

    por_dia = {}

    for i, h in enumerate(horarios):
        data_hora = datetime.datetime.fromisoformat(h)
        dia = data_hora.date()
        if dia not in por_dia:
            por_dia[dia] = {"alturas": [], "periodos": [], "swell": [], "vento_dir": [], "vento_speed": []}
        por_dia[dia]["alturas"].append(alturas[i])
        por_dia[dia]["periodos"].append(periodos[i])
        por_dia[dia]["swell"].append(swell_dir[i])
        por_dia[dia]["vento_dir"].append(vento_dir[i])
        por_dia[dia]["vento_speed"].append(vento_speed[i])

    for dia, val in por_dia.items():
        altura = round(max(val["alturas"]), 2)
        periodo = round(sum(val["periodos"]) / len(val["periodos"]), 1)
        swell_cardinal = graus_para_direcao(sum(val["swell"]) / len(val["swell"]))
        vento_cardinal = graus_para_direcao(sum(val["vento_dir"]) / len(val["vento_dir"]))
        vento = round(sum(val["vento_speed"]) / len(val["vento_speed"]), 1)
        estrelas, analise = classificar_surf(altura, periodo, vento, vento_cardinal, swell_cardinal)
        texto += f"📅 {dia.strftime('%d/%m')} – {estrelas}⭐\n"
        texto += f"🌊 Altura: {altura}m | 🌬️ Vento: {vento} km/h ({vento_cardinal}) | 🌊 Swell: {swell_cardinal}\n"
        texto += f"📈 Período médio: {periodo}s\n"
        texto += f"🔍 {analise}\n\n"

    return texto.strip()

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("previsao", previsao)],
        states={1: [MessageHandler(filters.TEXT & ~filters.COMMAND, processar_previsao)]},
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    print("✅ Iniciando SurfCheck Bot...")
    app.run_polling()
