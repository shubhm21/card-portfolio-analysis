"""
Load the cleaned CSVs into a SQLite database (data/cards.db) using sql/01_schema.sql,
then run every query in sql/02_analysis.sql and save each result to reports/sql_results/.
Swap the connection for PostgreSQL / SQL Server via SQLAlchemy if you prefer.
Run from the project root:  python python/02_load_to_sql.py
"""
from pathlib import Path
import re
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/cards.db"
RES = ROOT / "reports/sql_results"
RES.mkdir(parents=True, exist_ok=True)

cards = pd.read_csv(ROOT / "data/processed/cards_clean.csv", dtype={"card_last4": str})
clients = pd.read_csv(ROOT / "data/processed/clients_summary.csv")
for c in cards.columns:
    if cards[c].dtype == bool:
        cards[c] = cards[c].astype(int)

con = sqlite3.connect(DB)
con.executescript((ROOT / "sql/01_schema.sql").read_text())
clients.to_sql("dim_client", con, if_exists="append", index=False)
cards.to_sql("fact_cards", con, if_exists="append", index=False)
print("Loaded:", con.execute("SELECT COUNT(*) FROM fact_cards").fetchone()[0], "cards,",
      con.execute("SELECT COUNT(*) FROM dim_client").fetchone()[0], "clients")

# Run each named query block:  -- Q01: title  ... ;
sql = (ROOT / "sql/02_analysis.sql").read_text()
for m in re.finditer(r"-- (Q\d+): (.+?)\n(.*?;)", sql, re.S):
    qid, title, body = m.groups()
    out = pd.read_sql_query(body, con)
    out.to_csv(RES / f"{qid}.csv", index=False)
    print(f"\n{qid}: {title}\n{out.head(12).to_string(index=False)}")
con.close()
