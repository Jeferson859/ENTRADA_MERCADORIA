-- ═══════════════════════════════════════════════════════════════════
-- CUSTO POR REGIÃO — rode 1x no banco antes de usar a página
-- "Custos & Margem". Seguro re-executar (IF NOT EXISTS).
-- Depois rode scripts/carga_custo_regiao.sql (gerado da planilha).
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS produto_custo_regiao (
    codigo        TEXT        NOT NULL,   -- casa com produto.cod_barras
    uf            CHAR(2)     NOT NULL,   -- GO, TO, PA, MT
    custo         NUMERIC(12,2),
    valor_venda   NUMERIC(12,2),
    fornecedor    TEXT,
    atualizado_em TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (codigo, uf)
);

CREATE INDEX IF NOT EXISTS idx_pcr_uf ON produto_custo_regiao (uf);

COMMENT ON TABLE produto_custo_regiao IS
  'Custo e preço de tabela por produto e estado — fonte: planilha de custos';
