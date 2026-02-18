#!/usr/bin/env python3
"""
FB Scraper - Playwright-based Facebook group scraper
Targets Polish IT freelance groups for job posts.

STRATEGY:
- Persistent browser profile (save session after manual login)
- Human-like delays to avoid detection
- SQLite deduplication (never process same post twice)
- Public groups first (no login needed for reading)
"""

import asyncio
import json
import random
import sqlite3
import time
from datetime import datetime
from pathlib import Path

from playwright.async_api import Browser, Page, async_playwright

# ── Config ────────────────────────────────────────────────────────────────────

DATA_DIR = Path("C:/ClaudeAgent/fb_data")
DB_PATH = DATA_DIR / "jobs.db"
SESSION_DIR = DATA_DIR / "browser_session"

# Polish IT freelance groups (verified from FB search, public)
TARGET_GROUPS = [
    "https://www.facebook.com/groups/zlecenia.it.grafika",       # Programiści/graficy zlecenia - 13k, 10+/day
    "https://www.facebook.com/groups/zlecto.wykonawcy.zlecenia.uslugi",  # zlec.to - 66k, 90+/day
    "https://www.facebook.com/groups/zleceniaofertypracy",       # Zlecenia/Oferty IT - public
    "https://www.facebook.com/groups/praca.it.wynagrodzenia",    # Praca IT/oferty - 32k
    "https://www.facebook.com/groups/4007042206190287",          # Szukam programisty/WWW/apps
    "https://www.facebook.com/groups/grafikimontaz",             # Programiści/Graficy zlecenia
    "https://www.facebook.com/groups/2657738457741481",          # Oferty/Zlecenia/Usługi - 20k, 90+/day
    "https://www.facebook.com/groups/copywriterzy",              # Marketing/copywriting/SEO - 24k
    "https://www.facebook.com/groups/246806639124789",           # Remote Jobs IT - zdalny programista
    "https://www.facebook.com/groups/876337474198694",           # Zlecenia online WWW/Marketing
]

# ── Database ──────────────────────────────────────────────────────────────────

def init_db():
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id          TEXT PRIMARY KEY,
            group_url   TEXT,
            author      TEXT,
            text        TEXT,
            post_url    TEXT,
            scraped_at  TEXT,
            processed   INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id            TEXT PRIMARY KEY,
            post_id       TEXT,
            category      TEXT,
            budget_pln    REAL,
            requirements  TEXT,
            contact       TEXT,
            proposal      TEXT,
            status        TEXT DEFAULT 'pending',
            created_at    TEXT,
            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
    """)
    conn.commit()
    conn.close()

def save_post(post: dict) -> bool:
    """Returns True if new post (not seen before)"""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO posts (id, group_url, author, text, post_url, scraped_at) VALUES (?,?,?,?,?,?)",
            (post["id"], post["group_url"], post["author"], post["text"], post["post_url"], post["scraped_at"])
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Already seen
    finally:
        conn.close()

def get_unprocessed_posts(limit=50) -> list:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, group_url, author, text, post_url, scraped_at FROM posts WHERE processed=0 LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [{"id": r[0], "group_url": r[1], "author": r[2], "text": r[3], "post_url": r[4], "scraped_at": r[5]} for r in rows]

def mark_processed(post_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE posts SET processed=1 WHERE id=?", (post_id,))
    conn.commit()
    conn.close()

# ── Human-like helpers ────────────────────────────────────────────────────────

async def human_delay(min_ms=800, max_ms=2500):
    await asyncio.sleep(random.uniform(min_ms/1000, max_ms/1000))

async def human_scroll(page: Page, times=3):
    for _ in range(times):
        await page.evaluate("window.scrollBy(0, Math.floor(Math.random() * 400 + 200))")
        await human_delay(500, 1500)

# ── Scraper ───────────────────────────────────────────────────────────────────

class FBScraper:
    def __init__(self, headless=False):
        self.headless = headless  # False = visible browser (safer, use for login)
        self.new_posts = []

    async def scrape_group(self, page: Page, group_url: str, max_posts=20) -> list:
        """
        Scrape posts via GraphQL interception.
        FB sends post data as JSON to /api/graphql/ - we capture that directly.
        Much more reliable than HTML parsing.
        """
        import hashlib
        import re

        print(f"[FB] Scraping: {group_url}")
        posts = []
        captured_responses = []

        async def on_response(response):
            if "/api/graphql/" in response.url:
                try:
                    text = await response.text()
                    captured_responses.append(text)
                except Exception:
                    pass

        page.on("response", on_response)

        try:
            await page.goto(group_url, wait_until="domcontentloaded", timeout=30000)
            await human_delay(3000, 5000)

            # Scroll to trigger more feed loads
            for _ in range(8):
                await page.evaluate("window.scrollBy(0, Math.floor(Math.random() * 500 + 300))")
                await asyncio.sleep(1.3)

            await human_delay(2000, 3000)

        except Exception as e:
            print(f"[FB] Navigation error: {e}")

        page.remove_listener("response", on_response)

        # Parse GraphQL responses for post texts
        seen_texts = set()
        skip_strings = [
            'http', 'facebook.com', 'Ka\u017cdy mo\u017ce', 'Widoczna', 'publiczna',
            'Informacje', 'Dyskusja', 'Multimedia', 'className', 'style', 'color',
            'fontWeight', 'fontSize', 'span', 'null', 'undefined'
        ]

        for raw in captured_responses:
            if '"text"' not in raw and '"message"' not in raw:
                continue

            # Extract all "text":"..." values - use json.loads for proper unicode decoding
            matches = re.findall(r'"text"\s*:\s*"((?:[^"\\]|\\.)*)"', raw)

            for m in matches:
                try:
                    # Properly decode JSON string (handles \uXXXX, \n, \\, etc.)
                    text = json.loads(f'"{m}"')
                except Exception:
                    text = m.replace('\\n', '\n').replace('\\/', '/')

                if not isinstance(text, str):
                    continue
                text = text.strip()

                # Filter: length, skip UI/meta strings
                if len(text) < 40 or len(text) > 3000:
                    continue
                if any(skip in text for skip in skip_strings):
                    continue

                key = text[:60]
                if key in seen_texts:
                    continue
                seen_texts.add(key)

                post_id = hashlib.md5(text[:100].encode('utf-8', errors='ignore')).hexdigest()[:16]

                post = {
                    "id": post_id,
                    "group_url": group_url,
                    "author": "",
                    "text": text[:2000],
                    "post_url": group_url,
                    "scraped_at": datetime.now().isoformat()
                }

                is_new = save_post(post)
                if is_new:
                    posts.append(post)
                    if len(posts) >= max_posts:
                        break

        print(f"[FB] {group_url.split('/')[-1]}: {len(captured_responses)} responses -> {len(posts)} new posts")
        return posts

    async def run(self, groups=None, max_posts_per_group=20) -> list:
        """Main scrape run. Returns list of new posts."""
        groups = groups or TARGET_GROUPS
        all_new_posts = []

        async with async_playwright() as p:
            # Use persistent context to save cookies/session
            SESSION_DIR.mkdir(parents=True, exist_ok=True)

            browser = await p.chromium.launch_persistent_context(
                user_data_dir=str(SESSION_DIR),
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            page = await browser.new_page()

            # Remove webdriver flag
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """)

            for group_url in groups:
                new_posts = await self.scrape_group(page, group_url, max_posts_per_group)
                all_new_posts.extend(new_posts)
                await human_delay(3000, 7000)  # Delay between groups

            await browser.close()

        print(f"[FB] Total new posts: {len(all_new_posts)}")
        return all_new_posts


# ── Login helper ──────────────────────────────────────────────────────────────

async def manual_login():
    """
    Open browser for manual FB login.
    Auto-detects when user is logged in (no ENTER needed).
    Session saved to SESSION_DIR - only needed once.
    """
    print("="*60)
    print("MANUAL LOGIN MODE")
    print("="*60)
    print(f"Browser will open. Log into Facebook.")
    print(f"Session saved to: {SESSION_DIR}")
    print(f"Browser closes automatically after login.")
    print("="*60)

    SESSION_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            headless=False,
            viewport={"width": 1280, "height": 800},
        )
        page = await browser.new_page()
        await page.goto("https://www.facebook.com/login")

        print("\nWaiting for login... (browser closes automatically)")

        # Auto-detect login: wait until URL is no longer /login
        # Timeout: 5 minutes
        for _ in range(300):
            await asyncio.sleep(1)
            url = page.url
            if "facebook.com" in url and "/login" not in url and "checkpoint" not in url:
                print("[OK] Login detected! Saving session...")
                await asyncio.sleep(2)  # Let cookies settle
                break
        else:
            print("[WARN] Timeout - saving session anyway.")

        await browser.close()
        print("[OK] Session saved. You can now run --scrape.")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    init_db()

    if "--login" in sys.argv:
        asyncio.run(manual_login())

    elif "--scrape" in sys.argv:
        scraper = FBScraper(headless=False)  # Visible for safety
        new_posts = asyncio.run(scraper.run())
        print(f"\n✅ Scraped {len(new_posts)} new posts")
        print(f"DB: {DB_PATH}")

    elif "--test" in sys.argv:
        # Test DB + insert dummy post
        print("Testing DB...")
        test_post = {
            "id": "test_001",
            "group_url": "https://facebook.com/groups/test",
            "author": "Jan Kowalski",
            "text": "Szukam programisty Python do zrobienia skryptu automatyzującego wysyłkę maili. Budżet 500 PLN. Pilne!",
            "post_url": "https://facebook.com/groups/test/posts/001",
            "scraped_at": datetime.now().isoformat()
        }
        is_new = save_post(test_post)
        print(f"Post saved (new={is_new})")

        posts = get_unprocessed_posts()
        print(f"Unprocessed posts: {len(posts)}")
        print(f"First post: {posts[0]['text'][:80] if posts else 'none'}")

    else:
        print("Usage:")
        print("  python fb_scraper.py --login    # First-time FB login")
        print("  python fb_scraper.py --scrape   # Scrape groups")
        print("  python fb_scraper.py --test     # Test DB")
