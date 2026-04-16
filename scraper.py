import feedparser
import requests
from bs4 import BeautifulSoup
import sqlite3
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from datetime import datetime


# +--------------------+
#   TWITTER
# +--------------------+
def scrapear_twitter():
    print("🐦 Buscando tweets (modo opcional)...")

    nuevas = []
    con = None

    try:
        import snscrape.modules.twitter as sntwitter
    except Exception:
        print("⚠ snscrape no disponible")
        return []

    try:
        con = get_connection()
        scraper = sntwitter.TwitterSearchScraper("noticias chile")

        count = 0

        for tweet in scraper.get_items():
            try:
                texto = (tweet.content or "").strip()
                link = tweet.url

                if len(texto) < 80:
                    continue

                if not es_noticia_importante(texto):
                    continue

                nid = hashlib.md5(link.encode()).hexdigest()
                score = puntaje_noticia(texto)

                if guardar_noticia(con, nid, texto[:200], "X", link, "Social"):
                    nuevas.append({
                        "titulo": texto[:200],
                        "fuente": "X",
                        "link": link,
                        "score": score,
                        "region": "Social"
                    })

                count += 1

                # 👇 ultra limitado para no afectar scraping
                if len(nuevas) >= 2 or count >= 20:
                    break

            except Exception:
                continue

    except Exception as e:
        print("⚠ Twitter error:", e)

    finally:
        if con:
            con.close()

    return nuevas

# +--------------------+
#   LÓGICA
# +--------------------+
def puntaje_noticia(titulo):
    t = titulo.lower()
    score = 0

    # palabras muy importantes (alto impacto)
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

    # palabras relevantes
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

    # basura
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

    # longitud (más info = más serio)
    if len(titulo) > 80:
        score += 1

    return score


# +--------------------+
#  Noticias importantes
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

# Noticias no tan importantes
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
# Fuentes RSS chilenas
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

FUENTE_REGION_MAP = {
    "Arica": "Arica",
    "Iquique": "Iquique",
    "BioBioChile": "Nacional",
    "Emol": "Nacional",
}

FUENTES_NACIONALES = [
    # Global
    {
        "nombre": "Google News Chile",
        "rss": "https://news.google.com/rss/search?q=chile",
    },
    # Locales
    {"nombre": "BioBioChile", "rss": "https://www.biobiochile.cl/feed/"},
    {"nombre": "T13", "rss": "https://www.t13.cl/rss"},
    {"nombre": "Emol", "rss": "https://www.emol.com/rss/"},
    {"nombre": "La Tercera", "rss": "https://www.latercera.com/feed/"},
    {"nombre": "El Mostrador", "rss": "https://elmostrador.cl/feed/"},
    {"nombre": "CNN Chile", "rss": "https://www.cnnchile.com/feed/"},
    {"nombre": "Cooperativa","rss": "https://www.cooperativa.cl/noticias/site/tax/port/all/rss____1.xml",},
    {"nombre": "24 Horas", "rss": "https://www.24horas.cl/feeds/news.xml"},
    {"nombre": "ADN Radio", "rss": "https://www.adnradio.cl/rss/"},
    {"nombre": "Publimetro", "rss": "https://www.publimetro.cl/cl/rss.xml"},
    {"nombre": "El Dínamo", "rss": "https://www.eldinamo.cl/feed/"},
    {"nombre": "Ex-Ante", "rss": "https://www.ex-ante.cl/feed/"},
]


def obtener_region(nombre_fuente):
    regiones = [
        "Arica",
        "Iquique",
        "Antofagasta",
        "Valparaíso",
        "Santiago",
        "Rancagua",
        "Concepción",
        "Temuco",
        "Valdivia",
        "Puerto Montt",
        "Punta Arenas",
    ]

    for r in regiones:
        if r.lower() in nombre_fuente.lower():
            return r

    return "Nacional"


def es_noticia_importante(titulo):
    t = titulo.lower()

    # descartar basura
    for palabra in PALABRAS_BASURA:
        if palabra in t:
            return False

    # debe tener al menos 1 keyword importante
    for palabra in KEYWORDS_IMPORTANTE:
        if palabra in t:
            return True

    return False


# +--------------------+
#   BASE DE DATOS
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


def noticia_ya_vista(con, noticia_id):
    return con.execute("SELECT 1 FROM noticias WHERE id=?", (noticia_id,)).fetchone()


def formatear_fecha(fecha_iso):
    try:
        dt = datetime.fromisoformat(fecha_iso)
        return dt.strftime("%d-%m-%Y %H:%M")
    except:
        return fecha_iso

def guardar_noticia(con, noticia_id, titulo, fuente, link, region=None, fecha=None):
    if region is None:
        region = obtener_region(fuente)

    if fecha is None:
        fecha = datetime.now().isoformat()
    
    cur = con.execute(
        "INSERT OR IGNORE INTO noticias VALUES (?,?,?,?,?,?)",
        (noticia_id, titulo, fuente, link, datetime.now().isoformat(), region),
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
        feed = feedparser.parse(fuente["rss"], timeout=10)

        for entry in feed.entries[:10]:
            titulo = entry.get("title", "").strip()
            if entry.get("published_parsed"):
                fecha = datetime(*entry.published_parsed[:6]).isoformat()
            elif entry.get("updated_parsed"):
                fecha = datetime(*entry.updated_parsed[:6]).isoformat()
            else:
                fecha = "desconocida"
            link = entry.get("link", "").strip()

            if not titulo or not link:
                continue

            if not es_noticia_importante(titulo):
                continue

            nid = hashlib.md5(link.encode()).hexdigest()
            score = puntaje_noticia(titulo)
            region = obtener_region(fuente["nombre"])

            insertado = guardar_noticia(
                con, nid, titulo, fuente["nombre"], link, region
            )

            if insertado:
                nuevas.append(
                    {
                        "titulo": titulo,
                        "fuente": fuente["nombre"],
                        "link": link,
                        "score": score,
                        "region": region,
                    }
                )

    except Exception as e:
        print(f"Error en {fuente['nombre']}: {e}")

    finally:
        con.close()

    print(f"✔ {fuente['nombre']} → {len(nuevas)} nuevas")
    return nuevas


# +--------------------+
#   MAIN SCRAPPER
# +--------------------+
def scrapear():
    print("🚀 Iniciando scraping...")
    init_db()
    nuevas = []

    TODAS_LAS_FUENTES = FUENTES_NACIONALES + FUENTES_REGIONALES

    print(f"🌐 Fuentes a procesar: {len(TODAS_LAS_FUENTES)}")

    # PARALLEL RSS
    with ThreadPoolExecutor(max_workers=5) as executor:
        resultados = executor.map(procesar_fuente, TODAS_LAS_FUENTES)

    for r in resultados:
        nuevas.extend(r)

    print(f"📰 Noticias RSS encontradas: {len(nuevas)}")

    # TWITTER
    print("🐦 Scrapeando Twitter...")
    try:
        nuevas.extend(scrapear_twitter())
    except:
        print("⚠ Twitter no disponible")

    print(f"📊 Total noticias antes de ordenar: {len(nuevas)}")
    nuevas.sort(key=lambda x: x["score"], reverse=True)

    print(f"✅ Top noticias seleccionadas: {len(nuevas[:20])}")

    return nuevas[:20]
