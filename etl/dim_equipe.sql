CREATE MATERIALIZED VIEW `lakehouse`.`gold`.`dim_equipe` (
    TeamId STRING COLLATE UTF8_BINARY,
    TeamName STRING COLLATE UTF8_BINARY,
    TeamColor STRING COLLATE UTF8_BINARY
  ) AS
WITH teams AS (SELECT
    TeamId,
    TeamName,
    TeamColor,
    row_number() OVER (PARTITION BY TeamId ORDER BY TeamId) AS rn
  FROM
    lakehouse.bronze.f1_results
)
SELECT
  TeamId,
  TeamName,
  TeamColor
FROM
  teams
WHERE
  rn = 1