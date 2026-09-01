CREATE MATERIALIZED VIEW `lakehouse`.`gold`.`fato_resultados` (
    DriverId STRING COLLATE UTF8_BINARY,
    TeamId STRING COLLATE UTF8_BINARY,
    EventId STRING COLLATE UTF8_BINARY,
    Mode STRING COLLATE UTF8_BINARY,
    Position DOUBLE,
    ClassifiedPosition STRING COLLATE UTF8_BINARY,
    GridPosition DOUBLE,
    Time_seg DOUBLE,
    Status STRING COLLATE UTF8_BINARY,
    Points DOUBLE,
    Laps DOUBLE
  ) AS
WITH resultados AS (SELECT
    DriverId,
    TeamId,
    EventName AS EventId,
    Mode,
    Position,
    ClassifiedPosition,
    GridPosition,
    CASE
      WHEN Time IS NULL THEN NULL
      ELSE Time / 1e9
    END AS Time_seg,
    Status,
    Points,
    Laps
  FROM
    lakehouse.bronze.f1_results
)
SELECT
  *
FROM
  resultados