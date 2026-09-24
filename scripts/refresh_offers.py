"""Run the conservative Mak3Deals source-health refresh.

For local testing:
    python scripts/refresh_offers.py --dry-run

The production scheduler should call the protected web hook instead of writing
to a separate cron job's SQLite file. See FEED_PIPELINE.md.
"""

import argparse
import json
import sqlite3
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from offer_pipeline import refresh_sources  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    connection = sqlite3.connect(ROOT / "deals.db")
    connection.row_factory = sqlite3.Row
    try:
        print(json.dumps(refresh_sources(connection, dry_run=args.dry_run), indent=2))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
