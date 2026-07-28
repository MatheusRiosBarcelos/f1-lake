WITH 
  results_until_date AS (SELECT * 
    FROM `workspace_matheus_bronze`.`f1_results`
    WHERE date(date) <= date('2024-04-21')
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
    AVG(CASE WHEN mode = 'Sprint' THEN gridposition - position END) AS avg_overtake_sprint,
FROM
  tb_results
GROUP BY driverId)

SELECT * FROM tb_life