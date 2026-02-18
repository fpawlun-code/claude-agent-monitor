#!/usr/bin/env python3
"""
Freelance Pipeline - Main Orchestrator
Runs the full FB -> classify -> propose -> approve loop.

FLOW:
  1. Scrape FB groups (Playwright)
  2. Classify posts via RTX (skip irrelevant)
  3. Extract requirements via RTX
  4. Generate proposals via RTX
  5. Show CLI approval dashboard
  6. You approve/skip -> send (manual) or log

Usage:
  python freelance_pipeline.py --run      # Full pipeline
  python freelance_pipeline.py --approve  # Just review pending proposals
  python freelance_pipeline.py --stats    # Show stats
  python freelance_pipeline.py --demo     # Test with dummy posts (no scraping)
"""

import asyncio
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from fb_scraper import DB_PATH, FBScraper, get_unprocessed_posts, init_db, mark_processed
from proposal_generator import FreelanceClassifier, ProposalGenerator

# -- Pipeline ------------------------------------------------------------------

class FreelancePipeline:
    def __init__(self):
        init_db()
        self.classifier = FreelanceClassifier()
        self.generator = ProposalGenerator()

    def process_posts(self, posts: list) -> list:
        """Classify + generate proposals for a list of posts. Returns jobs."""
        jobs = []
        total = len(posts)

        print(f"\n[PIPELINE] Processing {total} posts via RTX...")

        for i, post in enumerate(posts, 1):
            print(f"  [{i}/{total}] {post['text'][:60]}...")

            # Step 1: Classify
            category = self.classifier.classify(post["text"])
            print(f"    -> category: {category}")

            if category == "irrelevant":
                mark_processed(post["id"])
                continue

            # Step 2: Extract requirements
            requirements = self.classifier.extract_requirements(post["text"])

            # Step 3: Generate proposal
            proposal = self.generator.generate(post["text"], category, requirements)

            # Step 4: Save job to DB
            job = self._save_job(post, category, requirements, proposal)
            jobs.append(job)
            mark_processed(post["id"])
            print(f"    [OK] Job saved: {category}")

        print(f"\n[PIPELINE] Done. {len(jobs)} new jobs generated.")
        return jobs

    def _save_job(self, post: dict, category: str, requirements: dict, proposal: str) -> dict:
        import json as json_mod
        conn = sqlite3.connect(DB_PATH)
        job_id = f"job_{post['id']}"
        conn.execute(
            """INSERT OR REPLACE INTO jobs
               (id, post_id, category, budget_pln, requirements, contact, proposal, status, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                job_id,
                post["id"],
                category,
                requirements.get("budget_pln"),
                json_mod.dumps(requirements, ensure_ascii=False),
                requirements.get("contact", ""),
                proposal,
                "pending",
                datetime.now().isoformat()
            )
        )
        conn.commit()
        conn.close()
        return {"id": job_id, "post": post, "category": category, "requirements": requirements, "proposal": proposal}

    def get_pending_jobs(self) -> list:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("""
            SELECT j.id, j.category, j.budget_pln, j.requirements, j.contact, j.proposal, j.status,
                   p.text, p.post_url, p.author, p.group_url
            FROM jobs j
            JOIN posts p ON j.post_id = p.id
            WHERE j.status = 'pending'
            ORDER BY j.created_at DESC
        """).fetchall()
        conn.close()

        import json as json_mod
        jobs = []
        for r in rows:
            jobs.append({
                "id": r[0], "category": r[1], "budget_pln": r[2],
                "requirements": json_mod.loads(r[3]) if r[3] else {},
                "contact": r[4], "proposal": r[5], "status": r[6],
                "post_text": r[7], "post_url": r[8], "author": r[9], "group_url": r[10]
            })
        return jobs

    def update_job_status(self, job_id: str, status: str):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE jobs SET status=? WHERE id=?", (status, job_id))
        conn.commit()
        conn.close()

    # -- CLI Approval Dashboard ------------------------------------------------

    def approval_dashboard(self):
        """Interactive CLI to review and approve proposals"""
        jobs = self.get_pending_jobs()

        if not jobs:
            print("\n[OK] No pending jobs to review.")
            return

        print(f"\n{'='*70}")
        print(f"  FREELANCE PIPELINE - APPROVAL DASHBOARD")
        print(f"  {len(jobs)} pending jobs")
        print(f"{'='*70}")

        approved = 0
        skipped = 0

        for i, job in enumerate(jobs, 1):
            req = job.get("requirements", {})
            budget = f"{job['budget_pln']} PLN" if job.get("budget_pln") else "nie podano"

            print(f"\n{'-'*70}")
            print(f"  JOB {i}/{len(jobs)} | {job['category'].upper()}")
            print(f"{'-'*70}")
            print(f"  Autor:    {job['author']}")
            print(f"  Budżet:   {budget}")
            print(f"  Kontakt:  {job.get('contact') or 'nie podano'}")
            print(f"  URL:      {job['post_url'][:80] if job['post_url'] else 'brak'}")
            print(f"\n  POST:")
            print(f"  {job['post_text'][:300]}")
            print(f"\n  PROPOZYCJA OFERTY:")
            print(f"{'-'*40}")
            print(f"  {job['proposal']}")
            print(f"{'-'*40}")

            while True:
                choice = input("\n  [A]kceptuj / [S]kip / [E]dit / [Q]quit: ").strip().lower()

                if choice == "a":
                    self.update_job_status(job["id"], "approved")
                    print(f"  [OK] Zaakceptowano! Skopiuj propozycję i wyślij na: {job['post_url']}")
                    approved += 1
                    break

                elif choice == "s":
                    self.update_job_status(job["id"], "skipped")
                    print(f"  [SKIP]  Pominięto")
                    skipped += 1
                    break

                elif choice == "e":
                    print("  Wpisz nową propozycję (ENTER+ENTER żeby skończyć):")
                    lines = []
                    while True:
                        line = input("  > ")
                        if line == "":
                            break
                        lines.append(line)
                    new_proposal = "\n".join(lines)
                    if new_proposal:
                        conn = sqlite3.connect(DB_PATH)
                        conn.execute("UPDATE jobs SET proposal=?, status='approved' WHERE id=?",
                                     (new_proposal, job["id"]))
                        conn.commit()
                        conn.close()
                        print(f"  [OK] Zapisano i zaakceptowano!")
                        approved += 1
                    break

                elif choice == "q":
                    print(f"\n  Zakończono. Zaakceptowano: {approved}, Pominięto: {skipped}")
                    return

        print(f"\n{'='*70}")
        print(f"  GOTOWE!")
        print(f"  Zaakceptowano: {approved} | Pominięto: {skipped}")
        print(f"  Zaakceptowane oferty - skopiuj z bazy lub sprawdź logi.")
        print(f"{'='*70}")

    # -- Stats -----------------------------------------------------------------

    def show_stats(self):
        conn = sqlite3.connect(DB_PATH)
        total_posts = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        total_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='pending'").fetchone()[0]
        approved = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='approved'").fetchone()[0]
        skipped = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='skipped'").fetchone()[0]

        by_cat = conn.execute(
            "SELECT category, COUNT(*) FROM jobs GROUP BY category ORDER BY COUNT(*) DESC"
        ).fetchall()
        conn.close()

        print(f"\n{'='*50}")
        print(f"  FREELANCE PIPELINE STATS")
        print(f"{'='*50}")
        print(f"  Posts scraped:  {total_posts}")
        print(f"  Jobs found:     {total_jobs}")
        print(f"  ├ Pending:      {pending}")
        print(f"  ├ Approved:     {approved}")
        print(f"  └ Skipped:      {skipped}")
        if by_cat:
            print(f"\n  By category:")
            for cat, count in by_cat:
                print(f"    {cat:15} {count}")
        print(f"{'='*50}")


# -- Full run ------------------------------------------------------------------

async def full_run():
    pipeline = FreelancePipeline()

    print("[1/3] Scraping FB groups...")
    scraper = FBScraper(headless=False)
    new_posts = await scraper.run()

    if not new_posts:
        print("No new posts found. Checking unprocessed from DB...")
        new_posts = get_unprocessed_posts(limit=50)

    print(f"\n[2/3] Processing {len(new_posts)} posts via RTX...")
    pipeline.process_posts(new_posts)

    print("\n[3/3] Opening approval dashboard...")
    pipeline.approval_dashboard()


def demo_run():
    """Test without actual scraping"""
    from fb_scraper import save_post

    pipeline = FreelancePipeline()

    demo_posts = [
        {
            "id": "demo_001", "group_url": "https://facebook.com/groups/test",
            "author": "Marek Nowak",
            "text": "Szukam kogoś do zrobienia strony WWW dla mojej firmy fotograficznej. Potrzebuję galerii, formularza kontaktowego i cennika. WordPress lub coś prostego. Budżet 1000-1500 PLN. Piszcie!",
            "post_url": "https://facebook.com/groups/test/posts/demo_001",
            "scraped_at": datetime.now().isoformat()
        },
        {
            "id": "demo_002", "group_url": "https://facebook.com/groups/test",
            "author": "Anna Wiśniewska",
            "text": "Potrzebuję skryptu do automatycznego pobierania cen z kilku stron (około 5) i zapisywania ich do pliku Excel. Uruchamiany raz dziennie. Python. Płacę 600 PLN.",
            "post_url": "https://facebook.com/groups/test/posts/demo_002",
            "scraped_at": datetime.now().isoformat()
        },
        {
            "id": "demo_003", "group_url": "https://facebook.com/groups/test",
            "author": "Tomasz K",
            "text": "Ktoś poleci dobry sklep z oponami w Poznaniu? Potrzebuję letnich na SUVa.",
            "post_url": "https://facebook.com/groups/test/posts/demo_003",
            "scraped_at": datetime.now().isoformat()
        },
        {
            "id": "demo_004", "group_url": "https://facebook.com/groups/test",
            "author": "Firma XYZ",
            "text": "Zlecę pozycjonowanie strony firmowej. Jesteśmy lokalną firmą budowlaną w Wrocławiu. Chcemy być wyżej w Google na kilka fraz. Budżet 800 PLN/mies. Kontakt: biuro@firmaxyz.pl",
            "post_url": "https://facebook.com/groups/test/posts/demo_004",
            "scraped_at": datetime.now().isoformat()
        },
    ]

    print("[DEMO] Inserting test posts...")
    for post in demo_posts:
        save_post(post)

    posts = get_unprocessed_posts(limit=20)
    print(f"[DEMO] Processing {len(posts)} posts...")
    pipeline.process_posts(posts)

    print("\n[DEMO] Opening approval dashboard...")
    pipeline.approval_dashboard()


# -- Entry point ---------------------------------------------------------------

if __name__ == "__main__":
    if "--run" in sys.argv:
        asyncio.run(full_run())

    elif "--approve" in sys.argv:
        pipeline = FreelancePipeline()
        pipeline.approval_dashboard()

    elif "--stats" in sys.argv:
        pipeline = FreelancePipeline()
        pipeline.show_stats()

    elif "--demo" in sys.argv:
        demo_run()

    else:
        print("Freelance Pipeline")
        print("-" * 40)
        print("  --run      Full pipeline (scrape + process + approve)")
        print("  --approve  Review pending proposals")
        print("  --stats    Show stats")
        print("  --demo     Test with dummy data (no FB scraping)")
        print()
        print("First time setup:")
        print("  python fb_scraper.py --login   # Log into Facebook")
        print("  python freelance_pipeline.py --demo   # Test the pipeline")
