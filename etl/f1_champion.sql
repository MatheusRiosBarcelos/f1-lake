CREATE OR REFRESH MATERIALIZED VIEW f1_champions AS
WITH year_driver_points AS (
  SELECT 
    CAST(YEAR AS BIGINT) AS YEAR,
    driverId , 
    SUM(points) as totalPoints
  FROM 
    lakehouse.bronze.f1_results
  WHERE 
    mode IN ('Race', 'Sprint')
  GROUP BY 
    CAST(YEAR AS BIGINT), driverId
),

rn_year_drive AS (
SELECT 
  *,
  ROW_NUMBER() OVER (
    PARTITION BY
     YEAR 
    ORDER BY 
     totalPoints DESC
  ) AS rankDriver
FROM 
  year_driver_points

)
SELECT
  *
FROM 
  rn_year_drive
WHERE 
  rankDriver = 1
ORDER BY
  YEAR