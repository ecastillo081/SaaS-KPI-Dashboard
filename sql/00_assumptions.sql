-- Frozen analysis assumptions for the local DuckDB build.
-- {{AS_OF_DATE}} is substituted by src/build_models.py.
-- Gross margin is a global modeled assumption, not observed COGS.
CREATE OR REPLACE VIEW stg.assumptions AS
SELECT
    0.80::DECIMAL(10, 4) AS gross_margin,
    DATE '{{AS_OF_DATE}}' AS as_of_date;
