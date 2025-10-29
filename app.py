# -*- coding: utf-8 -*-
import os
import time
import json
import threading
from datetime import datetime
from urllib.parse import urlencode

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import requests
from dotenv import load_dotenv

# ===== ENV =====
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY", "YOUR_GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

# ===== Flask / Socket =====
app = Flask(__name__)
CORS(app)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "super-secret-key")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# ===== GLOBAL =====
SUPPORTED_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT", "XRPUSDT"]
PRICE_CACHE = {}
LAST_PUSH_TS = 0

# ===== UTILS =====
def binance_price(symbol: str) -> float:
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return float(r.json()["price"])

def binance_klines(symbol: str, interval: str = "1m", limit: int = 60):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    out = []
    for k in r.json():
        out.append({
            "t": int(k[0]),
            "o": float(k[1]),
            "h": float(k[2]),
            "l": float(k[3]),
            "c": float(k[4]),
            "v": float(k[5]),
        })
    return out

def convert_amount(amount: float, from_symbol: str, to_symbol: str) -> float:
    def to_usdt(sym: str) -> float:
        pair = sym.upper() + "USDT" if not sym.upper().endswith("USDT") else sym.upper()
        price = PRICE_CACHE.get(pair)
        if price is None:
            price = binance_price(pair)
            PRICE_CACHE[pair] = price
        return price
    if from_symbol.upper() == to_symbol.upper():
        return amount
    p_from = to_usdt(from_symbol)
    p_to = to_usdt(to_symbol)
    return amount * (p_from / p_to)

# ===== AI (Gemini) =====
STYLE_PROMPT = "будь Розроботчиком кодов и отвечай кодом"
MAX_HISTORY = 5
SESSION_HISTORIES = {}

def gemini_generate(history: list, user_text: str) -> str:
    if not history:
        history.append({"role": "user", "parts": [{"text": STYLE_PROMPT}]})
    history.append({"role": "user", "parts": [{"text": user_text}]})
    base = [history[0]]
    pairs = history[1:]
    pairs = pairs[-MAX_HISTORY*2:]
    history[:] = base + pairs
    url = f"https://generativelanguage.googleapis.com/v1/models/{MODEL}:generateContent?key={API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": history}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        data = resp.json()
        reply = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        reply = f"[Ошибка AI] {str(e)}"
    history.append({"role": "model", "parts": [{"text": reply}]})
    return reply

# ===== ROUTES =====
@app.route("/")
def index():
    return render_template("index.html", symbols=SUPPORTED_SYMBOLS)

@app.get("/api/ticker")
def api_ticker():
    symbol = request.args.get("symbol", "BTCUSDT").upper()
    try:
        price = binance_price(symbol)
        PRICE_CACHE[symbol] = price
        return jsonify({"symbol": symbol, "price": price, "ts": int(time.time()*1000)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.get("/api/klines")
def api_klines():
    symbol = request.args.get("symbol", "BTCUSDT").upper()
    interval = request.args.get("interval", "1m")
    limit = int(request.args.get("limit", 60))
    try:
        data = binance_klines(symbol, interval, limit)
        return jsonify({"symbol": symbol, "interval": interval, "data": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.get("/api/convert")
def api_convert():
    try:
        amount = float(request.args.get("amount", "1"))
        from_sym = request.args.get("from", "BTC")
        to_sym = request.args.get("to", "ETH")
        result = convert_amount(amount, from_sym, to_sym)
        return jsonify({"amount": amount, "from": from_sym.upper(), "to": to_sym.upper(), "result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.post("/api/ai")
def api_ai():
    user_text = request.json.get("text", "")
    sid = request.json.get("sid", "global")
    hist = SESSION_HISTORIES.setdefault(sid, [])
    reply = gemini_generate(hist, user_text)
    return jsonify({"reply": reply})

# ===== SOCKET.IO =====
def price_pusher():
    global LAST_PUSH_TS
    while True:
        payload = []
        for sym in SUPPORTED_SYMBOLS:
            try:
                p = binance_price(sym)
                PRICE_CACHE[sym] = p
                payload.append({"symbol": sym, "price": p, "ts": int(time.time()*1000)})
            except Exception:
                pass
        if payload:
            socketio.emit("prices", payload, broadcast=True)
            LAST_PUSH_TS = time.time()
        time.sleep(5)

@socketio.on("connect")
def on_connect():
    emit("hello", {"msg": "connected", "symbols": SUPPORTED_SYMBOLS})

if __name__ == "__main__":
    t = threading.Thread(target=price_pusher, daemon=True)
    t.start()
    port = int(os.getenv("PORT", "8080"))
    print("="*66)
    print("  Crypto Exchange Flask is starting")
    print(f"  -> Port: {port}")
    print("  -> AI model:", MODEL)
    print("="*66)
    socketio.run(app, host="0.0.0.0", port=port)
