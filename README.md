# 📰 Scraper Noticias Chile

> Sistema de web scraping para recolección automatizada de noticias chilenas desde múltiples fuentes, con filtrado por relevancia y distribución vía bot de Telegram.

![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat-square&logo=docker)
![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=flat-square&logo=telegram)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## ¿Qué hace?

Cada 30 minutos el scraper revisa automáticamente los RSS de los principales medios chilenos, filtra las noticias nuevas, evita duplicados y te las manda directo al Telegram. Sin abrir el navegador, sin perderse nada.

```
Emol · T13 · BioBioChile · La Tercera · El Mostrador · CNN Chile
        ↓
   Procesador Python
   (filtra + deduplica)
        ↓
   Base de datos SQLite
        ↓
   Bot de Telegram 📲
```

---

## Características

- Scraping de múltiples fuentes RSS chilenas simultáneamente
- Deduplicación automática con hash MD5 por URL
- Persistencia en SQLite para no repetir noticias entre ejecuciones
- Scheduler interno — corre cada 30 minutos sin cron externo
- Totalmente dockerizado, levanta con un solo comando
- Variables de entorno para credenciales, sin hardcodear tokens

---

## Estructura del proyecto

```
scraper-noticias/
├── scraper.py          # Lógica de scraping y RSS parsing
├── bot.py              # Envío de mensajes por Telegram
├── main.py             # Función principal correr()
├── run.py              # Loop del scheduler (entry point)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .gitignore
```

---

## Requisitos

- Docker y Docker Compose instalados
- Un bot de Telegram (creado con [@BotFather](https://t.me/BotFather))
- Tu `CHAT_ID` de Telegram

---

## Instalación y uso

### 1. Clona el repositorio

```bash
git clone https://github.com/Panditax727/scraper-noticias.git
cd scraper-noticias
```

### 2. Crea el archivo `.env`

```bash
cp .env.example .env
```

Edita `.env` con tus credenciales:

```env
TELEGRAM_TOKEN=tu_token_aqui
TELEGRAM_CHAT_ID=tu_chat_id_aqui
```

> Para obtener tu `CHAT_ID`, habla con [@userinfobot](https://t.me/userinfobot) en Telegram.

### 3. Levanta el contenedor

```bash
docker compose up -d
```

### 4. Revisa los logs

```bash
docker compose logs -f
```

Deberías ver algo como:

```
Scraper iniciado, corriendo cada 30 min...
BioBioChile: 3 noticias nuevas
T13: 2 noticias nuevas
5 noticias enviadas al Telegram ✓
```

---

## Comandos útiles

```bash
# Levantar en background
docker compose up -d

# Ver logs en tiempo real
docker compose logs -f

# Detener el contenedor
docker compose down

# Reconstruir la imagen (tras cambios en el código)
docker compose up -d --build
```

---

## Fuentes incluidas

| Medio | RSS |
|---|---|
| BioBioChile | `biobiochile.cl/feed` |
| T13 | `t13.cl/rss` |
| Emol | `emol.com/rss` |
| La Tercera | `latercera.com/feed` |
| El Mostrador | `elmostrador.cl/feed` |
| CNN Chile | `cnnchile.com/feed` |

Para agregar una fuente nueva, edita el array `FUENTES` en `scraper.py`:

```python
{"nombre": "Tu Medio", "rss": "https://tumedio.cl/feed/"}
```

---

## Variables de entorno

| Variable | Descripción | Requerida |
|---|---|---|
| `TELEGRAM_TOKEN` | Token del bot de Telegram | ✅ |
| `TELEGRAM_CHAT_ID` | ID del chat donde llegan las noticias | ✅ |

---

## Próximas mejoras

- [ ] Filtro por región (Valparaíso, RM, etc.)
- [ ] Clasificación por categoría (política, deportes, cultura)
- [ ] Comando `/ultimas` para pedir noticias manualmente
- [ ] Panel web con historial de noticias
- [ ] Resumen diario automático a las 8:00 AM

---

## Autor

**Panditax** — [@Panditax727](https://github.com/Panditax727)

> Proyecto desarrollado como parte del setup de servidor personal. Corre 24/7 🇨🇱
