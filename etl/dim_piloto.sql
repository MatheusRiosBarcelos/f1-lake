CREATE MATERIALIZED VIEW `lakehouse`.`gold`.`dim_piloto` (
    DriverId STRING COLLATE UTF8_BINARY,
    DriverNumber STRING COLLATE UTF8_BINARY,
    BroadcastName STRING COLLATE UTF8_BINARY,
    Abbreviation STRING COLLATE UTF8_BINARY,
    FullName STRING COLLATE UTF8_BINARY,
    FirstName STRING COLLATE UTF8_BINARY,
    LastName STRING COLLATE UTF8_BINARY,
    CountryCode STRING COLLATE UTF8_BINARY,
    HeadshotUrl STRING COLLATE UTF8_BINARY
  ) AS
WITH ranked_drivers AS (SELECT
    DriverId,
    DriverNumber,
    BroadcastName,
    Abbreviation,
    FullName,
    FirstName,
    LastName,
    CountryCode,
    HeadshotUrl,
    ROW_NUMBER() OVER (PARTITION BY DriverId ORDER BY DriverId) AS rn
  FROM
    lakehouse.bronze.f1_results
)
SELECT
  DriverId,
  DriverNumber,
  BroadcastName,
  Abbreviation,
  FullName,
  FirstName,
  LastName,
  CountryCode,
  HeadshotUrl
FROM
  ranked_drivers
WHERE
  rn = 1