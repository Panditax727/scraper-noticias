import feedparser
import requests
from bs4 import BeautifulSoup
import sqlite3
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# +--------------------+
#  LÓGICA DE SCORING
# +--------------------+

def puntaje_noticia(titulo):
    t = titulo.lower()
    score = 0

    fuertes = [
        "presidente",
        "gobierno",
        "crisis",
        "emergencia",
        "terremoto",
        "incendio",
        "delito",
        "asesinato",
    ]

    medias = [
        "economía",
        "inflación",
        "ley",
        "reforma",
        "salud",
        "educación",
        "transporte",
        "carabineros",
        "pdi",
    ]

    basura = ["farándula", "famoso", "viral", "increíble", "no creerás", "video"]

    for palabra in fuertes:
        if palabra in t:
            score += 5

    for palabra in medias:
        if palabra in t:
            score += 3

    for palabra in basura:
        if palabra in t:
            score -= 5

    if len(titulo) > 80:
        score += 1

    return score


# +--------------------+
#  FILTROS
# +--------------------+

KEYWORDS_IMPORTANTE = [
    "gobierno",
    "presidente",
    "ministro",
    "congreso",
    "ley",
    "reforma",
    "economía",
    "inflación",
    "crisis",
    "emergencia",
    "terremoto",
    "incendio",
    "delito",
    "carabineros",
    "pdi",
    "salud",
    "educación",
    "transporte",
    "chile",
    "nacional",
]

PALABRAS_BASURA = [
    "famoso",
    "farándula",
    "reality",
    "viral",
    "increíble",
    "no creerás",
    "impactante",
    "video",
    "fotos",
]


# +--------------------+
#  FUENTES RSS
# +--------------------+

FUENTES_REGIONALES = [
    # Norte
    {"nombre": "Arica", "rss": "https://www.soychile.cl/arica/rss/"},
    {"nombre": "Iquique", "rss": "https://www.soychile.cl/iquique/rss/"},
    {"nombre": "Antofagasta", "rss": "https://www.soychile.cl/antofagasta/rss/"},
    # Centro
    {"nombre": "Valparaíso", "rss": "https://www.soychile.cl/valparaiso/rss/"},
    {"nombre": "Santiago", "rss": "https://www.soychile.cl/santiago/rss/"},
    {"nombre": "Rancagua", "rss": "https://www.soychile.cl/rancagua/rss/"},
    # Sur
    {"nombre": "Concepción", "rss": "https://www.soychile.cl/concepcion/rss/"},
    {"nombre": "Temuco", "rss": "https://www.soychile.cl/temuco/rss/"},
    {"nombre": "Valdivia", "rss": "https://www.soychile.cl/valdivia/rss/"},
    {"nombre": "Puerto Montt", "rss": "https://www.soychile.cl/puertomontt/rss/"},
    # Extremo sur
    {"nombre": "Punta Arenas", "rss": "https://www.soychile.cl/puntaarenas/rss/"},
]

FUENTES_NACIONALES = [
    {"nombre": "Google News Chile", "rss": "https://news.google.com/rss/search?q=chile"},

    # BioBioChile — URL original daba 404, nueva via FeedBurner
    # {"nombre": "BioBioChile", "rss": "https://www.biobiochile.cl/feed/"},
    {"nombre": "BioBioChile", "rss": "https://feeds.feedburner.com/radiobiobio/NNeJ"},

    # T13 — URL original daba 404, nueva URL confirmada
    # {"nombre": "T13", "rss": "https://www.t13.cl/rss"},
    {"nombre": "T13", "rss": "https://www.t13.cl/rss/"},

    # Emol — daba connection reset, misma URL (puede ser bloqueo de IP, se mantiene)
    {"nombre": "Emol", "rss": "https://www.emol.com/rss/"},

    # La Tercera — URL original daba 404, nueva URL confirmada
    # {"nombre": "La Tercera", "rss": "https://www.latercera.com/feed/"},
    {"nombre": "La Tercera", "rss": "https://www.latercera.com/arc/outboundfeeds/feeds/rss/?outputType=xml"},

    # El Mostrador — URL original daba 404, nueva URL confirmada
    # {"nombre": "El Mostrador", "rss": "https://elmostrador.cl/feed/"},
    {"nombre": "El Mostrador", "rss": "https://www.elmostrador.cl/noticias/feed/"},

    {"nombre": "CNN Chile", "rss": "https://www.cnnchile.com/feed/"},
    {"nombre": "Cooperativa", "rss": "https://www.cooperativa.cl/noticias/site/tax/port/all/rss____1.xml"},

    # 24 Horas — URL original daba 404, nueva URL confirmada
    # {"nombre": "24 Horas", "rss": "https://www.24horas.cl/feeds/news.xml"},
    {"nombre": "24 Horas", "rss": "https://www.24horas.cl/feed/"},

    # ADN Radio — URL original daba 404, nueva URL confirmada
    # {"nombre": "ADN Radio", "rss": "https://www.adnradio.cl/rss/"},
    {"nombre": "ADN Radio", "rss": "https://www.adnradio.cl/feed/"},

    # Publimetro — URL original daba 404, nueva URL confirmada
    # {"nombre": "Publimetro", "rss": "https://www.publimetro.cl/cl/rss.xml"},
    {"nombre": "Publimetro", "rss": "https://www.publimetro.cl/arc/outboundfeeds/rss/?outputType=xml"},

    # El Dínamo — URL original daba 404, nueva URL confirmada
    # {"nombre": "El Dínamo", "rss": "https://www.eldinamo.cl/feed/"},
    {"nombre": "El Dínamo", "rss": "https://www.eldinamo.cl/noticias/feed/"},

    {"nombre": "Ex-Ante", "rss": "https://www.ex-ante.cl/feed/"},

    # Fuentes nuevas agregadas
    {"nombre": "The Clinic", "rss": "https://www.theclinic.cl/feed/"},
    {"nombre": "Diario Financiero", "rss": "https://www.df.cl/noticias/site/list/port/rss.xml"},
    {"nombre": "El Siglo", "rss": "https://elsiglo.cl/feed/"},
    {"nombre": "La Nación", "rss": "https://www.lanacion.cl/feed/"},
]


# +--------------------+
#  HELPERS
# +--------------------+

def obtener_region(nombre_fuente):
    regiones = [
        "Arica", "Iquique", "Antofagasta", "Valparaíso", "Santiago",
        "Rancagua", "Concepción", "Temuco", "Valdivia", "Puerto Montt",
        "Punta Arenas",
    ]
    for r in regiones:
        if r.lower() in nombre_fuente.lower():
            return r
    return "Nacional"


def es_noticia_importante(titulo):
    t = titulo.lower()
    for palabra in PALABRAS_BASURA:
        if palabra in t:
            return False
    for palabra in KEYWORDS_IMPORTANTE:
        if palabra in t:
            return True
    return False


# +--------------------+
#  BASE DE DATOS
# +--------------------+

DB_PATH = "/app/data/noticias.db"


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS noticias (
            id TEXT PRIMARY KEY,
            titulo TEXT,
            fuente TEXT,
            link TEXT,
            fecha TEXT,
            region TEXT
        )
        """
    )
    con.commit()
    con.close()


def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)


def guardar_noticia(con, noticia_id, titulo, fuente, link, region=None, fecha=None):
    if region is None:
        region = obtener_region(fuente)
    if fecha is None:
        fecha = datetime.now().isoformat()

    cur = con.execute(
        "INSERT OR IGNORE INTO noticias VALUES (?,?,?,?,?,?)",
        (noticia_id, titulo, fuente, link, fecha, region),
    )
    con.commit()
    return cur.rowcount > 0


# +--------------------+
#  THREAD WORKER
# +--------------------+

def procesar_fuente(fuente):
    print(f"🔎 Procesando fuente: {fuente['nombre']}")
    con = get_connection()
    nuevas = []

    try:
        # ✅ FIX: feedparser no acepta timeout — usamos requests para descargar
        # el feed con timeout real y luego lo parseamos.
        resp = requests.get(fuente["rss"], timeout=10, headers={"User-Agent": "scraper-noticias/1.0"})
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)

        for entry in feed.entries[:10]:
            titulo = entry.get("title", "").strip()

            if entry.get("published_parsed"):
                fecha = datetime(*entry.published_parsed[:6]).isoformat()
            elif entry.get("updated_parsed"):
                fecha = datetime(*entry.updated_parsed[:6]).isoformat()
            else:
                fecha = datetime.now().isoformat()

            link = entry.get("link", "").strip()

            if not titulo or not link:
                continue

            if not es_noticia_importante(titulo):
                continue

            nid = hashlib.md5(link.encode()).hexdigest()
            score = puntaje_noticia(titulo)
            region = obtener_region(fuente["nombre"])

            insertado = guardar_noticia(con, nid, titulo, fuente["nombre"], link, region, fecha)
            if insertado:
                nuevas.append({
                    "titulo": titulo,
                    "fuente": fuente["nombre"],
                    "link": link,
                    "fecha": fecha,
                    "score": score,
                    "region": region,
                })

    except requests.RequestException as e:
        print(f"⚠ Error de red en {fuente['nombre']}: {e}")
    except Exception as e:
        print(f"⚠ Error procesando {fuente['nombre']}: {e}")
    finally:
        con.close()

    print(f"✔ {fuente['nombre']} → {len(nuevas)} nuevas")
    return nuevas


# +--------------------+
#  MAIN SCRAPER
# +--------------------+

def scrapear():
    print("🚀 Iniciando scraping...")
    init_db()

    nuevas = []
    TODAS_LAS_FUENTES = FUENTES_NACIONALES + FUENTES_REGIONALES
    print(f"🌐 Fuentes a procesar: {len(TODAS_LAS_FUENTES)}")

    with ThreadPoolExecutor(max_workers=5) as executor:
        resultados = executor.map(procesar_fuente, TODAS_LAS_FUENTES)
        for r in resultados:
            nuevas.extend(r)

    print(f"📰 Total noticias encontradas: {len(nuevas)}")
    nuevas.sort(key=lambda x: x["score"], reverse=True)
    print(f"✅ Top noticias seleccionadas: {len(nuevas[:20])}")

    return nuevas[:20]