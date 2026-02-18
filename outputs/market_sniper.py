```
import requests
from bs4 import BeautifulSoup
import json
import statistics

def scrape_olx(query, max_pages=3):
    results = []
    for page in range(1, max_pages + 1):
        url = f"https://www.olx.pl/elektronika/komputery/laptopy/q-{query}/?page={page}"
        try:
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            listings = soup.find_all('li', {'class': 'wrap'})
            for listing in listings:
                title = listing.find('h6').text.strip()
                price_text = listing.find('p', {'class': 'price'}).text.strip()
                url = listing.find('a')['href']
                if "RTX" in title and "Ryzen" in title:
                    results.append({
                        "title": title,
                        "price": extract_price(price_text),
                        "url": url
                    })
        except (requests.RequestException, AttributeError):
            print("Błąd pobierania strony")
    return results

def extract_price(price_text):
    price = price_text.replace("zł", "")
    price = price.strip()
    if price.endswith(" do negocjacji"):
        price = price[:-19].strip()
    return int(float(price))

def calculate_stats(prices_list):
    prices = [price["price"] for price in prices_list]
    avg_price = statistics.mean(prices)
    min_price = min(prices)
    max_price = max(prices)
    count = len(prices)
    return {
        "average": avg_price,
        "min": min_price,
        "max": max_price,
        "count": count
    }

def save_report(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f)

results = scrape_olx("hp-victus-16")
stats = calculate_stats(results)
save_report(stats, "prices_report.json")

print(f"Znaleziono {stats['count']} ofert. Średnia: {stats['average']} PLN, Min: {stats['min']} PLN, Max: {stats['max']} PLN")
```