# Raw data (not committed)

`cards_data.csv` (6,146 rows × 13 columns) contains full synthetic card numbers and CVVs, so it is excluded from version control on purpose.

1. Download `cards_data.csv` from the public **Financial Transactions Dataset** on Kaggle.
2. Save it here as `data/raw/cards_data.csv`.
3. Run `python python/01_clean_and_analyze.py` — the first step masks card numbers to the last 4 digits and drops CVVs.
