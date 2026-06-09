"""
Monitor pessoal de preços de passagens aéreas.

Roda periodicamente (via GitHub Actions), busca o voo mais barato de cada rota
configurada em config.json na Aviasales Data API (Travelpayouts), guarda o
histórico em data/history.csv, compara com o menor preço já visto em
data/state.json e dispara um alerta no Telegram quando vale a pena.

Credenciais SEMPRE via variáveis de ambiente (nunca hardcode):
- TRAVELPAYOUTS_TOKEN  -> token da Aviasales Data API
- TELEGRAM_BOT_TOKEN   -> token do bot do Telegram (via @BotFather)
- TELEGRAM_CHAT_ID     -> chat id para onde enviar os alertas
- TRAVELPAYOUTS_MARKER -> (opcional) marker de afiliado, entra no link gerado
"""

import csv
import json
import os
import sys
from datetime import datetime, timezone

import requests

CONFIG_PATH = "config.json"
HISTORY_PATH = "data/history.csv"
STATE_PATH = "data/state.json"

AVIASALES_URL = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

HISTORY_FIELDS = [
    "checked_at",
    "route_name",
    "origin",
    "destination",
    "departure_at",
    "return_at",
    "price",
    "currency",
    "airline",
    "transfers",
    "link",
]


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_state():
    if not os.path.exists(STATE_PATH):
        return {}
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def append_history(row):
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    file_exists = os.path.exists(HISTORY_PATH)
    with open(HISTORY_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HISTORY_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def fetch_cheapest_flight(route, currency, market, token):
    """
    Busca o voo mais barato para a rota na Aviasales Data API.

    Formato esperado da resposta (v3/prices_for_dates):
        {
            "success": true,
            "data": [
                {
                    "origin": "REC",
                    "destination": "LIS",
                    "price": 3200,
                    "airline": "TP",
                    "flight_number": 123,
                    "departure_at": "2026-09-10T08:00:00Z",
                    "return_at": "2026-09-20T20:00:00Z",
                    "transfers": 1,
                    "return_transfers": 0,
                    "duration": 900,
                    "link": "/REC1009LIS?marker=..."
                },
                ...
            ]
        }

    AJUSTE AQUI se a API mudar o formato: este é o único lugar que entende a
    estrutura do JSON retornado. O resto do programa trabalha com o dict
    "normalizado" devolvido por esta função (chaves: price, currency, airline,
    transfers, departure_at, return_at, link).
    """
    params = {
        "origin": route["origin"],
        "destination": route["destination"],
        "currency": currency,
        "market": market,
        "departure_at": route.get("departure_at"),
        "one_way": route.get("one_way", True),
        "direct": route.get("direct", False),
        "sorting": "price",
        "limit": 1,
        "page": 1,
        "token": token,
    }
    if route.get("return_at"):
        params["return_at"] = route["return_at"]

    response = requests.get(AVIASALES_URL, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()

    # A API retorna {"success": false, ...} quando não há resultados ou houve erro.
    if not payload.get("success", True):
        return None

    data = payload.get("data") or []
    if not data:
        return None

    cheapest = data[0]

    return {
        "price": cheapest.get("price"),
        "currency": currency,
        "airline": cheapest.get("airline"),
        "transfers": cheapest.get("transfers"),
        "departure_at": cheapest.get("departure_at"),
        "return_at": cheapest.get("return_at"),
        "link_path": cheapest.get("link"),
    }


def build_link(link_path, marker):
    """Monta a URL completa de compra a partir do path retornado pela API."""
    if not link_path:
        return ""
    base = "https://www.aviasales.com" + link_path
    if marker:
        separator = "&" if "?" in base else "?"
        base = f"{base}{separator}marker={marker}"
    return base


def send_telegram_alert(bot_token, chat_id, message_html):
    url = TELEGRAM_API_URL.format(token=bot_token)
    payload = {
        "chat_id": chat_id,
        "text": message_html,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()


def format_alert_message(route, flight, link, is_new_low):
    motivo = "🔻 Novo recorde de menor preço!" if is_new_low else "✅ Preço dentro do limite definido"

    transfers = flight.get("transfers")
    paradas = "voo direto" if transfers == 0 else f"{transfers} parada(s)" if transfers is not None else "paradas: ?"

    linhas = [
        f"<b>✈️ Alerta de preço — {route['name']}</b>",
        motivo,
        "",
        f"<b>Rota:</b> {route['origin']} → {route['destination']}",
        f"<b>Preço:</b> {flight['price']} {flight['currency'].upper()}",
        f"<b>Ida:</b> {flight.get('departure_at') or '?'}",
    ]
    if flight.get("return_at"):
        linhas.append(f"<b>Volta:</b> {flight['return_at']}")
    linhas.append(f"<b>Companhia:</b> {flight.get('airline') or '?'}")
    linhas.append(f"<b>Paradas:</b> {paradas}")
    if link:
        linhas.append(f"<b>Link:</b> {link}")

    return "\n".join(linhas)


def process_route(route, currency, market, tokens, state, now_iso):
    """Processa uma rota: busca, registra histórico, compara e alerta se preciso."""
    route_name = route["name"]
    travelpayouts_token = tokens["travelpayouts"]

    flight = fetch_cheapest_flight(route, currency, market, travelpayouts_token)
    if flight is None:
        print(f"[{route_name}] Nenhum resultado retornado pela API.")
        return

    price = flight.get("price")
    if price is None:
        print(f"[{route_name}] Resposta sem campo 'price' utilizável — ignorando.")
        return

    link = build_link(flight.get("link_path"), tokens.get("marker"))

    append_history({
        "checked_at": now_iso,
        "route_name": route_name,
        "origin": route["origin"],
        "destination": route["destination"],
        "departure_at": flight.get("departure_at"),
        "return_at": flight.get("return_at"),
        "price": price,
        "currency": flight["currency"],
        "airline": flight.get("airline"),
        "transfers": flight.get("transfers"),
        "link": link,
    })

    route_state = state.get(route_name)
    is_first_run = route_state is None
    previous_min_price = route_state.get("min_price") if route_state else None

    is_new_low = previous_min_price is None or price < previous_min_price
    is_within_max = price <= route.get("max_price", float("inf"))

    if is_first_run:
        # Na primeira execução só alertamos se já estiver abaixo do limite,
        # para não disparar uma notificação só por "descobrir" o preço atual.
        deve_alertar = is_within_max
    else:
        deve_alertar = is_within_max or is_new_low

    if deve_alertar:
        message = format_alert_message(route, flight, link, is_new_low and not is_first_run)
        try:
            send_telegram_alert(tokens["telegram_bot"], tokens["telegram_chat"], message)
            print(f"[{route_name}] Alerta enviado ao Telegram (preço: {price} {flight['currency'].upper()}).")
        except requests.RequestException as exc:
            print(f"[{route_name}] Falha ao enviar alerta no Telegram: {exc}")
    else:
        print(f"[{route_name}] Preço atual: {price} {flight['currency'].upper()} (sem alerta).")

    if is_new_low or is_first_run:
        state[route_name] = {
            "min_price": price if previous_min_price is None else min(price, previous_min_price),
            "currency": flight["currency"],
            "last_checked_at": now_iso,
        }
    else:
        route_state["last_checked_at"] = now_iso


def get_required_env(name):
    value = os.environ.get(name)
    if not value:
        print(f"ERRO: variável de ambiente '{name}' não definida. Configure-a antes de rodar.")
        sys.exit(1)
    return value


def main():
    travelpayouts_token = get_required_env("TRAVELPAYOUTS_TOKEN")
    telegram_bot_token = get_required_env("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = get_required_env("TELEGRAM_CHAT_ID")
    marker = os.environ.get("TRAVELPAYOUTS_MARKER", "")

    tokens = {
        "travelpayouts": travelpayouts_token,
        "telegram_bot": telegram_bot_token,
        "telegram_chat": telegram_chat_id,
        "marker": marker,
    }

    config = load_config()
    currency = config.get("currency", "brl")
    market = config.get("market", "br")
    routes = config.get("routes", [])

    state = load_state()
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for route in routes:
        try:
            process_route(route, currency, market, tokens, state, now_iso)
        except Exception as exc:
            # Uma rota com problema não pode derrubar as demais.
            print(f"[{route.get('name', '?')}] Erro inesperado ao processar a rota: {exc}")

    save_state(state)


if __name__ == "__main__":
    main()
