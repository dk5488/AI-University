"""Standalone script to generate the polity curriculum and cache it as JSON.

Usage:
    python scripts/generate_curriculum.py [--model gemini-2.5-pro]

Reads GEMINI_API_KEY from .env and writes data/curriculum_polity.json.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path

# Ensure the project root is on the path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from app.application.curriculum_service import CurriculumService
from app.memory.in_memory import create_in_memory_memory_service


async def main(model: str) -> None:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set in .env")
        sys.exit(1)

    print(f"Using model: {model}")
    print(f"API key configured: {'yes' if api_key else 'no'}")

    memory_service = create_in_memory_memory_service()
    service = CurriculumService(
        memory_service=memory_service,
        model=model,
        api_key=api_key,
    )

    print("Generating curriculum for 'polity' in bounded batches... (this may take several minutes)")
    start = time.perf_counter()

    try:
        nodes = await service.ensure_curriculum("polity")
        elapsed = time.perf_counter() - start
        print(f"\nSUCCESS! Generated {len(nodes)} nodes in {elapsed:.1f}s")

        # Verify the cache file was written
        cache_file = PROJECT_ROOT / "data" / "curriculum_polity.json"
        if cache_file.exists():
            size_kb = cache_file.stat().st_size / 1024
            print(f"Cached to: {cache_file} ({size_kb:.1f} KB)")
        else:
            print("Cache file was not written; saving manually...")
            service._save_to_file("polity", nodes)
            print(f"Saved to: {cache_file}")

        # Print a summary of top-level nodes
        root_nodes = [n for n in nodes if n.parent_id is None]
        print(f"\nTop-level nodes ({len(root_nodes)}):")
        for n in sorted(root_nodes, key=lambda x: x.learning_order):
            child_count = sum(1 for c in nodes if c.parent_id == n.id)
            print(f"  [{n.learning_order}] {n.title} ({n.level}, {child_count} children)")

    except Exception as e:
        elapsed = time.perf_counter() - start
        print(f"\nFAILED after {elapsed:.1f}s: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate curriculum")
    parser.add_argument(
        "--model",
        default="gemini-2.5-flash",
        help="Model to use (default: gemini-2.5-flash)",
    )
    args = parser.parse_args()
    asyncio.run(main(args.model))
