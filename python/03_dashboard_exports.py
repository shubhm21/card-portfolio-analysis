"""
Build the aggregated tables that feed the dashboard (reports/dashboard_data/).
Every table is pre-computed for every filter combination so the dashboard's
filters (brand, card type, include/exclude the Jan-Feb 2020 batch) work instantly:
  f_brand  in All, Amex, Discover, Mastercard, Visa
  f_type   in All, Credit, Debit, Debit (Prepaid)
  f_batch  in include, exclude
Run after 01_clean_and_analyze.py:  python python/03_dashboard_exports.py
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/dashboard_data"
OUT.mkdir(parents=True, exist_ok=True)
base = pd.read_csv(ROOT / "data/processed/cards_clean.csv")

BRANDS = ["All"] + sorted(base["card_brand"].unique())
TYPES = ["All"] + sorted(base["card_type"].unique())
BAND_ORDER = ["$0", "$1-1K", "$1K-5K", "$5K-10K", "$10K-20K", "$20K-50K", "$50K+"]


def kpis(df):
    n = len(df)
    np_ = df[df["card_type"] != "Debit (Prepaid)"]
    hr = df["risk_tier"] == "High"
    return pd.DataFrame([{
        "total_cards": n,
        "clients": df["client_id"].nunique(),
        "cards_per_client": round(n / df["client_id"].nunique(), 2),
        "total_credit_limit": df["credit_limit"].sum(),
        "avg_limit_excl_prepaid": round(np_["credit_limit"].mean(), 0) if len(np_) else None,
        "chip_rate": round(df["has_chip"].mean(), 4),
        "no_chip_cards": int((~df["has_chip"]).sum()),
        "stale_pin_rate": round(df["flag_stale_pin"].mean(), 4),
        "avg_pin_age": round(df["pin_age_years"].mean(), 1),
        "high_risk_cards": int(hr.sum()),
        "high_risk_rate": round(hr.mean(), 4),
        "expired_cards": int((df["expiry_status"] == "Expired").sum()),
        "expiring_12mo_cards": int((df["expiry_status"] == "Expiring within 12 mo").sum()),
        "reissue_pipeline_cards": int((df["expiry_status"] != "Active").sum()),
        "reissue_pipeline_rate": round((df["expiry_status"] != "Active").mean(), 4),
        "reissue_limit": df.loc[df["expiry_status"] != "Active", "credit_limit"].sum(),
        "batch_2020_cards": int(df["dq_2020_batch"].sum()),
    }])


def mix(df):
    return (df.groupby(["card_brand", "card_type"])
              .agg(cards=("card_id", "count"), total_limit=("credit_limit", "sum"),
                   avg_limit=("credit_limit", "mean")).round(0).reset_index())


def opened(df):
    o = df.groupby("acct_open_year").agg(cards=("card_id", "count")).reset_index()
    o["is_2020_batch"] = o["acct_open_year"] == 2020
    return o


def bands(df):
    b = df.groupby(["limit_band", "card_type"]).size().rename("cards").reset_index()
    b["band_order"] = b["limit_band"].map(BAND_ORDER.index)
    return b.sort_values(["band_order", "card_type"])


def risk(df):
    r = df.groupby(["card_brand", "risk_tier"]).size().rename("cards").reset_index()
    r["share_of_brand"] = (r["cards"] / r.groupby("card_brand")["cards"].transform("sum")).round(4)
    return r


def expiry(df):
    return (df.groupby(["expiry_status", "card_type"])
              .agg(cards=("card_id", "count"), credit_limit=("credit_limit", "sum")).reset_index())


def flags(df):
    n = len(df)
    rows = [("No chip", int(df["flag_no_chip"].sum())),
            ("PIN unchanged 10+ yrs", int(df["flag_stale_pin"].sum())),
            ("Expired", int(df["flag_expired"].sum())),
            ("2+ flags (High risk)", int((df["risk_score"] >= 2).sum())),
            ("All 3 flags", int((df["risk_score"] == 3).sum()))]
    out = pd.DataFrame(rows, columns=["flag", "cards"])
    out["share"] = (out["cards"] / n).round(4)
    return out


def pin_age(df):
    return df.groupby("pin_age_years").size().rename("cards").reset_index()


def per_client(df):
    c = df.groupby("client_id").size().value_counts().sort_index()
    return c.rename_axis("cards_held").rename("clients").reset_index()


def outreach(df):
    hr = df[df["risk_tier"] == "High"]
    return (hr.groupby("client_id")
              .agg(high_risk_cards=("card_id", "count"), no_chip=("flag_no_chip", "sum"),
                   stale_pin=("flag_stale_pin", "sum"), expired=("flag_expired", "sum"),
                   limit_exposed=("credit_limit", "sum"))
              .query("high_risk_cards >= 2")
              .sort_values(["high_risk_cards", "limit_exposed"], ascending=False)
              .reset_index())


TABLES = {"kpis": kpis, "brand_type_mix": mix, "cards_opened_by_year": opened,
          "limit_bands": bands, "risk_by_brand": risk, "expiry_by_type": expiry,
          "risk_flags": flags, "pin_age": pin_age, "cards_per_client": per_client,
          "outreach_clients": outreach}
parts = {k: [] for k in TABLES}

for b in BRANDS:
    for t in TYPES:
        for batch in ["include", "exclude"]:
            df = base
            if b != "All":
                df = df[df["card_brand"] == b]
            if t != "All":
                df = df[df["card_type"] == t]
            if batch == "exclude":
                df = df[~df["dq_2020_batch"]]
            if df.empty:
                continue          # e.g. Amex + Debit does not exist
            for name, fn in TABLES.items():
                part = fn(df)
                part.insert(0, "f_batch", batch)
                part.insert(0, "f_type", t)
                part.insert(0, "f_brand", b)
                parts[name].append(part)

for name, p in parts.items():
    out = pd.concat(p, ignore_index=True)
    if name == "outreach_clients":
        out.insert(0, "row_id", out["f_brand"] + "|" + out["f_type"] + "|" + out["f_batch"]
                   + "|" + out["client_id"].astype(str))
    out.to_csv(OUT / f"{name}.csv", index=False)

# Whole-file data-quality audit (not filtered)
n = len(base)
dq = pd.DataFrame([
    {"check": "Opened Jan-Feb 2020 (batch anomaly)", "cards": int(base["dq_2020_batch"].sum())},
    {"check": "Valid for under 12 months", "cards": int(base["dq_short_life"].sum())},
    {"check": "$0 credit limit", "cards": int((base["credit_limit"] == 0).sum())},
    {"check": "Debit cards carrying a credit limit",
     "cards": int(((base["card_type"] == "Debit") & (base["credit_limit"] > 0)).sum())},
    {"check": "Flagged on dark web", "cards": int(base["card_on_dark_web"].sum())},
])
dq["share"] = (dq["cards"] / n).round(4)
dq.to_csv(OUT / "data_quality.csv", index=False)

for f in sorted(OUT.glob("*.csv")):
    print(f"{f.name:28s} {len(pd.read_csv(f)):6d} rows  {f.stat().st_size/1024:7.1f} KB")
