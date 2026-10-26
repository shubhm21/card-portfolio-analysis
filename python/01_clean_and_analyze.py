"""
Card Portfolio Analysis — Python pipeline
1) Load raw cards_data.csv
2) Clean + mask sensitive fields (card_number -> last 4, drop CVV)
3) Feature engineering (account age, PIN age, expiry status, limit bands, risk flags)
4) EDA summaries + charts
5) Export cleaned data for SQL and Power BI
Run from the project root:  python python/01_clean_and_analyze.py
"""
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/cards_data.csv"
OUT = ROOT / "data/processed"
FIG = ROOT / "reports/figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

# Snapshot date = latest account-open month in the data (the dataset is a historical extract)
AS_OF = pd.Timestamp("2020-02-29")

# ---------- 1. Load ----------
df = pd.read_csv(RAW)
print(f"Raw shape: {df.shape}")
print("Nulls:", int(df.isna().sum().sum()), "| Duplicate rows:", int(df.duplicated().sum()),
      "| Unique card ids:", df["id"].is_unique)

# ---------- 2. Clean + mask ----------
df = df.rename(columns={"id": "card_id"})
df["card_last4"] = df["card_number"].astype(str).str[-4:]
df = df.drop(columns=["card_number", "cvv"])            # never carry full PAN/CVV downstream
df["credit_limit"] = df["credit_limit"].str.replace("$", "", regex=False).astype(float)
df["expires"] = pd.to_datetime(df["expires"], format="%m/%Y") + pd.offsets.MonthEnd(0)
df["acct_open_date"] = pd.to_datetime(df["acct_open_date"], format="%m/%Y")
df["has_chip"] = df["has_chip"].eq("YES")
df["card_on_dark_web"] = df["card_on_dark_web"].eq("Yes")

# Data-quality assertions
assert (df["expires"] > df["acct_open_date"]).all(), "card expires before account opened"
assert (df["year_pin_last_changed"] >= df["acct_open_date"].dt.year).all(), "PIN changed before account opened"
assert df["credit_limit"].ge(0).all(), "negative credit limit"

# ---------- 3. Feature engineering ----------
df["acct_open_year"] = df["acct_open_date"].dt.year
df["account_age_years"] = ((AS_OF - df["acct_open_date"]).dt.days / 365.25).round(1)
df["pin_age_years"] = AS_OF.year - df["year_pin_last_changed"]
months_to_exp = (df["expires"].dt.year - AS_OF.year) * 12 + (df["expires"].dt.month - AS_OF.month)
df["expiry_status"] = np.select(
    [months_to_exp < 0, months_to_exp <= 12], ["Expired", "Expiring within 12 mo"], "Active")
df["limit_band"] = pd.cut(
    df["credit_limit"], [-1, 0, 1000, 5000, 10000, 20000, 50000, np.inf],
    labels=["$0", "$1-1K", "$1K-5K", "$5K-10K", "$10K-20K", "$20K-50K", "$50K+"]).astype(str)
df["flag_no_chip"] = ~df["has_chip"]
df["flag_stale_pin"] = df["pin_age_years"] >= 10
df["flag_expired"] = df["expiry_status"].eq("Expired")
df["risk_score"] = df[["flag_no_chip", "flag_stale_pin", "flag_expired"]].sum(axis=1)
df["risk_tier"] = df["risk_score"].map({0: "Low", 1: "Medium"}).fillna("High")

# Data-quality flags (kept, not deleted, so the dashboard can filter them)
df["card_life_months"] = ((df["expires"].dt.year - df["acct_open_date"].dt.year) * 12
                          + (df["expires"].dt.month - df["acct_open_date"].dt.month))
df["dq_2020_batch"] = df["acct_open_date"] >= "2020-01-01"   # 1,178 cards in 2 months vs ~100/yr before
df["dq_short_life"] = df["card_life_months"] < 12            # cards valid for under a year

# Client-level table
clients = df.groupby("client_id").agg(
    cards=("card_id", "count"),
    brands=("card_brand", "nunique"),
    total_credit_limit=("credit_limit", "sum"),
    oldest_account=("acct_open_date", "min"),
    max_risk_score=("risk_score", "max"),
    no_chip_cards=("flag_no_chip", "sum"),
).reset_index()

df.to_csv(OUT / "cards_clean.csv", index=False, date_format="%Y-%m-%d")
clients.to_csv(OUT / "clients_summary.csv", index=False, date_format="%Y-%m-%d")

# ---------- 4. EDA ----------
def section(t):
    print("\n" + "=" * 8, t, "=" * 8)

section("KPIs")
kpis = {
    "Total cards": len(df),
    "Clients": df["client_id"].nunique(),
    "Avg cards per client": round(len(df) / df["client_id"].nunique(), 2),
    "Total credit limit": df["credit_limit"].sum(),
    "Avg credit limit": round(df["credit_limit"].mean(), 0),
    "Median credit limit": df["credit_limit"].median(),
    "Chip adoption %": round(df["has_chip"].mean() * 100, 1),
    "Stale PIN (10y+) %": round(df["flag_stale_pin"].mean() * 100, 1),
    "Expired at snapshot %": round(df["flag_expired"].mean() * 100, 1),
    "Cards on dark web": int(df["card_on_dark_web"].sum()),
}
for k, v in kpis.items():
    print(f"{k:24s} {v:,}")
pd.Series(kpis).to_csv(OUT / "kpis.csv", header=["value"])

section("Data quality")
print("Cards opened Jan-Feb 2020:", int(df["dq_2020_batch"].sum()),
      f"({df['dq_2020_batch'].mean():.1%}) | avg/yr 2015-2019:",
      round(df[df["acct_open_year"].between(2015, 2019)].groupby("acct_open_year").size().mean(), 0))
print("Cards with < 12 month validity:", int(df["dq_short_life"].sum()))
print("$0 credit limit cards:", int((df["credit_limit"] == 0).sum()))
df.to_csv(OUT / "cards_clean.csv", index=False, date_format="%Y-%m-%d")

section("Brand x Type")
bt = df.pivot_table(index="card_brand", columns="card_type", values="card_id",
                    aggfunc="count", fill_value=0)
print(bt)
section("Credit limit by type")
print(df.groupby("card_type")["credit_limit"].describe().round(0))
section("Expiry status")
print(df["expiry_status"].value_counts())
section("Risk tier")
print(df["risk_tier"].value_counts())
section("Cards per client")
print(clients["cards"].value_counts().sort_index())
section("Correlation (numeric)")
print(df[["credit_limit", "account_age_years", "pin_age_years", "num_cards_issued"]].corr().round(2))

# ---------- 5. Charts ----------
plt.rcParams.update({"figure.dpi": 120, "axes.spines.top": False, "axes.spines.right": False})

def save(name):
    plt.tight_layout()
    plt.savefig(FIG / name)
    plt.close()

bt.plot(kind="bar", stacked=True, figsize=(8, 4.5), title="Cards by brand and type")
plt.ylabel("Cards"); save("01_brand_type.png")

df.boxplot(column="credit_limit", by="card_type", figsize=(8, 4.5), showfliers=False)
plt.suptitle(""); plt.title("Credit limit by card type (outliers hidden)"); plt.ylabel("USD")
save("02_limit_by_type.png")

df.groupby("acct_open_year").size().plot(figsize=(8, 4.5), marker="o",
    title="Cards opened per year (2020 = Jan-Feb batch anomaly)")
plt.ylabel("Cards"); save("03_open_trend.png")

df["pin_age_years"].value_counts().sort_index().plot(kind="bar", figsize=(8, 4.5),
                                                     title="PIN age at snapshot (years)")
save("04_pin_age.png")

clients["cards"].value_counts().sort_index().plot(kind="bar", figsize=(8, 4.5),
                                                  title="Cards held per client")
save("05_cards_per_client.png")

df["risk_tier"].value_counts().reindex(["Low", "Medium", "High"]).plot(
    kind="bar", color=["#3a7", "#e90", "#d33"], figsize=(6, 4), title="Card risk tier")
save("06_risk_tier.png")

print("\nSaved cleaned data + figures.")
