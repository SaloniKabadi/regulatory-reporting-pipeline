-- Regulatory Report: Default Rate Summary by Loan Type
-- Mirrors RBI NPA classification reporting format.
-- "Defaulted" = Charged Off, Default, or Late (31-120 days).

WITH portfolio_base AS (
    SELECT
        contract_type,
        COUNT(*)                                            AS total_accounts,
        SUM(TARGET)                                         AS defaulted_accounts,
        SUM(loan_amnt)                                      AS total_exposure,
        SUM(CASE WHEN TARGET = 1 THEN loan_amnt ELSE 0 END) AS npa_exposure,
        AVG(annual_inc)                                     AS avg_income
    FROM loan_applications
    WHERE contract_type IS NOT NULL
    GROUP BY contract_type
)
SELECT
    contract_type                                           AS loan_type,
    total_accounts,
    defaulted_accounts,
    ROUND(defaulted_accounts * 100.0 / total_accounts, 2)   AS default_rate_pct,
    ROUND(total_exposure / 1000000.0, 2)                    AS total_exposure_mn,
    ROUND(npa_exposure   / 1000000.0, 2)                    AS npa_exposure_mn,
    ROUND(npa_exposure  * 100.0 / total_exposure, 2)        AS npa_ratio_pct,
    ROUND(avg_income, 0)                                    AS avg_customer_income
FROM portfolio_base
ORDER BY default_rate_pct DESC;
