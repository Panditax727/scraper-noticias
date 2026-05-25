from scraper import scrapear
from bot import enviar_noticia, enviar_resumen
from collections import defaultdict


def agrupar_por_region(noticias):
    grupos = defaultdict(list)
    for n in noticias:
        grupos[n.get("region", "Nacional")].append(n)
    return grupos


def correr():
    nuevas = scrapear()

    if not nuevas:
        print("Sin noticias nuevas.")
        return

    grupos = agrupar_por_region(nuevas)

    for region, items in grupos.items():
        enviar_noticia({
            "fuente": f"📍 {region}",
            "titulo": f"{len(items)} noticias importantes",
            "link": "",
            "fecha": None,
        })
        for n in items[:3]:
            enviar_noticia(n)

    enviar_resumen(len(nuevas))
    print(f"{len(nuevas)} noticias enviadas.")


if __name__ == "__main__":
    correr()