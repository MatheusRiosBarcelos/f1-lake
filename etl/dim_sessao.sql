CREATE MATERIALIZED VIEW `lakehouse`.`gold`.`dim_sessao` (
    Mode STRING COLLATE UTF8_BINARY
      NOT NULL
      COMMENT 'Chave primária - tipo de sessão (valor de origem do FastF1)',
    SessionName STRING COLLATE UTF8_BINARY
      NOT NULL
      COMMENT 'Nome amigável para exibição no Power BI',
    SessionOrder INT NOT NULL COMMENT 'Ordem cronológica da sessão no fim de semana'
  )
  COMMENT 'Dimensão de tipos de sessão (Corrida/Sprint) - grão: 1 linha por Mode' AS
SELECT
  Mode,
  SessionName,
  SessionOrder
FROM
  VALUES ('Sprint', 'Sprint', 1), ('R', 'Corrida', 2) AS t(Mode, SessionName, SessionOrder)