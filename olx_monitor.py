"""
OLX IT Services Monitor
Sprawdza nowe ogłoszenia IT w usługach OLX i wysyła powiadomienia Telegram.
Uruchamiane co 15 min przez GitHub Actions.

NOTE: OLX może wymagać Playwright jeśli treść jest renderowana przez JS.
      Jeśli requests zwraca pustą listę ofert, zmień na playwright.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

SEEN_IDS_FILE = Path("seen_ids_olx.json")

SEARCH_QUERIES = [
    ("Python", "https://www.olx.pl/uslugi/komputery-i-internet/q-python/"),
    ("Automatyzacja", "https://www.olx.pl/uslugi/komputery-i-internet/q-automatyzacja/"),
    ("Scraper/Bot", "https://www.olx.pl/uslugi/komputery-i-internet/q-scraper/"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pl-PL,pl;q=0.9",
}


def load_seen_ids() -> set:
    if SEEN_IDS_FILE.exists():
        return set(json.loads(SEEN_IDS_FILE.read_text()))
    return set()


def save_seen_ids(ids: set) -> None:
    SEEN_IDS_FILE.write_text(json.dumps(sorted(ids)))


def send_telegram(message: str) -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[WARN] Brak TELEGRAM_TOKEN lub TELEGRAM_CHAT_ID — pomijam wysyłkę")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    resp = requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }, timeout=10)
    if resp.status_code == 200:
        print("[OK] Telegram wysłany")
        return True
    print(f"[ERR] Telegram błąd: {resp.status_code} {resp.text[:200]}")
    return False


def extract_olx_id(url: str) -> str:
    """Wyciąga ID z URL OLX np. /d/oferta/title-IDxxx.html → IDxxx."""
    match = re.search(r'-([A-Za-z0-9]+)\.html', url)
    if match:
        return match.group(1)
    # Fallback: ostatni segment URL
    parts = url.rstrip("/").split("/")
    return parts[-1] if parts else url


def parse_olx_offers(html: str) -> list:
    """
    Parsuje HTML listingu OLX.
    OLX ma kilka wariantów struktury HTML — próbujemy je wszystkie.
    Jeśli zwraca 0 ofert, strona może być JS-rendered — potrzeba Playwright.
    """
    soup = BeautifulSoup(html, "html.parser")
    offers = []

    # Wariant 1: data-cy="l-card" (nowy OLX)
    items = soup.select('[data-cy="l-card"]')

    # Wariant 2: starsza wersja OLX
    if not items:
        items = soup.select(".offer-wrapper, .listing-grid-container article, .css-1sw7q4x")

    # Wariant 3: fallback — linki do /d/oferta/
    if not items:
        links = soup.select('a[href*="/d/oferta/"]')
        for link in links:
            href = link.get("href", "")
            if not href:
                continue
            full_url = href if href.startswith("http") else "https://www.olx.pl" + href
            offer_id = extract_olx_id(href)
            title = link.get_text(strip=True) or "Bez tytułu"
            if len(title) > 5:
                offers.append({
                    "id": offer_id,
                    "title": title[:120],
                    "price": "",
                    "location": "",
                    "url": full_url,
                })
        return offers

    for item in items:
        link_el = item.select_one('a[href*="/d/oferta/"], a[href*="olx.pl/d/"]')
        if not link_el:
            continue
        href = link_el.get("href", "")
        full_url = href if href.startswith("http") else "https://www.olx.pl" + href
        offer_id = extract_olx_id(href)

        # Tytuł
        title_el = item.select_one("h6, h4, h3, [data-cy='ad-card-title'], .title-cell")
        title = title_el.get_text(strip=True) if title_el else link_el.get_text(strip=True)

        # Cena
        price_el = item.select_one("[data-testid='ad-price'], .price, [class*='price']")
        price = price_el.get_text(strip=True) if price_el else ""

        # Lokalizacja/data
        loc_el = item.select_one("[data-testid='location-date'], .bottom-cell, [class*='location']")
        location = loc_el.get_text(strip=True) if loc_el else ""

        if offer_id and len(title) > 3:
            offers.append({
                "id": offer_id,
                "title": title[:120],
                "price": price[:50],
                "location": location[:60],
                "url": full_url,
            })

    return offers


def check_query(query_name: str, url: str, seen_ids: set) -> tuple[list, list]:
    """Zwraca (nowe_oferty, wszystkie_id)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERR] OLX '{query_name}': {e}")
        return [], []

    offers = parse_olx_offers(resp.text)
    print(f"[INFO] OLX '{query_name}': znaleziono {len(offers)} ofert")

    if len(offers) == 0:
        print("[WARN] 0 ofert — możliwe że OLX wymaga JS (Playwright). Sprawdź stronę ręcznie.")

    new_offers = [o for o in offers if o["id"] and o["id"] not in seen_ids]
    all_ids = [o["id"] for o in offers if o["id"]]
    return new_offers, all_ids


def format_message(offer: dict, query: str) -> str:
    price_line = f"💰 Cena: {offer['price']}\n" if offer["price"] else ""
    loc_line = f"📍 {offer['location']}\n" if offer["location"] else ""
    return (
        f"📌 <b>[OLX] Nowe ogłoszenie IT!</b>\n"
        f"🔍 Szukana fraza: {query}\n\n"
        f"📋 <b>{offer['title']}</b>\n"
        f"{price_line}"
        f"{loc_line}"
        f"🔗 {offer['url']}"
    )


def main():
    print(f"[START] OLX Monitor — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    seen_ids = load_seen_ids()
    print(f"[INFO] Zapamiętane ID: {len(seen_ids)}")

    all_new = []
    all_current_ids = set()

    for query_name, url in SEARCH_QUERIES:
        new_offers, all_ids = check_query(query_name, url, seen_ids)
        all_new.extend([(o, query_name) for o in new_offers])
        all_current_ids.update(all_ids)

    print(f"[INFO] Nowych ofert OLX: {len(all_new)}")

    sent = 0
    for offer, query in all_new:
        msg = format_message(offer, query)
        if send_telegram(msg):
            sent += 1
        print(f"  → {offer['title'][:60]} | {offer['url']}")

    updated_ids = seen_ids | all_current_ids
    if len(updated_ids) > 2000:
        updated_ids = set(sorted(updated_ids)[-2000:])
    save_seen_ids(updated_ids)

    print(f"[DONE] Wysłano {sent}/{len(all_new)} powiadomień OLX. IDs: {len(updated_ids)}")


if __name__ == "__main__":
    main()
