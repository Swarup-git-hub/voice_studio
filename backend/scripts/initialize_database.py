from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, inspect, text


BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database.connection import Base  # noqa: E402
from app.database import models as database_models  # noqa: F401,E402


def build_database_url(database_path: Path) -> str:
    return "sqlite:///" + database_path.resolve().as_posix()


def initialize_database(
    database_path: Path,
    *,
    allow_existing: bool,
) -> dict[str, Any]:
    resolved_path = database_path.resolve()
    existed_before = resolved_path.exists()
    size_before = resolved_path.stat().st_size if existed_before else 0

    if existed_before and size_before > 0 and not allow_existing:
        raise RuntimeError(
            "Refusing to modify an existing non-empty database. "
            "Use --allow-existing only when intentional."
        )

    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(
        build_database_url(resolved_path),
        connect_args={"check_same_thread": False},
    )

    try:
        Base.metadata.create_all(bind=engine)
        table_names = sorted(inspect(engine).get_table_names())

        if not table_names:
            raise RuntimeError("Database metadata produced no tables.")

        row_counts: dict[str, int] = {}

        with engine.connect() as connection:
            for table_name in table_names:
                escaped_name = table_name.replace('"', '""')
                row_count = connection.execute(
                    text(f'SELECT COUNT(*) FROM "{escaped_name}"')
                ).scalar_one()
                row_counts[table_name] = int(row_count)

            integrity_result = connection.execute(
                text("PRAGMA integrity_check")
            ).scalar_one()

        non_empty_tables = {
            table_name: row_count
            for table_name, row_count in row_counts.items()
            if row_count != 0
        }

        if non_empty_tables:
            raise RuntimeError(
                "Database is not clean. "
                f"Non-empty tables: {non_empty_tables}"
            )

        if str(integrity_result).lower() != "ok":
            raise RuntimeError(
                f"SQLite integrity check failed: {integrity_result}"
            )

        return {
            "status": "created",
            "database_path": str(resolved_path),
            "existed_before": existed_before,
            "size_before": size_before,
            "size_after": resolved_path.stat().st_size,
            "tables": table_names,
            "row_counts": row_counts,
            "integrity_check": str(integrity_result),
            "clean": True,
        }
    finally:
        engine.dispose()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create or validate an empty AI Voice Studio SQLite database."
        )
    )
    parser.add_argument(
        "--database-path",
        type=Path,
        default=BACKEND_ROOT / "voice.db",
        help="SQLite path. Defaults to backend/voice.db.",
    )
    parser.add_argument(
        "--allow-existing",
        action="store_true",
        help=(
            "Allow validation of an existing database. "
            "The command still fails if any application table contains rows."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the result as JSON.",
    )
    return parser


def main() -> int:
    arguments = build_parser().parse_args()

    try:
        result = initialize_database(
            arguments.database_path,
            allow_existing=arguments.allow_existing,
        )
    except Exception as error:
        payload = {
            "status": "error",
            "error": str(error),
        }

        if arguments.json:
            print(json.dumps(payload, ensure_ascii=False))
        else:
            print(
                f"Database initialisation failed: {error}",
                file=sys.stderr,
            )

        return 1

    if arguments.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print("AI Voice Studio database initialised.")
        print("Database:", result["database_path"])
        print("Tables:", ", ".join(result["tables"]))
        print("Clean:", result["clean"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
