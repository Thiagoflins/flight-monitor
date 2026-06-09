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
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

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
        "one_way": "true" if route.get("one_way", True) else "false",
        "direct": "true" if route.get("direct", False) else "false",
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
        "duration_to": cheapest.get("duration_to"),
        "duration_back": cheapest.get("duration_back"),
        "link_path": cheapest.get("link"),
    }


def build_link(link_path, marker):
    """Monta a URL completa de compra a partir do path retornado pela API.

    Usada apenas pra registrar no history.csv (debug/auditoria). O alerta no
    Telegram usa `build_search_links` com várias plataformas.
    """
    if not link_path:
        return ""
    base = "https://www.aviasales.com" + link_path
    if marker:
        separator = "&" if "?" in base else "?"
        base = f"{base}{separator}marker={marker}"
    return base


def build_search_links(route, flight):
    """Monta URLs de busca em Google Flights, Skyscanner e Kayak.

    Usa a data efetiva retornada pela API (`flight.departure_at`), que é o
    dia mais barato do mês monitorado — assim a busca abre exatamente no dia
    do preço alertado, não num dia genérico.
    """
    origin = route["origin"]
    dest = route["destination"]
    dep_date = (flight.get("departure_at") or "")[:10]
    ret_date = (flight.get("return_at") or "")[:10]
    one_way = route.get("one_way", True)

    if not dep_date:
        return {}

    q = f"Flights from {origin} to {dest} on {dep_date}"
    if not one_way and ret_date:
        q += f" through {ret_date}"
    google = f"https://www.google.com/travel/flights?q={quote_plus(q)}"

    yymmdd = dep_date[2:4] + dep_date[5:7] + dep_date[8:10]
    skyscanner = (
        f"https://www.skyscanner.com.br/transporte/passagens-aereas/"
        f"{origin.lower()}/{dest.lower()}/{yymmdd}/"
    )
    if not one_way and ret_date:
        ret_yymmdd = ret_date[2:4] + ret_date[5:7] + ret_date[8:10]
        skyscanner += f"{ret_yymmdd}/"

    kayak = f"https://www.kayak.com.br/flights/{origin}-{dest}/{dep_date}"
    if not one_way and ret_date:
        kayak += f"/{ret_date}"

    return {
        "Google Flights": google,
        "Skyscanner": skyscanner,
        "Kayak": kayak,
    }


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


def _format_datetime_br(iso_str):
    """Converte '2026-07-12T08:25:00-03:00' em '12/07/2026 - 08:25'.

    Mantém o horário local do voo (que já vem no fuso da origem),
    sem conversão de timezone.
    """
    if not iso_str or len(iso_str) < 16:
        return iso_str or "?"
    return f"{iso_str[8:10]}/{iso_str[5:7]}/{iso_str[0:4]} - {iso_str[11:13]}:{iso_str[14:16]}"


def _arrival_datetime_br(iso_str, duration_minutes):
    """Soma a duração (em minutos) ao horário de partida e formata em BR."""
    if not iso_str or not duration_minutes or duration_minutes <= 0:
        return None
    try:
        dt = datetime.fromisoformat(iso_str)
    except ValueError:
        return None
    arr = dt + timedelta(minutes=duration_minutes)
    return f"{arr.day:02d}/{arr.month:02d}/{arr.year} - {arr.hour:02d}:{arr.minute:02d}"


def format_alert_message(route, flight, is_new_low, is_within_max):
    price = flight["price"]
    currency = flight["currency"].upper()
    max_price = route.get("max_price")

    if is_within_max:
        cabecalho = f"<b>🎯🔥 OPORTUNIDADE — {route['name']}</b>"
        motivo = f"<b>Preço dentro do seu alvo!</b> (limite: {max_price} {currency})"
    elif is_new_low:
        cabecalho = f"<b>📉 Novo recorde — {route['name']}</b>"
        motivo = f"Preço caiu, mas ainda acima do alvo de {max_price} {currency}."
    else:
        cabecalho = f"<b>✈️ Alerta de preço — {route['name']}</b>"
        motivo = "Atualização de preço."

    transfers = flight.get("transfers")
    paradas = "voo direto" if transfers == 0 else f"{transfers} parada(s)" if transfers is not None else "paradas: ?"

    linhas = [
        cabecalho,
        motivo,
        "",
        f"<b>Rota:</b> {route['origin']} → {route['destination']}",
        f"<b>Preço:</b> {price} {currency}",
        f"<b>Ida:</b> {_format_datetime_br(flight.get('departure_at'))}",
    ]
    chegada_ida = _arrival_datetime_br(flight.get("departure_at"), flight.get("duration_to"))
    if chegada_ida:
        linhas.append(f"<b>Chegada:</b> {chegada_ida}")
    if flight.get("return_at"):
        linhas.append(f"<b>Volta:</b> {_format_datetime_br(flight['return_at'])}")
        chegada_volta = _arrival_datetime_br(flight.get("return_at"), flight.get("duration_back"))
        if chegada_volta:
            linhas.append(f"<b>Chegada (volta):</b> {chegada_volta}")
    linhas.append(f"<b>Companhia:</b> {flight.get('airline') or '?'}")
    linhas.append(f"<b>Paradas:</b> {paradas}")

    search_links = build_search_links(route, flight)
    if search_links:
        linhas.append("")
        linhas.append("<b>🔗 Buscar em:</b>")
        for plataforma, url in search_links.items():
            linhas.append(f'  • <a href="{url}">{plataforma}</a>')

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
        message = format_alert_message(route, flight, is_new_low and not is_first_run, is_within_max)
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
