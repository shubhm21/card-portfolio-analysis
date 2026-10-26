# Power BI build guide — Card Portfolio Dashboard

Estimated time: 30–45 minutes in Power BI Desktop (free, Windows).

## 1. Load and model

1. **Get data** → Text/CSV → `data/processed/cards_clean.csv`, then again for `clients_summary.csv`. (Or paste the queries from `01_power_query.m`.)
2. In Power Query, rename the tables `fact_cards` and `dim_client`, check the column types match `01_power_query.m`, then **Close & Apply**.
3. **Modeling → New table** → paste the `DimDate` expression from `02_dax_measures.dax`. Mark it as a date table (Table tools → Mark as date table → `Date`).
4. **Model view** — create relationships:
   - `dim_client[client_id]` 1 → * `fact_cards[client_id]` (single direction)
   - `DimDate[Date]` 1 → * `fact_cards[acct_open_date]` (active)
   - `DimDate[Date]` 1 → * `fact_cards[expires]` (inactive — used by `USERELATIONSHIP`)
5. Sort-by-column: `limit_band` by `limit_band_sort`, `risk_tier` by `risk_tier_sort`.
6. Hide technical columns from report view (sort keys, `dq_*`, `card_life_months`).
7. Create a `_Measures` table and add every measure from `02_dax_measures.dax`. Format: currency for limit measures, % for the % measures, whole number for counts.
8. **View → Themes → Browse for themes** → `03_theme.json`.

## 2. Report pages

### Page 1 — Executive Overview
| Position | Visual | Fields |
|---|---|---|
| Top row | 6 × Card | Total Cards, Clients, Total Credit Limit, Avg Limit (excl. Prepaid), Chip Adoption %, High Risk % |
| Middle left | Clustered bar | Axis `card_brand`, Values `Total Cards`, Legend `card_type` |
| Middle right | Donut | Legend `card_type`, Values `Total Credit Limit` |
| Bottom | Line chart | Axis `DimDate[Year]`, Values `Total Cards` (title: "Cards opened per year") |
| Left rail | Slicers | `card_brand`, `card_type`, `expiry_status`, and a toggle on `dq_2020_batch` |

### Page 2 — Credit Limits
- Column chart: `limit_band` × `Total Cards`, legend `card_type`.
- Box-style view: use a **Scatter** with `account_age_years` (X) vs `credit_limit` (Y), details `card_id`, legend `card_type` — shows there's no age/limit relationship.
- Matrix: rows `card_brand`, columns `card_type`, values `Avg Credit Limit`, conditional formatting background color scale.
- Table: Top 10 clients — `dim_client[client_id]`, `cards`, `total_credit_limit`, with a Top N filter (10 by `Total Credit Limit`).

### Page 3 — Security & Risk
- Cards: No-Chip Cards, Stale PIN %, High Risk Cards, Dark Web Cards.
- 100% stacked bar: `card_brand` × `Total Cards`, legend `risk_tier` (colors Low = green, Medium = amber, High = red).
- Column chart: `pin_age_years` × `Total Cards` (PIN age histogram).
- Table "Outreach list": `client_id`, `High Risk Cards`, `Total Credit Limit` — visual-level filter `High Risk Cards >= 2`.

### Page 4 — Lifecycle & Data Quality
- Stacked column: `expiry_status` × `Total Cards`, legend `card_type`.
- Line chart: `DimDate[Year]` × `Cards Expiring (by expiry date)` — reissue workload by year.
- Card: `2020 Batch %` with subtitle explaining the Jan–Feb 2020 anomaly.
- Text box summarizing the data-quality checks (see README findings).

## 3. Interactions and polish
- Sync slicers across all pages (View → Sync slicers).
- Add a drill-through page on `client_id` showing every card for one client (last-4 only).
- Use `Selected Brand Label` in dynamic titles: Format → Title → fx → field value.
- Add tooltips pages for the brand bar chart showing chip % and avg limit.
- Publish to Power BI Service (optional) and link it from your portfolio/GitHub README.

## 4. Screenshots for your portfolio
Export each page (File → Export → PDF) and save PNGs into `reports/figures/powerbi_*.png`, then reference them in the README.
