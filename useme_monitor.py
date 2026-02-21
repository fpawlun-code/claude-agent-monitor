"""
Useme IT Job Monitor v2
Używa Playwright z istniejącą sesją (fb_data/useme_session) — omija 403.
Filtruje oferty pasujące do naszych możliwości i wysyła na Telegram.
"""

import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path

import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8530149996:AAHDfbX1mGT4qBDUwJxmjCRfsG-it4I46ME")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "8109579489")

SEEN_IDS_FILE = Path("seen_ids_useme.json")
SESSION_DIR = Path("C:/ClaudeAgent/fb_data/useme_session")

# Kategorie IT na Useme
URLS = [
    "https://useme.com/pl/jobs/category/programowanie-i-it,35/",          # IT ogólnie
    "https://useme.com/pl/jobs/category/programowanie-i-it,35/aplikacje-webowe,102/",
    "https://useme.com/pl/jobs/category/programowanie-i-it,35/oprogramowanie,100/",
    "https://useme.com/pl/jobs/category/programowanie-i-it,35/projekty-it,103/",
]

# Słowa kluczowe — czego szukamy (nasza specjalność)
OUR_KEYWORDS = [
    "python", "bot", "automatyzacja", "automat", "scraping", "scraper",
    "api", "integracja", "integration", "web scraping", "playwright",
    "selenium", "fastapi", "flask", "django", "ai", "openai", "chatgpt",
    "gpt", "llm", "skrypt", "script", "parser", "crawler", "webhook",
    "telegram", "discord", "allegro api", "woocommerce", "shopify",
    "excel automation", "csv", "pandas", "dane", "data", "raport",
    "dashboard", "monitoring", "powiadomienia", "notifications",
    "backend", "rest api", "json", "xml", "n8n", "make", "zapier",
]

# Wykluczenia (nie nasza specjalność)
EXCLUDE_KEYWORDS = [
    "seo", "logo", "grafik", "graphic", "fotograf", "video", "film",
    "tłumacz", "copywriter", "marketing", "social media", "instagram",
    "facebook reklam", "ads", "ulotk", "druk",
]


def load_seen_ids() -> set:
    if SEEN_IDS_FILE.exists():
        return set(json.loads(SEEN_IDS_FILE.read_text()))
    return set()


def save_seen_ids(ids: set) -> None:
    SEEN_IDS_FILE.write_text(json.dumps(sorted(ids)))


def send_telegram(message: str) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"[ERR] Telegram: {e}")
        return False


def is_relevant(text: str) -> bool:
    """Sprawdza czy oferta pasuje do naszych kompetencji."""
    text_lower = text.lower()
    if any(kw in text_lower for kw in EXCLUDE_KEYWORDS):
        return False
    return any(kw in text_lower for kw in OUR_KEYWORDS)


async def scrape_useme_playwright() -> list[dict]:
    """Scrape Useme używając Playwright z sesją lub bez."""
    from playwright.async_api import async_playwright

    offers = []

    async with async_playwright() as p:
        # Użyj istniejącej sesji jeśli jest dostępna
        use_session = SESSION_DIR.exists() and any(SESSION_DIR.iterdir())

        if use_session:
            context = await p.chromium.launch_persistent_context(
                str(SESSION_DIR),
                headless=False,  # headful — omija Cloudflare
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            )
            page = context.pages[0] if context.pages else await context.new_page()
        else:
            browser = await p.chromium.launch(
                headless=False,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                locale="pl-PL",
            )
            page = await context.new_page()

        for url in URLS[:3]:  # Sprawdzamy pierwsze 3 URL-e
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                await asyncio.sleep(8)  # Poczekaj na JS + Cloudflare

                # Zbierz wszystkie linki do ofert — format: /pl/jobs/slug-tytul,ID/
                links = await page.eval_on_selector_all(
                    'a[href*="/pl/jobs/"]',
                    'els => els.map(el => ({href: el.getAttribute("href"), text: el.innerText.trim()}))'
                )

                for link in links:
                    href = link.get("href", "") or ""
                    # URL format: /pl/jobs/slug-tytul,ID/ — ID po przecinku
                    m = re.search(r"/pl/jobs/[^,]+,(\d+)/$", href)
                    if not m:
                        continue
                    offer_id = m.group(1)
                    title = link.get("text", "").strip()
                    if len(title) < 5:
                        continue
                    offers.append({
                        "id": offer_id,
                        "title": title[:120],
                        "url": href.split("?")[0],
                        "budget": "",
                        "deadline": "",
                    })

                print(f"[INFO] Useme {url}: {len(links)} linków")

            except Exception as e:
                print(f"[ERR] Useme {url}: {e}")

        await context.close()

    # Deduplikacja po ID
    seen = set()
    unique = []
    for o in offers:
        if o["id"] not in seen:
            seen.add(o["id"])
            unique.append(o)

    return unique


def format_useme_message(offer: dict) -> str:
    budget = f"\n💰 Budżet: {offer['budget']}" if offer.get("budget") else ""
    return (
        f"🆕 <b>USEME — Nowa oferta IT!</b>{budget}\n\n"
        f"📋 <b>{offer['title']}</b>\n"
        f"🔗 {offer['url']}"
    )


async def main():
    print(f"[START] Useme Monitor v2 — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    seen_ids = load_seen_ids()
    print(f"[INFO] Zapamiętane ID: {len(seen_ids)}")

    all_offers = await scrape_useme_playwright()
    print(f"[INFO] Znaleziono ofert: {len(all_offers)}")

    new_offers = [o for o in all_offers if o["id"] not in seen_ids]
    relevant = [o for o in new_offers if is_relevant(o["title"])]
    print(f"[INFO] Nowych: {len(new_offers)}, pasujących do naszych kompetencji: {len(relevant)}")

    sent = 0
    for offer in relevant:
        msg = format_useme_message(offer)
        if send_telegram(msg):
            sent += 1
            print(f"  [OK] {offer['title'][:60]}")
        else:
            print(f"  [ERR] Telegram: {offer['title'][:60]}")

    # Aktualizuj seen_ids
    all_ids = {o["id"] for o in all_offers}
    updated = seen_ids | all_ids
    if len(updated) > 3000:
        updated = set(sorted(updated)[-3000:])
    save_seen_ids(updated)

    print(f"[DONE] Wysłano {sent}/{len(relevant)} powiadomień Useme")


if __name__ == "__main__":
    asyncio.run(main())
