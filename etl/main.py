#%%

import os
import dotenv
from tqdm.notebook import tqdm
import nekt

# %%

nekt.data_access_token = "NqySJyPGO1Sw7afi2MjBDcXSLFDIbIx4l8jCZH7Ym12DnkRQWp05V4elYQunydGEdVNliULGH4dmxDcRKw9X63H7BwwmD9R6ntbX6hddDgZm30UnIUllk2ztdg1wzXJDWILYguhu7hL4ByLt9yddDsdub9yvugl5molTKTgO2JDrvhAGoBVvgwrGXFjZNup6M4YwhlY6wzKVRICUDss0YxYnSwqSVI7WKTszB9XRKMPOxwwdGSmnOaB5k9PP2VE0"
nekt.engine = 'spark'

# %%

query_dates = """
SELECT DISTINCT date(date) AS dt_ref
FROM f1_results
WHERE year(date) = '{year}'
ORDER BY 1
"""

# Minha query de Feature Store
query = """
WITH 
  results_until_date AS (SELECT * 
    FROM f1_results
    WHERE date(date) <= date('{date}')
    ORDER BY date DESC),

  drivers_selected AS (SELECT DISTINCT driverId
  FROM
    results_until_date
  WHERE YEAR >= (SELECT MAX(YEAR) - 2
    FROM
    results_until_date)),

  tb_results AS (SELECT t1.*
  FROM
    results_until_date AS t1
  INNER JOIN drivers_selected AS t2 ON t1.driverId = t2.driverId
  ORDER BY 
    YEAR
  ),

  tb_life AS (SELECT driverId,
      --Quantidade Seasons
      COUNT(DISTINCT YEAR) AS qtde_seasons,
      --Quantidade seesions
      COUNT(*) AS qtde_sessions,
      SUM(CASE WHEN (status = 'Finished' OR status LIKE '+%') THEN 1 ELSE 0 END) AS qtde_sessions_finesshed,
      SUM(CASE WHEN mode = 'Race' THEN 1 ELSE 0 END) AS qtde_race,
      SUM(CASE WHEN mode = 'Race' AND (status = 'Finished' OR status LIKE '+%') THEN 1 ELSE 0 END) AS qtde_sessions_finesshed_race,
      SUM(CASE WHEN mode = 'Sprint' THEN 1 ELSE 0 END) AS qtde_sprint,
      SUM(CASE WHEN mode = 'Sprint' AND (status = 'Finished' OR status LIKE '+%') THEN 1 ELSE 0 END) AS qtde_sessions_finesshed_sprint,
      --Primeiros Lugares
      SUM(CASE WHEN position = 1  THEN 1 ELSE 0 END) AS qtde_1Pos,
      SUM(CASE WHEN position = 1  AND mode = 'Race' THEN 1 ELSE 0 END) AS qtde_1Pos_race,
      SUM(CASE WHEN position = 1  AND mode = 'Sprint' THEN 1 ELSE 0 END) AS qtde_1Pos_sprint,
      --Podios
      SUM(CASE WHEN position <= 3 THEN 1 ELSE 0 END) AS qtde_Podios,
      SUM(CASE WHEN position <= 3 AND mode = 'Race' THEN 1 ELSE 0 END) AS qtde_Podios_race,
      SUM(CASE WHEN position <= 3 AND mode = 'Sprint' THEN 1 ELSE 0 END) AS qtde_Podios_sprint,
      --Quantidade TOP5 corrida
      SUM(CASE WHEN position <= 5 THEN 1 ELSE 0 END) AS qtde_pos5,
      SUM(CASE WHEN position <= 5 AND mode = 'Race' THEN 1 ELSE 0 END) AS qtde_pos5_race,
      SUM(CASE WHEN position <= 5 AND mode = 'Sprint' THEN 1 ELSE 0 END) AS qtde_pos5_sprint,
      --Quantidade TOP5 GRID
      SUM(CASE WHEN gridposition <= 5 THEN 1 ELSE 0 END) AS qtde_gridpos5,
      SUM(CASE WHEN gridposition <= 5 AND mode = 'Race' THEN 1 ELSE 0 END) AS qtde_gridpos5_race,
      SUM(CASE WHEN gridposition <= 5 AND mode = 'Sprint' THEN 1 ELSE 0 END) AS qtde_gridpos5_sprint,
      --Pontos
      SUM(points) AS qtde_points,
      SUM(CASE WHEN mode = 'Race' THEN points END) AS qtde_points_race,
      SUM(CASE WHEN mode = 'Sprint' THEN points END) AS qtde_points_sprint,
      --Média Posição (GRID e POSIÇÂO FINAL (tanto para RACE/SPRINT))
      AVG(gridposition) AS avg_gridposition,
      AVG(CASE WHEN mode = 'Race' THEN gridposition END) AS avg_gridposition_race,
      AVG(CASE WHEN mode = 'Sprint' THEN gridposition END) AS avg_gridposition_sprint,
      AVG(POSITION) AS avg_position,
      AVG(CASE WHEN mode = 'Race' THEN POSITION END) AS avg_position_race,
      AVG(CASE WHEN mode = 'Sprint' THEN POSITION END) AS avg_position_sprint,
      --Quantidade de Poles (Primeira posição no grid de largada)
      SUM(CASE WHEN gridposition = 1 THEN 1 ELSE 0 END) AS qtde_1_gridposition,
      SUM(CASE WHEN gridposition = 1 AND mode = 'Race' THEN 1 ELSE 0 END) AS qtde_1_gridposition_race,
      SUM(CASE WHEN gridposition = 1 AND mode = 'Sprint' THEN 1 ELSE 0 END) AS qtde_1_gridposition_sprint,
      --Quantidade de Pole e Primeiro lugar
      SUM(CASE WHEN gridposition = 1 AND POSITION = 1 THEN 1 ELSE 0 END) AS qtde_pole_win,
      SUM(CASE WHEN gridposition = 1 AND POSITION = 1 AND mode = 'Race' THEN 1 ELSE 0 END) AS qtde_pole_win_race,
      SUM(CASE WHEN gridposition = 1 AND POSITION = 1 AND mode = 'Sprint' THEN 1 ELSE 0 END) AS qtde_pole_win_sprint,
      --Quantidade de Seções pontuando
      SUM(CASE WHEN points > 0 THEN 1 ELSE 0 END) AS qtde_sessions_with_points,
      SUM(CASE WHEN points > 0 AND mode = 'Race' THEN 1 ELSE 0 END) AS qtde_sessions_with_points_race,
      SUM(CASE WHEN points > 0 AND mode= 'Sprint' THEN 1 ELSE 0 END) AS qtde_sessions_with_points_sprint,
      --Quantidade de Seções com ultrapassagem
      SUM(CASE WHEN position < gridposition THEN 1 ELSE 0 END) AS qtde_sessions_with_overtake,
      SUM(CASE WHEN position < gridposition AND mode =  'Race' THEN 1 ELSE 0 END) AS qtde_sessions_with_overtake_race,
      SUM(CASE WHEN position < gridposition AND mode =  'Sprint' THEN 1 ELSE 0 END) AS qtde_sessions_with_overtake_sprint,
      --Média de Ultrapassagens
      AVG(gridposition - position) AS avg_overtake,
      AVG(CASE WHEN mode = 'Race' THEN gridposition - position END) AS avg_overtake_race,
      AVG(CASE WHEN mode = 'Sprint' THEN gridposition - position END) AS avg_overtake_sprint
  FROM
    tb_results
  GROUP BY driverId)
SELECT 
  date('{date}') AS dt_ref, *
  FROM tb_life
ORDER BY 
  driverid
"""

#Carregamento das minhas tabelas necessárias para query
(nekt.load_table(layer_name = "Bronze", table_name = "f1_results").createOrReplaceTempView("f1_results"))

# Sessão Spark
spark = nekt.get_spark_session()

years = list(range(1991,2025))

for y in years:
  dates = spark.sql(query_dates.format(year=y)).toPandas()['dt_ref'].astype(str).tolist()
  df_all = spark.sql(query.format(date=dates.pop(0)))

  for dt in dates:
    df_all = df_all.union(spark.sql(query.format(date=dt)))
    
  # Salva DataFrame resultante da query
  nekt.save_table(
    df=df_all,
    layer_name='Silver',
    table_name='fs_f1_driver_life',
    folder_name='F1',
    mode='append'
  )
  
  del(df_all)
