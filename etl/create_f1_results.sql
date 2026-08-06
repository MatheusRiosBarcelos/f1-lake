CREATE OR REFRESH STREAMING TABLE lakehouse.bronze.f1_results
TBLPROPERTIES ('delta.feature.timestampNtz' = 'supported')
AS
SELECT *
FROM STREAM read_files(
  's3://datalake-raw-learn/f1/results',
  format => 'parquet'
)