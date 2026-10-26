// =========================================================
// Power Query (M) — paste each query via
// Home > Transform data > New Source > Blank Query > Advanced Editor
// Change ProjectPath to wherever you unzipped the project.
// =========================================================

// ---------- Query 1: ProjectPath (parameter-style text query) ----------
"C:\Users\YOU\card-portfolio-analysis\data\processed\"

// ---------- Query 2: fact_cards ----------
let
    Source   = Csv.Document(File.Contents(ProjectPath & "cards_clean.csv"),
                 [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers  = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Headers, {
        {"card_id", Int64.Type}, {"client_id", Int64.Type},
        {"card_brand", type text}, {"card_type", type text},
        {"expires", type date}, {"has_chip", type logical},
        {"num_cards_issued", Int64.Type}, {"credit_limit", Currency.Type},
        {"acct_open_date", type date}, {"year_pin_last_changed", Int64.Type},
        {"card_on_dark_web", type logical}, {"card_last4", type text},
        {"acct_open_year", Int64.Type}, {"account_age_years", type number},
        {"pin_age_years", Int64.Type}, {"expiry_status", type text},
        {"limit_band", type text}, {"flag_no_chip", type logical},
        {"flag_stale_pin", type logical}, {"flag_expired", type logical},
        {"risk_score", Int64.Type}, {"risk_tier", type text},
        {"card_life_months", Int64.Type}, {"dq_2020_batch", type logical},
        {"dq_short_life", type logical}}),
    // Sort keys so bands and tiers display in logical order (use "Sort by column")
    LimitSort = Table.AddColumn(Typed, "limit_band_sort", each
        List.PositionOf({"$0","$1-1K","$1K-5K","$5K-10K","$10K-20K","$20K-50K","$50K+"}, [limit_band]), Int64.Type),
    RiskSort  = Table.AddColumn(LimitSort, "risk_tier_sort", each
        List.PositionOf({"Low","Medium","High"}, [risk_tier]), Int64.Type)
in
    RiskSort

// ---------- Query 3: dim_client ----------
let
    Source  = Csv.Document(File.Contents(ProjectPath & "clients_summary.csv"),
                [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed   = Table.TransformColumnTypes(Headers, {
        {"client_id", Int64.Type}, {"cards", Int64.Type}, {"brands", Int64.Type},
        {"total_credit_limit", Currency.Type}, {"oldest_account", type date},
        {"max_risk_score", Int64.Type}, {"no_chip_cards", Int64.Type}})
in
    Typed

// ---------- Alternative: load straight from SQL instead of CSV ----------
// SQL Server:  Sql.Database("localhost", "CardsDB", [Query = "SELECT * FROM fact_cards"])
// PostgreSQL:  PostgreSQL.Database("localhost:5432", "cards")
// SQLite:      use the ODBC connector with an SQLite ODBC driver pointing at data/cards.db
