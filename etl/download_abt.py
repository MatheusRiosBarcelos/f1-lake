import nekt

nekt.data_access_token = "NqySJyPGO1Sw7afi2MjBDcXSLFDIbIx4l8jCZH7Ym12DnkRQWp05V4elYQunydGEdVNliULGH4dmxDcRKw9X63H7BwwmD9R6ntbX6hddDgZm30UnIUllk2ztdg1wzXJDWILYguhu7hL4ByLt9yddDsdub9yvugl5molTKTgO2JDrvhAGoBVvgwrGXFjZNup6M4YwhlY6wzKVRICUDss0YxYnSwqSVI7WKTszB9XRKMPOxwwdGSmnOaB5k9PP2VE0"

nekt.engine = 'spark'

spark = nekt.get_spark_session()

(nekt.load_table(layer_name = "Silver", table_name = "fs_f1_driver_all").createOrReplaceTempView("fs_f1_driver_all"))
(nekt.load_table(layer_name = "Silver", table_name = "f1_champions").createOrReplaceTempView("f1_champions"))

query = """

WITH tb_abt AS (
    SELECT t1.*,
        coalesce(t2.rankdriver, 0) AS flChampion
    
    FROM fs_f1_driver_all AS t1
    
    LEFT JOIN f1_champions AS t2
    ON t1.driverid_life = t2.driverid 
    AND (EXTRACT(YEAR FROM t1.dt_ref_life)) = t2.year
    
    WHERE t1.dt_ref_life >= date('2000-01-01')
    AND t1.dt_ref_life < date('2026-01-01')
    
    ORDER BY dt_ref_life DESC, driverid
)

SELECT * FROM tb_abt

"""

df= spark.sql(query).toPandas()

df.to_csv("../data/abt_f1_drivers_champion.csv", 
          index=False,
          sep=';')
