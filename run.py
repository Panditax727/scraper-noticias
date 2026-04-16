import schedule
import time
from main import correr

schedule.every(30).minutes.do(correr)

print("Scraper iniciado, corriendo cada 30 min...")
correr()  # corre una vez al arrancar
while True:
    schedule.run_pending()
    time.sleep(60)