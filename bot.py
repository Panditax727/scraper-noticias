import os
import sqlite3
from datetime import datetime
import email.utils
import requests
import telebot
import logging

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

bot = telebot.TeleBot(TOKEN)

DB_PATH = "/app/data/noticias.db"

os.makedirs("logs", exist_ok=True)

# +--------------------+
#  LOGGER
# +--------------------+

def get_user_logger(user_id):
    logger = logging.getLogger(str(user_id))
    if not logger.handlers:
        handler = logging.FileHandler(f"logs/user_{user_id}.log", encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s | %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


# +--------------------+
#  HELPERS
# +--------------------+

def formatear_fecha(fecha):
    if not fecha or fecha == "desconocida":
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


def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)


def enviar_mensaje(chat_id, texto, parse_mode="Markdown"):
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": texto,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"⚠ Error enviando mensaje: {e}")


# +--------------------+
#  FUNCIONES PÚBLICAS (usadas por main.py)
# +--------------------+

def enviar_noticia(noticia):
    fecha = noticia.get("fecha")
    link = noticia.get("link", "")

    if link:
        texto = (
            f"*{noticia['fuente']}*\n"
            f"{noticia['titulo']}\n"
            f"🕒 {formatear_fecha(fecha)}\n"
            f"[Ver noticia]({link})"
        )
    else:
        texto = (
            f"*{noticia['fuente']}*\n"
            f"{noticia['titulo']}\n"
            f"🕒 {formatear_fecha(fecha)}"
        )

    enviar_mensaje(CHAT_ID, texto)


def enviar_resumen(total, top_noticias):
    """Envía resumen con top 3 e instrucciones de comandos."""
    lines = [f"✅ *Scraping completado* — {total} noticias nuevas encontradas\n"]

    if top_noticias:
        lines.append("📌 *Top 3 más relevantes:*")
        for i, n in enumerate(top_noticias[:3], 1):
            lines.append(f"{i}. [{n['titulo'][:60]}...]({n['link']})" if len(n['titulo']) > 60 else f"{i}. [{n['titulo']}]({n['link']})")

    lines.append("\n💡 *Comandos disponibles:*")
    lines.append("/ver — Ver todas las noticias de este ciclo")
    lines.append("/top — Ver las top 3 más relevantes")
    lines.append("/resumen — Ver noticias agrupadas por fuente")

    enviar_mensaje(CHAT_ID, "\n".join(lines))


# +--------------------+
#  COMANDOS DEL BOT
# +--------------------+

@bot.message_handler(commands=["start", "ayuda", "help"])
def cmd_ayuda(message):
    texto = (
        "🤖 *Bot de Noticias Chile*\n\n"
        "Comandos disponibles:\n"
        "/ver — Ver todas las noticias del último ciclo\n"
        "/top — Ver las top 3 más relevantes\n"
        "/resumen — Ver noticias agrupadas por fuente\n"
        "/ayuda — Mostrar esta ayuda"
    )
    enviar_mensaje(message.chat.id, texto)


@bot.message_handler(commands=["top"])
def cmd_top(message):
    try:
        con = get_connection()
        rows = con.execute(
            """
            SELECT titulo, fuente, link, fecha, score
            FROM sesion_noticias
            ORDER BY score DESC
            LIMIT 3
            """
        ).fetchall()
        con.close()
    except Exception as e:
        enviar_mensaje(message.chat.id, f"⚠ Error leyendo noticias: {e}")
        return

    if not rows:
        enviar_mensaje(message.chat.id, "No hay noticias del último ciclo aún. Espera el próximo scraping.")
        return

    enviar_mensaje(message.chat.id, "📌 *Top 3 noticias más relevantes:*")
    for i, (titulo, fuente, link, fecha, score) in enumerate(rows, 1):
        texto = (
            f"*{i}. {fuente}*\n"
            f"{titulo}\n"
            f"🕒 {formatear_fecha(fecha)}\n"
            f"[Ver noticia]({link})"
        )
        enviar_mensaje(message.chat.id, texto)


@bot.message_handler(commands=["ver", "mas"])
def cmd_ver(message):
    try:
        con = get_connection()
        rows = con.execute(
            """
            SELECT titulo, fuente, link, fecha, score
            FROM sesion_noticias
            ORDER BY score DESC
            """
        ).fetchall()
        con.close()
    except Exception as e:
        enviar_mensaje(message.chat.id, f"⚠ Error leyendo noticias: {e}")
        return

    if not rows:
        enviar_mensaje(message.chat.id, "No hay noticias del último ciclo aún. Espera el próximo scraping.")
        return

    total = len(rows)
    enviar_mensaje(message.chat.id, f"📰 *{total} noticias del último ciclo:*")

    for titulo, fuente, link, fecha, score in rows:
        texto = (
            f"*{fuente}*\n"
            f"{titulo}\n"
            f"🕒 {formatear_fecha(fecha)}\n"
            f"[Ver noticia]({link})"
        )
        enviar_mensaje(message.chat.id, texto)


@bot.message_handler(commands=["resumen"])
def cmd_resumen(message):
    try:
        con = get_connection()
        rows = con.execute(
            """
            SELECT fuente, COUNT(*) as total
            FROM sesion_noticias
            GROUP BY fuente
            ORDER BY total DESC
            """
        ).fetchall()
        con.close()
    except Exception as e:
        enviar_mensaje(message.chat.id, f"⚠ Error leyendo noticias: {e}")
        return

    if not rows:
        enviar_mensaje(message.chat.id, "No hay noticias del último ciclo aún.")
        return

    lines = ["📊 *Noticias por fuente (último ciclo):*\n"]
    for fuente, total in rows:
        lines.append(f"• *{fuente}*: {total} noticia{'s' if total > 1 else ''}")

    lines.append("\nUsa /ver para ver todas o /top para las más relevantes.")
    enviar_mensaje(message.chat.id, "\n".join(lines))


# +--------------------+
#  HANDLER GENERAL
# +--------------------+

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

    enviar_mensaje(
        message.chat.id,
        "No entendí ese comando. Usa /ayuda para ver los comandos disponibles."
    )


# +--------------------+
#  ENTRY POINT
# +--------------------+

if __name__ == "__main__":
    print("🤖 Bot de Telegram iniciado (modo escucha)...")
    bot.polling(none_stop=True)