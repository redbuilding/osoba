#!/usr/bin/env python3
"""
CSV -> MySQL loader for 'shipments' table.

Requires:
  pip install mysql-connector-python

Notes:
  - Expects the table 'shipments' to exist with:
      value_usd DECIMAL(15,2)  -- IMPORTANT: Value may contain decimals like '1277046.00'
      mtons     DECIMAL(12,2)
  - Reads CSV with UTF-8 BOM safely.
  - Converts TRUE/YES/1 to 1 for boolean fields.
  - Strips $, commas, spaces, and parentheses-negatives from numeric fields.
"""

import os
import sys
import csv
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import mysql.connector as mysql

# --- edit these ---
HOST = "localhost"
USER = "portuser"
PWD  = "5h!ppingISmygame"
DB   = "tradestats"
CSV  = "/Users/qasim/Downloads/db.csv"   # full absolute path
# ------------------

# Absolute path to your CSV
CSV_PATH = os.getenv("CSV_PATH", "/Users/qasim/Downloads/db.csv")

# Batch size for executemany()
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1000"))

# Fail-fast? If True, stop on first bad row. If False, skip bad rows and log them.
FAIL_FAST = False

# ----------------------------
# Helpers
# ----------------------------
def clean_num(x: str) -> str:
    """Strip common noise: commas, $, non-breaking spaces, spaces, parentheses-negatives."""
    if x is None:
        return ""
    s = str(x).strip()
    if s == "":
        return ""
    neg = s.startswith("(") and s.endswith(")")
    if neg:
        s = s[1:-1]
    s = (
        s.replace(",", "")
         .replace("$", "")
         .replace("\u00A0", "")  # NBSP
         .replace(" ", "")
    )
    return "-" + s if neg else s

def to_bool(x) -> int:
    return 1 if str(x).strip().upper() in ("TRUE", "T", "1", "YES", "Y") else 0

def to_int(x):
    s = clean_num(x)
    if s == "":
        return None
    try:
        # allow "123.0" -> 123 by converting via Decimal first
        return int(Decimal(s).to_integral_value(rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError):
        raise ValueError(f"Cannot parse int from '{x}'")

def to_dec(x, places="0.01"):
    s = clean_num(x)
    if s == "":
        return None
    try:
        d = Decimal(s)
        # Quantize to 2 decimals by default (for DECIMAL(*,2) columns)
        return d.quantize(Decimal(places), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        raise ValueError(f"Cannot parse decimal from '{x}'")

def null_if_empty(s):
    s = None if s is None else str(s).strip()
    return None if s == "" else s

# ----------------------------
# Column headers expected
# ----------------------------
COLS = [
    "Direction",
    "Year",
    "US Coast",
    "US Port",
    "US PORT STATE",
    "Ultimate Country",
    "Ultimate Region",
    "Commodity Group",
    "HS Code 4 Digit",
    "HS Code 4 Description",
    "IS Containerized",
    "Reefer",
    "Ship Line Name",
    "US Company Name",
    "Value",
    "MTONS",
    "TEUS",
]

# ----------------------------
# SQL
# ----------------------------
INSERT_SQL = """
INSERT INTO shipments
(direction, year, us_coast, us_port, us_port_state, ultimate_country, ultimate_region,
 commodity_group, hs_code_4_digit, hs_code_4_desc, is_containerized, reefer,
 ship_line_name, us_company_name, value_usd, mtons, teus)
VALUES
(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
"""

# ----------------------------
# Main loader
# ----------------------------
def main():
    if not os.path.isfile(CSV_PATH):
        print(f"ERROR: CSV not found at: {CSV_PATH}")
        sys.exit(1)

    conn = mysql.connect(host=HOST, user=USER, password=PWD, database=DB)
    cur = conn.cursor()

    rows_read = 0
    rows_loaded = 0
    rows_failed = 0
    batch = []

    failed_path = os.path.join(os.path.dirname(CSV_PATH), "failed_rows.csv")
    failed_file = open(failed_path, "w", newline="", encoding="utf-8")
    failed_writer = None

    try:
        with open(CSV_PATH, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            # Validate headers
            missing = [c for c in COLS if c not in reader.fieldnames]
            if missing:
                print("ERROR: CSV is missing expected columns:", missing)
                print("Found columns:", reader.fieldnames)
                sys.exit(1)

            for row in reader:
                rows_read += 1
                try:
                    vals = (
                        null_if_empty(row["Direction"]),
                        to_int(row["Year"]),
                        null_if_empty(row["US Coast"]),
                        null_if_empty(row["US Port"]),
                        null_if_empty(row["US PORT STATE"]),
                        null_if_empty(row["Ultimate Country"]),
                        null_if_empty(row["Ultimate Region"]),
                        null_if_empty(row["Commodity Group"]),
                        to_int(row["HS Code 4 Digit"]),
                        null_if_empty(row["HS Code 4 Description"]),
                        to_bool(row["IS Containerized"]),
                        to_bool(row["Reefer"]),
                        null_if_empty(row["Ship Line Name"]),
                        null_if_empty(row["US Company Name"]),
                        to_dec(row["Value"], places="0.01"),   # <-- decimal dollars
                        to_dec(row["MTONS"], places="0.01"),
                        to_int(row["TEUS"]),
                    )
                    batch.append(vals)

                    if len(batch) >= BATCH_SIZE:
                        cur.executemany(INSERT_SQL, batch)
                        conn.commit()
                        rows_loaded += len(batch)
                        batch.clear()

                except Exception as e:
                    rows_failed += 1
                    if FAIL_FAST:
                        raise
                    # Lazily create failed_rows writer with same fieldnames plus error
                    if failed_writer is None:
                        failed_fieldnames = list(reader.fieldnames) + ["__error__"]
                        failed_writer = csv.DictWriter(failed_file, fieldnames=failed_fieldnames)
                        failed_writer.writeheader()
                    row_copy = dict(row)
                    row_copy["__error__"] = str(e)
                    failed_writer.writerow(row_copy)

        # Flush remaining
        if batch:
            cur.executemany(INSERT_SQL, batch)
            conn.commit()
            rows_loaded += len(batch)
            batch.clear()

    finally:
        failed_file.close()
        cur.close()
        conn.close()

    print(f"Done. Read: {rows_read}, Loaded: {rows_loaded}, Failed: {rows_failed}")
    if rows_failed:
        print(f"See failed rows at: {failed_path}")

if __name__ == "__main__":
    main()
