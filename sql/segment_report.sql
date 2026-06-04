-- Customer Risk Segmentation using Lending Club grade.
-- grade A-G is analogous to CIBIL bureau bands used in Indian banking:
--   A,B  -> Low Risk   (prime borrowers)
--   C,D  -> Medium Risk
--   E,F,G-> High Risk  (subprime)

SELECT
    CASE
        WHEN grade IN ('A', 'B')      THEN 'Low Risk'
        WHEN grade IN ('C', 'D')      THEN 'Medium Risk'
        WHEN grade IN ('E', 'F', 'G') THEN 'High Risk'
        ELSE                               'Unrated'
    END                                                  AS risk_band,
    COUNT(*)                                             AS customer_count,
    ROUND(AVG(TARGET) * 100.0, 2)                        AS actual_default_rate,
    ROUND(SUM(loan_amnt) / 1000000.0, 2)                 AS exposure_mn,
    ROUND(AVG(loan_amnt), 0)                             AS avg_loan_size,
    ROUND(AVG(int_rate), 2)                              AS avg_interest_rate
FROM loan_applications
WHERE grade IS NOT NULL
GROUP BY risk_band
ORDER BY actual_default_rate DESC;
