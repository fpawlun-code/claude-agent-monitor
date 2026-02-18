import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from fb_scraper import get_unprocessed_posts, mark_processed
from proposal_generator import FreelanceClassifier, ProposalGenerator

classifier = FreelanceClassifier()
generator = ProposalGenerator()

posts = get_unprocessed_posts(limit=10)
print(f'Processing {len(posts)} posts via RTX...\n')

for p in posts:
    cat = classifier.classify(p['text'])
    print(f'[{cat}] {p["text"][:80]}')
    if cat != 'irrelevant':
        req = classifier.extract_requirements(p['text'])
        prop = generator.generate(p['text'], cat, req)
        print(f'  PROPOSAL: {prop[:200]}')
    mark_processed(p['id'])
    print()
