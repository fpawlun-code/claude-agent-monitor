"""
Useme IT Job Monitor
Sprawdza nowe oferty IT na Useme i wysyła powiadomienia Telegram.
Uruchamiane co 15 min przez GitHub Actions.

NOTE: Selektory CSS mogą wymagać korekty po inspekcji HTML (F12 na useme.com/pl/jobs/).
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

SEEN_IDS_FILE = Path("seen_ids_useme.json")

CATEGORIES = [
    ("Programowanie", "https://useme.com/pl/jobs/?category=100"),
    ("Aplikacje webowe", "https://useme.com/pl/jobs/?category=102"),
    ("Projekty IT", "https://useme.com/pl/jobs/?category=103"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
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


def parse_offers(html: str, base_url: str = "https://useme.com") -> list:
    """
    Parsuje HTML listingu Useme. Selektory do weryfikacji po inspekcji strony.
    Useme używa klas dynamicznych — próbuje kilka wariantów.
    """
    soup = BeautifulSoup(html, "html.parser")
    offers = []

    # Wariant 1: lista ofert z article lub li z linkiem do /pl/jobs/
    items = soup.select("article.job, li.job, .job-list-item, .offer-item, article[data-id]")

    # Wariant 2: fallback — wszystkie linki do /pl/jobs/ z ID numerycznym
    if not items:
        links = soup.select('a[href*="/pl/jobs/"]')
        seen_hrefs = set()
        for link in links:
            href = link.get("href", "")
            # Szukamy linków postaci /pl/jobs/12345/ (ID numeryczne)
            parts = [p for p in href.split("/") if p.isdigit()]
            if parts and href not in seen_hrefs:
                seen_hrefs.add(href)
                offer_id = parts[0]
                full_url = href if href.startswith("http") else base_url + href
                title = link.get_text(strip=True) or "Bez tytułu"
                # Szukamy budżetu i deadline w rodzicu
                parent = link.parent
                budget = ""
                deadline = ""
                if parent:
                    budget_el = parent.select_one(".budget, .price, [class*='budget'], [class*='price']")
                    deadline_el = parent.select_one(".deadline, .date, [class*='deadline'], [class*='date']")
                    budget = budget_el.get_text(strip=True) if budget_el else ""
                    deadline = deadline_el.get_text(strip=True) if deadline_el else ""
                if title and len(title) > 5:  # pomijamy puste/krótkie
                    offers.append({
                        "id": offer_id,
                        "title": title[:120],
                        "budget": budget[:50],
                        "deadline": deadline[:30],
                        "url": full_url,
                    })
        return offers

    # Wariant 1 — parsowanie z article/li
    for item in items:
        offer_id = item.get("data-id", "")
        link_el = item.select_one("a[href*='/pl/jobs/']")
        if not link_el:
            continue
        href = link_el.get("href", "")
        if not offer_id:
            parts = [p for p in href.split("/") if p.isdigit()]
            offer_id = parts[0] if parts else href
        full_url = href if href.startswith("http") else base_url + href
        title = (item.select_one("h2, h3, .title, [class*='title']") or link_el).get_text(strip=True)
        budget_el = item.select_one(".budget, .price, [class*='budget'], [class*='price']")
        deadline_el = item.select_one(".deadline, .date, [class*='deadline'], [class*='date']")
        offers.append({
            "id": offer_id,
            "title": title[:120],
            "budget": budget_el.get_text(strip=True)[:50] if budget_el else "",
            "deadline": deadline_el.get_text(strip=True)[:30] if deadline_el else "",
            "url": full_url,
        })

    return offers


def check_category(category_name: str, url: str, seen_ids: set) -> tuple[list, list]:
    """Zwraca (nowe_oferty, wszystkie_id)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERR] {category_name}: {e}")
        return [], []

    offers = parse_offers(resp.text)
    print(f"[INFO] {category_name}: znaleziono {len(offers)} ofert")

    new_offers = [o for o in offers if o["id"] and o["id"] not in seen_ids]
    all_ids = [o["id"] for o in offers if o["id"]]
    return new_offers, all_ids


def format_message(offer: dict, category: str) -> str:
    budget_line = f"💰 Budżet: {offer['budget']}\n" if offer["budget"] else ""
    deadline_line = f"⏰ Deadline: {offer['deadline']}\n" if offer["deadline"] else ""
    return (
        f"🆕 <b>USEME - Nowa oferta IT!</b>\n"
        f"📂 Kategoria: {category}\n\n"
        f"📋 <b>{offer['title']}</b>\n"
        f"{budget_line}"
        f"{deadline_line}"
        f"🔗 {offer['url']}"
    )


def main():
    print(f"[START] Useme Monitor — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    seen_ids = load_seen_ids()
    print(f"[INFO] Zapamiętane ID: {len(seen_ids)}")

    all_new = []
    all_current_ids = set()

    for category_name, url in CATEGORIES:
        new_offers, all_ids = check_category(category_name, url, seen_ids)
        all_new.extend([(o, category_name) for o in new_offers])
        all_current_ids.update(all_ids)

    print(f"[INFO] Nowych ofert: {len(all_new)}")

    sent = 0
    for offer, category in all_new:
        msg = format_message(offer, category)
        if send_telegram(msg):
            sent += 1
        print(f"  → {offer['title'][:60]} | {offer['url']}")

    # Aktualizuj seen_ids (dodaj nowe, zachowaj stare by uniknąć duplikatów po długim czasie)
    updated_ids = seen_ids | all_current_ids
    # Ogranicz do 2000 ostatnich by plik nie rósł bez końca
    if len(updated_ids) > 2000:
        updated_ids = set(sorted(updated_ids)[-2000:])
    save_seen_ids(updated_ids)

    print(f"[DONE] Wysłano {sent}/{len(all_new)} powiadomień. IDs zapisane: {len(updated_ids)}")


if __name__ == "__main__":
    main()
