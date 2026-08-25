import os
import sys

import chromadb
from chromadb.config import Settings

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.config import VECTOR_INDEX_DIR

PAPER_VECTOR_DIR = os.path.join(VECTOR_INDEX_DIR, "paper_vector")

print(f"Checking ChromaDB at: {PAPER_VECTOR_DIR}")

if not os.path.exists(PAPER_VECTOR_DIR):
    print("❌ Directory does not exist.")
    exit(1)

try:
    client = chromadb.PersistentClient(
        path=PAPER_VECTOR_DIR,
        settings=Settings(anonymized_telemetry=False)
    )
    print("✅ Client connected.")

    collections = client.list_collections()
    print(f"📚 Found {len(collections)} collections:")
    for col in collections:
        print(f"   - Name: {col.name}, ID: {col.id}")
        print(f"     Count: {col.count()}")

except Exception as e:
    print(f"❌ Error: {e}")
