CyberX — Крипто біржа (демо)

Функції:
- Live ціни (Socket.IO) для: BTC, ETH, SOL, BNB, DOGE, XRP (USDT-пари з Binance).
- Свічкові дані 1m/5m/... (REST /api/klines).
- Конвертації між криптовалютами через USDT-міст (REST /api/convert).
- AI помічник (Gemini) зі стилем "відповідай кодом" (POST /api/ai).

УВАГА: Демо-інтерфейс. Не для реальної торгівлі.

Запуск локально (скорочено):
1) python -m venv venv
2) Активуй віртуальне середовище
3) pip install -r requirements.txt
4) Скопіюй .env.example у .env та впиши GOOGLE_API_KEY
5) python app.py
6) Відкрий http://127.0.0.1:8080

Структура:
- app.py
- requirements.txt
- .env.example
- templates/index.html
- static/style.css
- static/app.js
