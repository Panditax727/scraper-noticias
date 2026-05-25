import os
import sqlite3
from datetime import datetime, date, timedelta
import email.utils
import requests
import telebot
import logging
import re

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
        return None
    try:
        return datetime.fromisoformat(fecha)
    except:
        pass
    try:
        return email.utils.parsedate_to_datetime(fecha)
    except:
        return None


def formato_mensaje(titulo, fuente, fecha_dt, link):
    if fecha_dt:
        solo_fecha = fecha_dt.strftime("%d-%m-%Y")
        solo_hora = fecha_dt.strftime("%I:%M %p")
    else:
        solo_fecha = "Sin fecha"
        solo_hora = "—"

    if link:
        return (
            f"📰 *{fuente}*\n"
            f"━━━━━━━━━━━━━━\n"
            f"📌 {titulo}\n\n"
            f"📅 Fecha: {solo_fecha}\n"
            f"🕒 Hora: {solo_hora}\n"
            f"👉 [Leer noticia]({link})"
        )
    else:
        return (
            f"📰 *{fuente}*\n"
            f"━━━━━━━━━━━━━━\n"
            f"📌 {titulo}\n\n"
            f"📅 Fecha: {solo_fecha}\n"
            f"🕒 Hora: {solo_hora}"
        )


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
                "disable_web_page_preview": False,
            },
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"⚠ Error enviando mensaje: {e}")


def enviar_filas(chat_id, rows, encabezado):
    if not rows:
        enviar_mensaje(chat_id, "🔍 No encontré noticias con ese filtro.")
        return
    enviar_mensaje(chat_id, encabezado)
    for titulo, fuente, link, fecha, score in rows:
        fecha_dt = formatear_fecha(fecha)
        enviar_mensaje(chat_id, formato_mensaje(titulo, fuente, fecha_dt, link))


# +--------------------+
#  PARSEO DE FILTROS
# +--------------------+

TRAMOS = {
    "mañana":  (6, 12),
    "manana":  (6, 12),
    "tarde":   (12, 18),
    "noche":   (18, 24),
    "madrugada": (0, 6),
}

CATEGORIAS = {
    "gobierno":    ["gobierno", "presidente", "ministro", "congreso"],
    "economia":    ["economía", "inflación", "dólar", "pib", "financiero"],
    "seguridad":   ["delito", "carabineros", "pdi", "crimen", "robo", "asesinato"],
    "salud":       ["salud", "hospital", "enfermedad", "pandemia", "médico"],
    "educacion":   ["educación", "escuela", "universidad", "estudiante"],
    "emergencia":  ["terremoto", "incendio", "alud", "inundación", "emergencia", "catástrofe"],
    "transporte":  ["transporte", "metro", "bus", "tren", "autopista"],
    "economia":    ["economía", "inflación", "dólar", "financiero", "pib"],
}

def parsear_filtro(args):
    """
    Interpreta los argumentos del comando /ver y devuelve
    un dict con los filtros aplicables: fecha, tramo, categoria.
    Ejemplos:
        /ver hoy
        /ver ayer
        /ver 25-05-2026
        /ver mañana
        /ver tarde
        /ver gobierno
        /ver hoy tarde
        /ver 25-05-2026 noche
    """
    filtro = {"fecha_desde": None, "fecha_hasta": None, "tramo": None, "categoria": None}

    if not args:
        return filtro  # sin filtro = todo el ciclo actual

    tokens = args.lower().split()
    hoy = date.today()

    for token in tokens:
        # — Fecha relativa
        if token == "hoy":
            filtro["fecha_desde"] = datetime.combine(hoy, datetime.min.time())
            filtro["fecha_hasta"] = datetime.combine(hoy, datetime.max.time())
        elif token == "ayer":
            ayer = hoy - timedelta(days=1)
            filtro["fecha_desde"] = datetime.combine(ayer, datetime.min.time())
            filtro["fecha_hasta"] = datetime.combine(ayer, datetime.max.time())

        # — Fecha exacta dd-mm-yyyy
        elif re.match(r"\d{2}-\d{2}-\d{4}", token):
            try:
                dia = datetime.strptime(token, "%d-%m-%Y")
                filtro["fecha_desde"] = datetime.combine(dia.date(), datetime.min.time())
                filtro["fecha_hasta"] = datetime.combine(dia.date(), datetime.max.time())
            except:
                pass

        # — Tramo horario
        elif token in TRAMOS:
            filtro["tramo"] = TRAMOS[token]

        # — Categoría
        elif token in CATEGORIAS:
            filtro["categoria"] = CATEGORIAS[token]

    return filtro


def construir_query(filtro, tabla="sesion_noticias"):
    """Construye la query SQL y parámetros según el filtro."""
    condiciones = []
    params = []

    if filtro["fecha_desde"] and filtro["fecha_hasta"]:
        condiciones.append("fecha BETWEEN ? AND ?")
        params.append(filtro["fecha_desde"].isoformat())
        params.append(filtro["fecha_hasta"].isoformat())

    if filtro["tramo"]:
        hora_ini, hora_fin = filtro["tramo"]
        condiciones.append("CAST(strftime('%H', fecha) AS INTEGER) BETWEEN ? AND ?")
        params.append(hora_ini)
        params.append(hora_fin - 1)

    if filtro["categoria"]:
        keywords = filtro["categoria"]
        sub = " OR ".join([f"LOWER(titulo) LIKE ?" for _ in keywords])
        condiciones.append(f"({sub})")
        for kw in keywords:
            params.append(f"%{kw}%")

    where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
    query = f"SELECT titulo, fuente, link, fecha, score FROM {tabla} {where} ORDER BY score DESC"
    return query, params


def descripcion_filtro(filtro, args):
    partes = []
    if filtro["fecha_desde"]:
        partes.append(f"📅 {filtro['fecha_desde'].strftime('%d-%m-%Y')}")
    if filtro["tramo"]:
        nombre_tramo = next((k for k, v in TRAMOS.items() if v == filtro["tramo"]), "")
        partes.append(f"🕒 {nombre_tramo.capitalize()}")
    if filtro["categoria"]:
        nombre_cat = next((k for k, v in CATEGORIAS.items() if v == filtro["categoria"]), "")
        partes.append(f"🏷 {nombre_cat.capitalize()}")
    if not partes:
        partes.append("último ciclo")
    return " · ".join(partes)


# +--------------------+
#  FUNCIONES PÚBLICAS (usadas por main.py)
# +--------------------+

def enviar_noticia(noticia):
    fecha_dt = formatear_fecha(noticia.get("fecha"))
    link = noticia.get("link", "")
    enviar_mensaje(CHAT_ID, formato_mensaje(noticia["titulo"], noticia["fuente"], fecha_dt, link))


def enviar_resumen(total, top_noticias):
    lines = [f"✅ *Scraping completado* — {total} noticias nuevas\n"]

    if top_noticias:
        lines.append("📌 *Top 3 más relevantes:*")
        for i, n in enumerate(top_noticias[:3], 1):
            titulo = n['titulo'][:60] + "..." if len(n['titulo']) > 60 else n['titulo']
            lines.append(f"{i}. [{titulo}]({n['link']})")

    lines.append("\n💡 *Comandos disponibles:*")
    lines.append("/ver — Todo el último ciclo")
    lines.append("/ver hoy — Noticias de hoy")
    lines.append("/ver ayer — Noticias de ayer")
    lines.append("/ver 25-05-2026 — Fecha específica")
    lines.append("/ver mañana · tarde · noche — Por tramo horario")
    lines.append("/ver gobierno · economia · seguridad · salud · educacion · emergencia · transporte — Por categoría")
    lines.append("/top — Top 3 más relevantes")
    lines.append("/resumen — Noticias por fuente")
    lines.append("/ayuda — Ver todos los comandos")

    enviar_mensaje(CHAT_ID, "\n".join(lines))


# +--------------------+
#  COMANDOS DEL BOT
# +--------------------+

@bot.message_handler(commands=["start", "ayuda", "help"])
def cmd_ayuda(message):
    texto = (
        "🤖 *Bot de Noticias Chile*\n\n"
        "*Filtros disponibles para /ver:*\n\n"
        "📅 *Por fecha:*\n"
        "  /ver hoy\n"
        "  /ver ayer\n"
        "  /ver 25-05-2026\n\n"
        "🕒 *Por tramo horario:*\n"
        "  /ver madrugada — 00:00 a 06:00\n"
        "  /ver mañana — 06:00 a 12:00\n"
        "  /ver tarde — 12:00 a 18:00\n"
        "  /ver noche — 18:00 a 00:00\n\n"
        "🏷 *Por categoría:*\n"
        "  /ver gobierno\n"
        "  /ver economia\n"
        "  /ver seguridad\n"
        "  /ver salud\n"
        "  /ver educacion\n"
        "  /ver emergencia\n"
        "  /ver transporte\n\n"
        "🔀 *Combinados:*\n"
        "  /ver hoy tarde\n"
        "  /ver 25-05-2026 noche\n"
        "  /ver hoy gobierno\n\n"
        "*Otros comandos:*\n"
        "/top — Top 3 más relevantes\n"
        "/resumen — Noticias por fuente\n"
        "/ayuda — Mostrar esta ayuda"
    )
    enviar_mensaje(message.chat.id, texto)


@bot.message_handler(commands=["top"])
def cmd_top(message):
    try:
        con = get_connection()
        rows = con.execute(
            "SELECT titulo, fuente, link, fecha, score FROM sesion_noticias ORDER BY score DESC LIMIT 3"
        ).fetchall()
        con.close()
    except Exception as e:
        enviar_mensaje(message.chat.id, f"⚠ Error leyendo noticias: {e}")
        return

    enviar_filas(message.chat.id, rows, "📌 *Top 3 noticias más relevantes:*")


@bot.message_handler(commands=["ver", "mas"])
def cmd_ver(message):
    # Extraer argumentos: /ver [args]
    partes = message.text.strip().split(maxsplit=1)
    args = partes[1] if len(partes) > 1 else ""

    filtro = parsear_filtro(args)
    desc = descripcion_filtro(filtro, args)

    # Si no hay filtro de fecha, busca en sesion_noticias (último ciclo)
    # Si hay filtro de fecha, busca en la tabla histórica noticias
    tabla = "noticias" if filtro["fecha_desde"] else "sesion_noticias"

    try:
        con = get_connection()
        query, params = construir_query(filtro, tabla)
        rows = con.execute(query, params).fetchall()
        con.close()
    except Exception as e:
        enviar_mensaje(message.chat.id, f"⚠ Error leyendo noticias: {e}")
        return

    enviar_filas(message.chat.id, rows, f"📰 *Noticias — {desc}* ({len(rows)} encontradas)")


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

    get_user_logger(user_id).info(
        f"[CHAT_ID:{message.chat.id}] [USER:@{username}] [NAME:{nombre}] [TEXT:{texto_usuario}]"
    )
    print(
        f"[CHAT_ID:{message.chat.id}] [USER_ID:{user_id}] [USER:@{username}] [NAME:{nombre}] [TEXT:{texto_usuario}]",
        flush=True,
    )
    enviar_mensaje(message.chat.id, "No entendí ese comando. Usa /ayuda para ver los comandos disponibles.")


# +--------------------+
#  ENTRY POINT
# +--------------------+

if __name__ == "__main__":
    print("🤖 Bot de Telegram iniciado (modo escucha)...")
    bot.polling(none_stop=True)