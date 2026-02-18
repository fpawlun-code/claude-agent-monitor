import requests
from bs4 import BeautifulSoup
import json
import statistics
import re

def scrape_olx(query, max_pages=3):
    results = []
    for page in range(1, max_pages + 1):
        url = f"https://www.olx.pl/elektronika/komputery/laptopy/q-{query}/?page={page}"
        try:
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            listings = soup.find_all('div', {'data-cy': 'l-card'})

            for listing in listings:
                try:
                    title_elem = listing.find('h6')
                    price_elem = listing.find('p', {'data-testid': 'ad-price'})
                    link_elem = listing.find('a')

                    if not all([title_elem, price_elem, link_elem]):
                        continue

                    title = title_elem.text.strip()
                    price_text = price_elem.text.strip()
                    listing_url = link_elem.get('href', '')

                    if "RTX" in title and "Ryzen" in title:
                        price = extract_price(price_text)
                        if price:
                            results.append({
                                "title": title,
                                "price": price,
                                "url": listing_url
                            })
                except (AttributeError, ValueError) as e:
                    continue

        except requests.RequestException as e:
            print(f"Błąd pobierania strony {page}: {e}")

    return results

def extract_price(price_text):
    """Wyciąga cenę z tekstu, obsługuje różne formaty"""
    try:
        # Usuń wszystko oprócz cyfr
        numbers = re.findall(r'\d+', price_text.replace(' ', ''))
        if numbers:
            # Połącz wszystkie cyfry (np. "2 500" -> "2500")
            price_str = ''.join(numbers)
            return int(price_str)
        return None
    except:
        return None

def calculate_stats(prices_list):
    if not prices_list:
        return {
            "average": 0,
            "min": 0,
            "max": 0,
            "count": 0
        }

    prices = [item["price"] for item in prices_list]
    avg_price = statistics.mean(prices)
    min_price = min(prices)
    max_price = max(prices)
    count = len(prices)

    return {
        "average": round(avg_price, 2),
        "min": min_price,
        "max": max_price,
        "count": count
    }

def save_report(data, listings, filename):
    report = {
        "stats": data,
        "listings": listings,
        "timestamp": "2026-02-17"
    }
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    print("🔍 Szukam HP Victus 16 (Ryzen 7 + RTX) na OLX...")

    results = scrape_olx("hp-victus-16", max_pages=3)

    if results:
        stats = calculate_stats(results)
        save_report(stats, results, "C:\\ClaudeAgent\\prices_report.json")

        print(f"\n✅ Znaleziono {stats['count']} ofert:")
        print(f"   Średnia: {stats['average']} PLN")
        print(f"   Min: {stats['min']} PLN")
        print(f"   Max: {stats['max']} PLN")
        print(f"\n📁 Raport zapisany: C:\\ClaudeAgent\\prices_report.json")
    else:
        print("❌ Nie znaleziono ofert spełniających kryteria (Ryzen 7 + RTX)")
