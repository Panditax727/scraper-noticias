import schedule
import time
from main import correr

schedule.every(30).minutes.do(correr)

print("Scraper iniciado, corriendo cada 30 min...")
correr()  # corre una vez al arrancar

# ✅ FIX: el loop ahora captura excepciones para que un error puntual
# no mate el proceso completo — el scraper sigue vivo hasta el próximo ciclo.
while True:
    try:
        schedule.run_pending()
    except Exception as e:
        print(f"⚠ Error en ciclo de schedule: {e}")
    time.sleep(60)