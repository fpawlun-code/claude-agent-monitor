#!/usr/bin/env python3
"""
Facebook Monitor Engine - Real Estate Lead Generation
Uses ai_gateway (RTX) for bulk post analysis, saves Claude tokens for decisions.

WORKFLOW:
1. Scrape FB groups (Playwright - 0 tokens)
2. Bulk classify posts via RTX (0 Claude tokens)
3. Extract structured data via RTX (0 Claude tokens)
4. Claude only validates final leads (minimal tokens)

TARGET: 90-95% token savings vs. full Claude processing
"""

import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import json

from ai_gateway import LocalAI

class FBMonitorEngine:
    """Automated FB monitoring with RTX-powered analysis"""

    def __init__(self):
        self.gateway = LocalAI()
        self.data_dir = Path("C:\\ClaudeAgent\\fb_data")
        self.data_dir.mkdir(exist_ok=True)

        self.log_file = Path("C:\\ClaudeAgent\\fb_monitor.log")

    def log(self, message: str):
        """Write to log with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}\n"

        print(log_line.strip())

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_line)

    def classify_post(self, post_text: str) -> Optional[str]:
        """
        Classify FB post into category (via RTX)

        Returns: "apartment", "house", "room", "commercial", "irrelevant"
        """
        system_context = """You are a real estate classifier. Analyze Polish Facebook posts about real estate.
Respond with ONLY one word: apartment, house, room, commercial, or irrelevant."""

        prompt = f"""Classify this post:

{post_text}

Category:"""

        result = self.gateway.ask_rtx(
            prompt=prompt,
            system_context=system_context,
            temperature=0.2,
            max_tokens=10
        )

        if result.get("success"):
            category = result["response"].strip().lower()
            valid_categories = ["apartment", "house", "room", "commercial", "irrelevant"]

            if category in valid_categories:
                return category

        return None

    def extract_data(self, post_text: str) -> Optional[Dict]:
        """
        Extract structured data from post (via RTX)

        Returns: {price_pln, area_m2, rooms, location, phone, email}
        """
        system_context = """You are a data extraction expert. Extract real estate data from Polish text.
Respond with ONLY valid JSON. Use null for missing fields."""

        prompt = f"""Extract these fields from the post:
- price_pln (number, no currency symbols)
- area_m2 (number)
- rooms (number)
- location (string, city/district)
- phone (string, format: XXX-XXX-XXX)
- email (string)

Post:
{post_text}

JSON:"""

        result = self.gateway.ask_rtx(
            prompt=prompt,
            system_context=system_context,
            temperature=0.1,
            max_tokens=200
        )

        if result.get("success"):
            try:
                # Try to parse JSON
                response_text = result["response"].strip()

                # Extract JSON if wrapped in markdown
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()

                data = json.loads(response_text)
                return data
            except json.JSONDecodeError as e:
                self.log(f"⚠️  JSON parse error: {e}")
                return None

        return None

    def analyze_post(self, post: Dict) -> Optional[Dict]:
        """
        Full analysis: classify + extract data (RTX-powered)

        Args:
            post: {"id": str, "text": str, "url": str, "author": str}

        Returns: Enriched post with category and extracted data
        """
        self.log(f"🔍 Analyzing post {post.get('id')}: {post.get('text', '')[:50]}...")

        # Step 1: Classify (RTX)
        category = self.classify_post(post["text"])

        if category == "irrelevant" or category is None:
            self.log(f"❌ Irrelevant post, skipping")
            return None

        self.log(f"✅ Category: {category}")

        # Step 2: Extract data (RTX)
        extracted = self.extract_data(post["text"])

        if not extracted:
            self.log(f"⚠️  Data extraction failed")
            return None

        # Merge
        result = {
            **post,
            "category": category,
            "extracted": extracted,
            "analyzed_at": datetime.now().isoformat()
        }

        self.log(f"📊 Extracted: {extracted}")

        return result

    def process_batch(self, posts: List[Dict]) -> List[Dict]:
        """
        Process multiple posts via RTX

        This is where 90% token savings happen vs. Claude
        """
        self.log(f"📦 Processing batch of {len(posts)} posts via RTX...")

        qualified_leads = []

        for i, post in enumerate(posts, 1):
            self.log(f"🔄 [{i}/{len(posts)}]")

            analyzed = self.analyze_post(post)

            if analyzed and analyzed["category"] in ["apartment", "house"]:
                qualified_leads.append(analyzed)

        self.log(f"✅ Batch complete: {len(qualified_leads)} qualified leads")

        return qualified_leads

    def save_leads(self, leads: List[Dict], filename: Optional[str] = None):
        """Save qualified leads to JSON"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"leads_{timestamp}.json"

        output_file = self.data_dir / filename

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(leads, f, indent=2, ensure_ascii=False)

        self.log(f"📁 Saved {len(leads)} leads to: {output_file}")

        return str(output_file)

    def run_monitoring_loop(self, interval_minutes: int = 60):
        """
        Continuous monitoring loop

        Args:
            interval_minutes: Time between scraping cycles
        """
        self.log("🚀 Starting FB monitoring loop...")
        self.log(f"⏱️  Interval: {interval_minutes} minutes")

        cycle = 0

        while True:
            cycle += 1
            self.log(f"\n{'='*60}")
            self.log(f"🔄 CYCLE {cycle} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.log(f"{'='*60}")

            # TODO: Integrate with actual FB scraper
            # For now, simulate with dummy data
            self.log("⏳ Scraping FB groups... (TODO: integrate Playwright)")

            # Simulate posts
            dummy_posts = self._generate_dummy_posts(count=10)

            # Process via RTX
            qualified = self.process_batch(dummy_posts)

            # Save leads
            if qualified:
                self.save_leads(qualified)
                self.log(f"💰 Tokens saved vs. Claude: ~{len(dummy_posts) * 500} tokens")

            # Wait for next cycle
            self.log(f"\n⏸️  Sleeping for {interval_minutes} minutes...")
            time.sleep(interval_minutes * 60)

    def _generate_dummy_posts(self, count: int = 10) -> List[Dict]:
        """Generate dummy FB posts for testing"""
        templates = [
            "Sprzedam mieszkanie 3 pokoje, 65m2, centrum Szczecin, 450 000 PLN. Kontakt: 555-123-456",
            "Do wynajęcia kawalerka 30m2, Prawobrzeże, 1500 PLN/mc. Tel: 666-789-012",
            "Sprzedam dom 150m2, Warszewo, działka 500m2, 890 000 PLN. Email: contact@example.com",
            "Kupię mieszkanie do 400k, 2-3 pokoje, centrum lub blisko",
            "Szukam współlokatora do mieszkania na Pogodnie, 800 PLN/mc",
            "Witam, polecam super hydraulika, tanio i solidnie!",
            "Sprzedam Samsung Galaxy S24, stan idealny, 2500 PLN",
            "Mieszkanie na sprzedaż, 4 pokoje, 80m2, Niebuszewo, 520 tys. Tel: 777-456-123",
            "Dom szeregowy, 120m2, 3 pokoje, ogródek, 650 000 PLN, Kijewo",
            "Lokal użytkowy 100m2, parter, centrum, 3000 PLN/mc czynsz"
        ]

        posts = []
        for i in range(count):
            posts.append({
                "id": f"post_{i+1}",
                "text": templates[i % len(templates)],
                "url": f"https://facebook.com/groups/test/posts/{i+1}",
                "author": f"User{i+1}",
                "timestamp": datetime.now().isoformat()
            })

        return posts

if __name__ == "__main__":
    print("="*60)
    print("🏠 FB MONITOR ENGINE - RTX POWERED")
    print("="*60)

    engine = FBMonitorEngine()

    # Health check
    print("\n[1/2] Checking RTX gateway...")
    if not engine.gateway.health_check():
        print("❌ RTX not available")
        exit(1)

    # Test with dummy data
    print("\n[2/2] Testing with dummy posts...")
    dummy_posts = engine._generate_dummy_posts(count=5)

    qualified = engine.process_batch(dummy_posts)

    if qualified:
        output_file = engine.save_leads(qualified, "test_leads.json")
        print(f"\n✅ Test complete: {len(qualified)} leads saved")
        print(f"📁 Output: {output_file}")

        # Show usage stats
        stats = engine.gateway.get_usage_stats()
        print(f"\n💰 Total tokens saved: ~{stats['total_tokens_saved']}")
        print(f"💵 Cost saved: ${stats['estimated_cost_saved_usd']}")

    print("\n" + "="*60)
    print("🎯 ENGINE READY")
    print("="*60)
    print("\nTo run continuous monitoring:")
    print("  python fb_monitor_engine.py --loop")
