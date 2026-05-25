import sqlite3
from scraper import scrapear, DB_PATH, init_db
from bot import enviar_noticia, enviar_resumen
from collections import defaultdict


def guardar_sesion(noticias):
    """Guarda las noticias del ciclo actual en sesion_noticias para que el bot pueda consultarlas."""
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.execute("DROP TABLE IF EXISTS sesion_noticias")
    con.execute(
        """
        CREATE TABLE sesion_noticias (
            titulo TEXT,
            fuente TEXT,
            link TEXT,
            fecha TEXT,
            score INTEGER,
            region TEXT
        )
        """
    )
    for n in noticias:
        con.execute(
            "INSERT INTO sesion_noticias VALUES (?,?,?,?,?,?)",
            (n["titulo"], n["fuente"], n["link"], n.get("fecha", ""), n.get("score", 0), n.get("region", "Nacional")),
        )
    con.commit()
    con.close()


def correr():
    nuevas = scrapear()

    if not nuevas:
        print("Sin noticias nuevas.")
        return

    # Guardar en sesion_noticias para que /ver, /top, /resumen funcionen
    guardar_sesion(nuevas)

    # Enviar top 3 + mensaje con instrucciones
    top3 = nuevas[:3]
    for n in top3:
        enviar_noticia(n)

    enviar_resumen(len(nuevas), nuevas)
    print(f"{len(nuevas)} noticias procesadas, top 3 enviadas.")


if __name__ == "__main__":
    correr()