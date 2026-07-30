WITH tb_abt AS (SELECT t1.*,coalesce(t2.rankdriver, 0) AS flChampion
  FROM `workspace_matheus_silver`.`fs_f1_driver_all` AS t1

  LEFT JOIN `workspace_matheus_silver`.`f1_champions` AS t2
  ON t1.driverid_life = t2.driverid 
  AND (EXTRACT(YEAR FROM t1.dt_ref_life)) = t2.year

  WHERE t1.dt_ref_life >= date('2000-01-01')
  AND t1.dt_ref_life < date('2026-01-01')
  )

SELECT * FROM tb_abt