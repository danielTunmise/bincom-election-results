"""
Convert the MySQL dump (bincom_test.sql) into a SQLite database (db.sqlite3).

Usage:
    python import_mysql_dump.py                 # uses bincom_test.sql -> db.sqlite3
    python import_mysql_dump.py dump.sql out.db

How it works (simple, line based - the dump is a plain phpMyAdmin export):
  1. Read the dump line by line.
  2. CREATE TABLE blocks: rewrite MySQL column types to SQLite ones.
  3. INSERT statements: only swap MySQL backticks for double quotes
     (SQLite accepts multi-row INSERT ... VALUES (...),(...); as is).
  4. Everything else (SET, DROP, /*! ... */ comments) is skipped.
"""
import re
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def mysql_type_to_sqlite(mysql_type: str) -> str:
    """int(11) -> INTEGER, varchar/char/text/datetime -> TEXT."""
    return "INTEGER" if mysql_type.lower().startswith("int") else "TEXT"


def convert_create_table(block: list) -> str:
    """Turn the lines of one MySQL CREATE TABLE into a SQLite CREATE TABLE."""
    table = re.search(r"`(\w+)`", block[0]).group(1)
    columns, primary_key = [], None
    for line in block[1:]:
        line = line.strip()
        if line.startswith(")"):          # ") ENGINE=InnoDB ..." ends the block
            break
        if line.startswith("PRIMARY KEY"):
            primary_key = re.search(r"\(`(\w+)`\)", line).group(1)
            continue
        m = re.match(r"`(\w+)`\s+(\w+)(?:\(\d+\))?(.*?),?$", line)
        name, col_type, rest = m.group(1), m.group(2), m.group(3)
        col_sql = f'"{name}" {mysql_type_to_sqlite(col_type)}'
        if "NOT NULL" in rest:
            col_sql += " NOT NULL"
        columns.append((name, col_sql))
    # An INTEGER PRIMARY KEY in SQLite is an auto-incrementing row id.
    cols = [
        sql + " PRIMARY KEY" if name == primary_key else sql
        for name, sql in columns
    ]
    return f'CREATE TABLE "{table}" (\n  ' + ",\n  ".join(cols) + "\n);"


def convert(dump_path: Path, db_path: Path) -> None:
    if db_path.exists():
        db_path.unlink()                  # always start from a clean database
    script = []                           # list of finished SQLite statements
    block = None                          # lines of the CREATE TABLE being read
    insert = None                         # text of the INSERT being read
    for line in dump_path.read_text(encoding="latin-1").splitlines():
        if block is not None:             # inside a CREATE TABLE
            block.append(line)
            if line.startswith(")"):
                script.append(convert_create_table(block))
                block = None
        elif insert is not None:          # inside a multi-line INSERT
            insert += "\n" + line.replace("`", '"')
            if line.rstrip().endswith(";"):
                script.append(insert)
                insert = None
        elif line.startswith("CREATE TABLE"):
            block = [line]
        elif line.startswith("INSERT INTO"):
            insert = line.replace("`", '"')
            if line.rstrip().endswith(";"):
                script.append(insert)
                insert = None
        # anything else (comments, SET, DROP, blank lines) is ignored
    conn = sqlite3.connect(db_path)
    conn.executescript("\n".join(script))
    conn.commit()
    for (table,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
        count = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        print(f"{table:28s} {count} rows")
    conn.close()


if __name__ == "__main__":
    dump = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DIR / "bincom_test.sql"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else BASE_DIR / "db.sqlite3"
    convert(dump, out)
    print(f"\nCreated {out}")
