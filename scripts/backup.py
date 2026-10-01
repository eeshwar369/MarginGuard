"""Create a consistent SQLite backup without copying a live WAL file."""

import argparse
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path("data/marginguard.sqlite3"))
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    if not args.database.is_file():
        parser.error("The source database does not exist")
    args.destination.mkdir(parents=True, exist_ok=True)
    target = args.destination / ("marginguard-" + datetime.now(UTC).strftime("%Y%m%d-%H%M%S") + ".sqlite3")
    if target.exists():
        parser.error("The target backup already exists; retry in one second")
    with sqlite3.connect(args.database.resolve().as_uri() + "?mode=ro", uri=True) as source:
        with sqlite3.connect(target) as backup:
            source.backup(backup)
            assert backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    print(target)


if __name__ == "__main__":
    main()
