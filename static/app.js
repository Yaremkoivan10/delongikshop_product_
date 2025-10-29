const $ = (sel) => document.querySelector(sel);
const pricesBox = $("#prices");
const symbolSel = $("#symbol");
const intervalSel = $("#interval");
const chartTitle = $("#chart-title");
const wsStatus = $("#ws-status");
const fromAmount = $("#fromAmount");
const fromSym = $("#fromSym");
const toSym = $("#toSym");
const convertOut = $("#convertOut");

let chart;

function addOption(el, val) {
  const o = document.createElement("option");
  o.value = val;
  o.textContent = val;
  el.appendChild(o);
}

SUPPORTED.forEach(s => addOption(symbolSel, s));
symbolSel.value = "BTCUSDT";

const socket = io({ transports: ["websocket"] });
socket.on("connect", () => { wsStatus.textContent = "● online"; wsStatus.classList.add("online"); });
socket.on("disconnect", () => { wsStatus.textContent = "● offline"; wsStatus.classList.remove("online"); });
socket.on("hello", (m) => {});
socket.on("prices", (arr) => { renderPrices(arr); });

function renderPrices(items) {
  pricesBox.innerHTML = "";
  items.forEach(p => {
    const row = document.createElement("div");
    row.className = "price-row";
    const last = window.__last || {};
    const prev = last[p.symbol];
    const dir = prev && p.price > prev ? "up" : prev && p.price < prev ? "down" : "";
    row.innerHTML = `<div class="sym">${p.symbol}</div><div class="val ${dir}">${(+p.price).toFixed(6)}</div>`;
    pricesBox.appendChild(row);
    window.__last = window.__last || {};
    window.__last[p.symbol] = p.price;
  });
}

async function loadKlines() {
  const symbol = symbolSel.value;
  const interval = intervalSel.value;
  chartTitle.textContent = `${symbol} — ${interval}`;
  const r = await fetch(`/api/klines?symbol=${symbol}&interval=${interval}&limit=120`);
  const data = await r.json();
  const labels = data.data.map(k => new Date(k.t).toLocaleTimeString());
  const closes = data.data.map(k => k.c);
  renderChart(labels, closes);
}
$("#load-klines").addEventListener("click", loadKlines);

function renderChart(labels, series) {
  const ctx = $("#chart").getContext("2d");
  if (chart) chart.destroy();
  chart = new Chart(ctx, {
    type: "line",
    data: { labels, datasets: [{ label: "Close", data: series }] },
    options: { responsive: true, animation: false, scales: { x: { display: true }, y: { display: true } } }
  });
}

$("#convertBtn").addEventListener("click", async () => {
  const amount = parseFloat(fromAmount.value || "0");
  const from = fromSym.value;
  const to = toSym.value;
  const r = await fetch(`/api/convert?amount=${amount}&from=${from}&to=${to}`);
  const data = await r.json();
  if (data.result !== undefined) {
    convertOut.textContent = `${amount} ${from} ≈ ${data.result} ${to}`;
  } else {
    convertOut.textContent = "Помилка: " + (data.error || "невідома");
  }
});

$("#ai-send").addEventListener("click", async () => {
  const text = $("#ai-input").value.trim();
  if (!text) return;
  $("#ai-reply").textContent = "Зачекай...";
  const sid = localStorage.getItem("sid") || crypto.randomUUID();
  localStorage.setItem("sid", sid);
  const r = await fetch("/api/ai", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({ text, sid })
  });
  const data = await r.json();
  $("#ai-reply").textContent = data.reply || "[порожня відповідь]";
});

(async function boot(){
  await loadKlines();
  const batch = await Promise.all(SUPPORTED.map(s => fetch(`/api/ticker?symbol=${s}`).then(r=>r.json()).catch(()=>null)));
  const filtered = batch.filter(Boolean).map(j => ({symbol:j.symbol, price:j.price, ts:j.ts}));
  renderPrices(filtered);
})();