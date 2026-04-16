import requests
import os
from datetime import datetime
import email.utils
import telebot
import logging

TOKEN   = os.environ["TELEGRAM_TOKEN"]
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
        # ISO format
        return datetime.fromisoformat(fecha).strftime("%d-%m-%Y %H:%M")
    except:
        pass

    try:
        # RSS format (RFC 822)
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
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={
            "chat_id":    CHAT_ID,
            "text":       texto,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False
        },
        timeout=10
    )
    

def enviar_resumen(total):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text":    f"Scraper terminó: {total} noticias nuevas encontradas."
        },
        timeout=10
    )
    
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
        flush=True
    )
    
    # Reenviar mensaje
    # display_name = username or nombre or "usuario"
    #bot.reply_to(message)
    
bot.polling()
    