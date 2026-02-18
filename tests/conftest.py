"""
conftest.py - pytest session configuration
Blocks heavy ML imports (sentence_transformers, transformers) that crash
due to importlib.metadata bug in this Python 3.12 environment.
ReactAgent tests use mocked memory instead.
"""

import sys
from unittest.mock import MagicMock

# Block before any test module imports them.
# sentence_transformers triggers importlib.metadata.packages_distributions()
# which crashes with TypeError on broken package metadata.
_BLOCKED = [
    "sentence_transformers",
    "sentence_transformers.SentenceTransformer",
    "transformers",
    "qdrant_client",
    "qdrant_client.models",
    "memory_system",
]

for _mod in _BLOCKED:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# Ensure memory_system.QdrantMemory is mockable
sys.modules["memory_system"].QdrantMemory = MagicMock()
