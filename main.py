import os
import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv
from surfcheck import get_forecast_text

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Configuração de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Função para lidar com o comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Comando /start chamado por %s", update.effective_user.username)
    await update.message.reply_text(
        "\U0001F30A Olá! Eu sou o SurfCheck Bot.\nEnvie /previsao para saber as condições em Itaúna - Saquarema."
    )

# Função para lidar com o comando /previsao
async def previsao(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Comando /previsao chamado por %s", update.effective_user.username)
    try:
        message = (
            "Escolha uma opção de previsão para Itaúna - Saquarema:\n"
            "1. Hoje\n"
            "2. Amanhã\n"
            "3. Próximos 3 dias"
        )
        await update.message.reply_text(message)
        context.user_data["state"] = "awaiting_day_selection"
        logger.info("Estado de seleção de dia definido")
    except Exception as e:
        logger.exception("Erro ao processar comando /previsao: %s", str(e))
        await update.message.reply_text("Erro ao obter a previsão. Tente novamente mais tarde.")

# Lógica para lidar com a escolha do usuário após o /previsao
async def handle_response(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_input = update.message.text.strip()
    logger.info("Resposta do usuário: %s", user_input)

    try:
        if context.user_data.get("state") == "awaiting_day_selection":
            if user_input not in ["1", "2", "3"]:
                await update.message.reply_text("Escolha inválida. Por favor, envie 1, 2 ou 3.")
                return

            dias = {"1": 1, "2": 1, "3": 3}[user_input]
            hoje = datetime.now().date()
            data_inicio = hoje if user_input == "1" else hoje + timedelta(days=1)

            logger.info("Chamando get_forecast_text com %s dias a partir de %s", dias, data_inicio)
            forecast = await get_forecast_text("Itauna", data_inicio.isoformat(), dias)
            logger.info("Previsão obtida com sucesso")

            await update.message.reply_text(forecast)
            context.user_data.pop("state", None)
        else:
            await update.message.reply_text("Envie o comando /previsao para iniciar.")
    except Exception as e:
        logger.exception("Erro ao gerar previsão: %s", str(e))
        await update.message.reply_text("Erro ao obter a previsão. Tente novamente mais tarde.")

if __name__ == "__main__":
    try:
        logger.info("Iniciando SurfCheck Bot...")
        app = ApplicationBuilder().token(BOT_TOKEN).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("previsao", previsao))
        app.add_handler(CommandHandler("1", handle_response))
        app.add_handler(CommandHandler("2", handle_response))
        app.add_handler(CommandHandler("3", handle_response))
        app.add_handler(CommandHandler(None, handle_response))

        app.run_polling()
    except Exception as e:
        logger.exception("Erro ao iniciar o bot: %s", str(e))
