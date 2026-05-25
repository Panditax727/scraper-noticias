import requests
import os
from datetime import datetime
import email.utils
import telebot
import logging

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

bot = telebot.TeleBot(TOKEN)

os.makedirs("logs", exist_ok=True)


def get_user_logger(user_id):
    logger = logging.getLogger(str(user_id))
    if not logger.handlers:
        handler = logging.FileHandler(f"logs/user_{user_id}.log", encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s | %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def formatear_fecha(fecha):
    if not fecha:
        return "Sin fecha"
    try:
        return datetime.fromisoformat(fecha).strftime("%d-%m-%Y %H:%M")
    except:
        pass
    try:
        parsed = email.utils.parsedate_to_datetime(fecha)
        return parsed.strftime("%d-%m-%Y %H:%M")
    except:
        return fecha


def enviar_noticia(noticia):
    fecha = noticia.get("fecha")
    texto = (
        f"*{noticia['fuente']}*\n"
        f"{noticia['titulo']}\n"
        f"🕒 {formatear_fecha(fecha)}\n"
        f"[Ver noticia]({noticia['link']})"
    )
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": texto,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False,
            },
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"⚠ Error enviando noticia '{noticia.get('titulo', '')}': {e}")


def enviar_resumen(total):
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": f"Scraper terminó: {total} noticias nuevas encontradas.",
            },
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"⚠ Error enviando resumen: {e}")


@bot.message_handler(func=lambda message: True)
def recibir_mensaje(message):
    texto_usuario = message.text
    user_id = message.from_user.id
    username = message.from_user.username or "sin_username"
    nombre = message.from_user.first_name

    user_logger = get_user_logger(user_id)
    user_logger.info(
        f"[CHAT_ID:{message.chat.id}] "
        f"[USER:@{username}] "
        f"[NAME:{nombre}] "
        f"[TEXT:{texto_usuario}]"
    )

    print(
        f"[CHAT_ID:{message.chat.id}] "
        f"[USER_ID:{user_id}] "
        f"[USER:@{username}] "
        f"[NAME:{nombre}] "
        f"[TEXT:{texto_usuario}]",
        flush=True,
    )


# ✅ FIX: bot.polling() removido del nivel de módulo.
# Ahora solo se inicia si ejecutas bot.py directamente (python bot.py),
# no cuando se importa desde main.py o run.py.
if __name__ == "__main__":
    print("🤖 Bot de Telegram iniciado (modo escucha)...")
    bot.polling()