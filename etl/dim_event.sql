CREATE MATERIALIZED VIEW `lakehouse`.`gold`.`dim_event` (
    EventId STRING COLLATE UTF8_BINARY,
    Year BIGINT,
    RoundNumber BIGINT,
    OfficialEventName STRING COLLATE UTF8_BINARY,
    EventName STRING COLLATE UTF8_BINARY,
    Country STRING COLLATE UTF8_BINARY,
    Location STRING COLLATE UTF8_BINARY,
    Date DATE,
    rn INT
  ) AS
WITH event AS (SELECT
    EventName AS EventId,
    Year,
    RoundNumber,
    OfficialEventName,
    EventName,
    Country,
    Location,
    CAST(Date AS DATE) AS Date,
    ROW_NUMBER() OVER (PARTITION BY EventName, Year ORDER BY Year DESC) AS rn
  FROM
    lakehouse.bronze.f1_results
)
SELECT
  *
FROM
  event
WHERE
  rn = 1