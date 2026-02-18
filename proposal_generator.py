#!/usr/bin/env python3
"""
Freelance Proposal Generator
Uses RTX (local Ollama) to:
1. Classify IT job posts from Polish FB groups
2. Extract job requirements
3. Generate personalized proposals in Polish

Zero Claude tokens - 100% RTX powered.
"""

import json
from typing import Optional

from ai_gateway import LocalAI


class FreelanceClassifier:
    """Classifies FB posts as IT freelance jobs"""

    CATEGORIES = {
        "web_dev": "Strona WWW, sklep, landing page, WordPress",
        "scripting": "Skrypt, automatyzacja, bot, scraper",
        "mobile_app": "Aplikacja mobilna, Android, iOS",
        "content": "Artykuł, blog, copywriting, tłumaczenie",
        "design": "Logo, grafika, banner, UI/UX",
        "data": "Analiza danych, Excel, raport, dashboard",
        "seo": "Pozycjonowanie, SEO, Google Ads, reklama",
        "other_it": "Inne IT/tech (nie pasuje do powyższych)",
        "irrelevant": "Nie jest zleceniem IT/freelance",
    }

    def __init__(self):
        self.ai = LocalAI()

    def classify(self, post_text: str) -> str:
        """Returns category name or 'irrelevant'"""
        categories_list = "\n".join(
            f"- {k}: {v}" for k, v in self.CATEGORIES.items()
        )

        prompt = f"""Jesteś klasyfikatorem ogłoszeń z polskich grup Facebook.
Klasyfikuj post do JEDNEJ kategorii.

KATEGORIE:
{categories_list}

POST:
{post_text[:800]}

Odpowiedz TYLKO jednym słowem (nazwą kategorii):"""

        result = self.ai.ask_rtx(
            prompt=prompt,
            temperature=0.1,
            max_tokens=15
        )

        if result.get("success"):
            cat = result["response"].strip().lower().split()[0]
            if cat in self.CATEGORIES:
                return cat

        return "irrelevant"

    def extract_requirements(self, post_text: str) -> dict:
        """Extract structured job info via RTX"""
        prompt = f"""Wyciągnij dane ze zlecenia freelance. Odpowiedz TYLKO w JSON.

POST:
{post_text[:800]}

JSON (użyj null dla brakujących pól):
{{
  "task_description": "krótki opis zadania (1 zdanie)",
  "budget_pln": null,
  "deadline": null,
  "contact": null,
  "tech_stack": [],
  "urgency": "normal/urgent/flexible"
}}"""

        result = self.ai.ask_rtx(
            prompt=prompt,
            temperature=0.1,
            max_tokens=300
        )

        if result.get("success"):
            try:
                text = result["response"].strip()
                # Extract JSON block if wrapped in markdown
                if "```" in text:
                    text = text.split("```")[1]
                    if text.startswith("json"):
                        text = text[4:]
                return json.loads(text.strip())
            except (json.JSONDecodeError, IndexError):
                pass

        return {"task_description": post_text[:100], "budget_pln": None, "contact": None}


class ProposalGenerator:
    """Generates personalized freelance proposals in Polish"""

    # Our capabilities per category
    SKILLS = {
        "web_dev": "tworzeniu stron WWW, sklepów internetowych i landing pages (WordPress, React, HTML/CSS)",
        "scripting": "automatyzacji, skryptach Python i botach (web scraping, API, automatyzacja zadań)",
        "mobile_app": "aplikacjach mobilnych i webowych (React Native, PWA)",
        "content": "tworzeniu treści, artykułów SEO i copywritingu",
        "design": "projektowaniu graficznym, logo i materiałach marketingowych",
        "data": "analizie danych, raportach i dashboardach (Python, Excel, PowerBI)",
        "seo": "SEO, pozycjonowaniu i kampaniach Google Ads",
        "other_it": "rozwiązaniach IT i programowaniu",
    }

    # Pricing hints per category (PLN)
    PRICE_HINTS = {
        "web_dev": (500, 3000),
        "scripting": (300, 1500),
        "mobile_app": (2000, 8000),
        "content": (80, 400),
        "design": (200, 1200),
        "data": (400, 2000),
        "seo": (500, 2500),
        "other_it": (300, 2000),
    }

    def __init__(self):
        self.ai = LocalAI()

    def generate(self, post_text: str, category: str, requirements: dict) -> str:
        """Generate a personalized proposal in Polish"""
        skill_desc = self.SKILLS.get(category, "rozwiązaniach IT")
        price_range = self.PRICE_HINTS.get(category, (300, 2000))

        budget_note = ""
        if requirements.get("budget_pln"):
            budget_note = f"Wspomniano budżet: {requirements['budget_pln']} PLN."
        else:
            budget_note = f"Zakres cenowy podobnych zleceń: {price_range[0]}-{price_range[1]} PLN."

        task_desc = requirements.get("task_description", "")
        urgency = requirements.get("urgency", "normal")

        urgency_note = ""
        if urgency == "urgent":
            urgency_note = "Widzę, że zależy Ci na czasie - mogę zacząć dziś."

        prompt = f"""Napisz krótką, profesjonalną ofertę po polsku do tego zlecenia freelance.

ZLECENIE: {post_text[:400]}
OPIS ZADANIA: {task_desc}
KATEGORIA: {category}
SPECJALIZACJA: {skill_desc}
BUDŻET: {budget_note}
{urgency_note}

ZASADY:
- Maksymalnie 5-7 zdań
- Wspomnij konkretnie o zadaniu z posta (pokaż że czytałeś)
- Podaj orientacyjną cenę lub poproś o kontakt po szczegóły
- Ton: profesjonalny ale przyjazny, nie formalny
- Zaproponuj krótkie demo/przykład jeśli możliwe
- NIE zacznij od "Cześć," ani "Witam,"
- Zakończ zaproszeniem do kontaktu

OFERTA:"""

        result = self.ai.ask_rtx(
            prompt=prompt,
            temperature=0.7,
            max_tokens=300
        )

        if result.get("success"):
            return result["response"].strip()

        # Fallback proposal
        return (
            f"Widzę, że szukasz kogoś do {task_desc or 'tego projektu'}. "
            f"Specjalizuję się w {skill_desc}. "
            f"Mogę to dla Ciebie zrealizować. "
            f"Napisz do mnie w wiadomości prywatnej, ustalamy szczegóły i cenę."
        )


# -- Quick test ----------------------------------------------------------------

if __name__ == "__main__":
    classifier = FreelanceClassifier()
    generator = ProposalGenerator()

    test_posts = [
        "Szukam kogoś do zrobienia strony WWW dla małej firmy budowlanej. WordPress, coś prostego z galerią zdjęć i formularzem kontaktowym. Budżet ok 800 PLN. Pilne, na wczoraj :) Piszcie na priv.",
        "Potrzebuję skrypt Python który będzie automatycznie pobierał dane z kilku stron i zapisywał do Excela. Codziennie rano. Budżet 500 zł.",
        "Ktoś poleci dobrego hydraulika w Krakowie?",
        "Zlecę napisanie 10 artykułów SEO o tematyce ogrodniczej, każdy ok 1500 słów. Płacę 100 PLN/artykuł. Doświadczeni copywriterzy - piszcie!",
    ]

    for post in test_posts:
        print("\n" + "="*60)
        print(f"POST: {post[:80]}...")

        category = classifier.classify(post)
        print(f"CATEGORY: {category}")

        if category == "irrelevant":
            print("-> SKIP")
            continue

        requirements = classifier.extract_requirements(post)
        print(f"REQUIREMENTS: {requirements}")

        proposal = generator.generate(post, category, requirements)
        print(f"\nPROPOSAL:\n{proposal}")
