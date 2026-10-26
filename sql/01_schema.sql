-- =========================================================
-- Card Portfolio Analysis — schema
-- Tested on SQLite; runs on PostgreSQL / SQL Server with the
-- type tweaks noted in comments.
-- Star schema: dim_client  1 ── *  fact_cards
-- =========================================================

DROP TABLE IF EXISTS fact_cards;
DROP TABLE IF EXISTS dim_client;

CREATE TABLE dim_client (
    client_id           INTEGER PRIMARY KEY,
    cards               INTEGER NOT NULL,
    brands              INTEGER NOT NULL,
    total_credit_limit  DECIMAL(12,2) NOT NULL,
    oldest_account      DATE NOT NULL,
    max_risk_score      INTEGER NOT NULL,
    no_chip_cards       INTEGER NOT NULL
);

CREATE TABLE fact_cards (
    card_id               INTEGER PRIMARY KEY,
    client_id             INTEGER NOT NULL REFERENCES dim_client(client_id),
    card_brand            VARCHAR(20) NOT NULL,
    card_type             VARCHAR(20) NOT NULL,
    expires               DATE NOT NULL,
    has_chip              SMALLINT NOT NULL,      -- 1/0  (BIT in SQL Server, BOOLEAN in Postgres)
    num_cards_issued      INTEGER NOT NULL,
    credit_limit          DECIMAL(12,2) NOT NULL,
    acct_open_date        DATE NOT NULL,
    year_pin_last_changed INTEGER NOT NULL,
    card_on_dark_web      SMALLINT NOT NULL,
    card_last4            CHAR(4) NOT NULL,       -- full card number and CVV are never loaded
    acct_open_year        INTEGER NOT NULL,
    account_age_years     DECIMAL(5,1) NOT NULL,
    pin_age_years         INTEGER NOT NULL,
    expiry_status         VARCHAR(30) NOT NULL,
    limit_band            VARCHAR(12) NOT NULL,
    flag_no_chip          SMALLINT NOT NULL,
    flag_stale_pin        SMALLINT NOT NULL,
    flag_expired          SMALLINT NOT NULL,
    risk_score            INTEGER NOT NULL,
    risk_tier             VARCHAR(10) NOT NULL,
    card_life_months      INTEGER NOT NULL,
    dq_2020_batch         SMALLINT NOT NULL,
    dq_short_life         SMALLINT NOT NULL
);

CREATE INDEX ix_cards_client ON fact_cards(client_id);
CREATE INDEX ix_cards_brand_type ON fact_cards(card_brand, card_type);
