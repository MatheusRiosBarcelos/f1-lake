CREATE OR REFRESH MATERIALIZED VIEW abt_f1_drivers_champion AS(  
    WITH tb_abt AS (SELECT t1.*,coalesce(t2.rankdriver, 0) AS flChampion
    FROM lakehouse.silver.fs_f1_driver_all AS t1

    LEFT JOIN lakehouse.silver.f1_champions AS t2
    ON t1.driverid = t2.driverid
    AND (EXTRACT(YEAR FROM t1.dt_ref)) = t2.year

    -- Sem teto fixo: a ABT acompanha a temporada corrente conforme o lake e
    -- atualizado. Um `< date('2026-01-01')` aqui deixava a temporada de 2026
    -- fora da tabela e impedia a previsao do campeonato em andamento.
    --
    -- Atencao ao rotulo: para a temporada em curso, `flChampion` marca o lider
    -- de pontos ATE a data, nao um campeao confirmado. O treino em
    -- ml_champion/train.py so usa anos encerrados, entao isso nao contamina o
    -- modelo -- mas nao trate essas linhas como verdade historica.
    WHERE t1.dt_ref >= date('2000-01-01')
    )
    SELECT * FROM tb_abt
)
