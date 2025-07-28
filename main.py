import os
import datetime
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

def grau_para_letra(grau):
    if grau is None:
        return "?"
    direcoes = ["N", "NE", "L", "SE", "S", "SO", "O", "NO"]
    idx = round(grau / 45) % 8
    return direcoes[idx]

def classificar_onda(altura):
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

def calcular_estrelas(altura, periodo, vento, direcao_vento):
    if altura is None or periodo is None or vento is None:
        return 0
    estrelas = 1
    if 0.5 <= altura <= 2 and periodo >= 8:
        estrelas += 1
    if vento <= 10 and (direcao_vento in ["N", "NO", "NE", "L"]):
        estrelas += 1
    if estrelas > 3:
        estrelas = 3
    return estrelas

def texto_analise(estrelas):
    if estrelas == 1:
        return "Condições fracas, mar pequeno ou desorganizado."
    elif estrelas == 2:
        return "Condições razoáveis, pode render algumas boas ondas."
    else:
        return "Boas condições! Vale conferir, ondas com potencial."

async def previsao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Escolha o período da previsão:\n1. Hoje\n2. Amanhã\n3. Próximos 3 dias")

    def verificar_resposta(resposta):
        return resposta.text in ["1", "2", "3"]

    resposta = await context.application.bot.wait_for_message(chat_id=update.effective_chat.id, timeout=30, filters=verificar_resposta)

    if resposta is None:
        await update.message.reply_text("Tempo esgotado. Envie /previsao novamente.")
        return

    escolha = resposta.text
    hoje = datetime.date.today()
    if escolha == "1":
        datas = [hoje]
    elif escolha == "2":
        datas = [hoje + datetime.timedelta(days=1)]
    else:
        datas = [hoje + datetime.timedelta(days=i) for i in range(3)]

    latitude = -22.93668
    longitude = -42.48337
    tz = "America/Sao_Paulo"

    try:
        inicio = datas[0].strftime("%Y-%m-%d")
        fim = datas[-1].strftime("%Y-%m-%d")

        url_mar = f"https://marine-api.open-meteo.com/v1/marine?latitude={latitude}&longitude={longitude}&hourly=wave_height,wave_direction,swell_wave_period,wind_speed_10m,wind_direction_10m,swell_wave_direction&timezone={tz}&start_date={inicio}&end_date={fim}"
        async with httpx.AsyncClient() as client:
            resposta = await client.get(url_mar)
        dados = resposta.json()

        horas = dados["hourly"]["time"]
        altura_ondas = dados["hourly"]["wave_height"]
        direcao_swell = dados["hourly"]["swell_wave_direction"]
        periodo = dados["hourly"]["swell_wave_period"]
        vento = dados["hourly"]["wind_speed_10m"]
        direcao_vento = dados["hourly"]["wind_direction_10m"]

        previsao_txt = "📍 Previsão para Itaúna – Saquarema\n"
        if len(datas) > 1:
            previsao_txt += f"🗓️ De {datas[0].strftime('%d/%m')} até {datas[-1].strftime('%d/%m')}\n"
        previsao_txt += "\n"

        for dia in datas:
            dia_str = dia.strftime("%Y-%m-%d")
            indices = [i for i, h in enumerate(horas) if h.startswith(dia_str)]
            if not indices:
                continue
            altura_dia = sum([altura_ondas[i] for i in indices]) / len(indices)
            periodo_dia = sum([periodo[i] for i in indices if periodo[i] is not None]) / len(indices)
            vento_dia = sum([vento[i] for i in indices]) / len(indices)
            dir_vento_dia = grau_para_letra(sum([direcao_vento[i] for i in indices]) / len(indices))
            dir_swell_dia = grau_para_letra(sum([direcao_swell[i] for i in indices]) / len(indices))

            estrelas = calcular_estrelas(altura_dia, periodo_dia, vento_dia, dir_vento_dia)
            descricao = texto_analise(estrelas)

            previsao_txt += f"📅 {dia.strftime('%d/%m')} – {'⭐' * estrelas}\n"
            previsao_txt += f"🌊 Altura: {altura_dia:.2f}m | 🌬️ Vento: {vento_dia:.1f} km/h ({dir_vento_dia}) | 🌊 Swell: {dir_swell_dia}\n"
            previsao_txt += f"📈 Período médio: {periodo_dia:.1f}s\n"
            previsao_txt += f"🔍 {descricao}\n\n"

        await update.message.reply_text(previsao_txt)

    except Exception as e:
        print("Erro:", e)
        await update.message.reply_text("Erro ao obter a previsão. Tente novamente mais tarde.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("🌊 Olá! Eu sou o SurfCheck Bot.\nEnvie /previsao para saber as condições em Itaúna - Saquarema.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("previsao", previsao))
    print("✅ Iniciando SurfCheck Bot...")
    app.run_polling()
