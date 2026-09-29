"""Run the daily safe retailer-source discovery pass locally.

The production scheduler should call the protected web hook so it writes to
the same database as the web service. This CLI is for staging/operations.
"""

import argparse
import json
import os
import sqlite3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from retailer_deals import discover_retailer_deals, ensure_retailer_deal_schema  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-url-check", action="store_true", help="Skip official source reachability checks")
    args = parser.parse_args()
    database_path = os.environ.get("MAK3DEALS_DATABASE", str(ROOT / "deals.db"))
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        ensure_retailer_deal_schema(connection)
        print(json.dumps(discover_retailer_deals(connection, check_urls=not args.no_url_check), indent=2))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
