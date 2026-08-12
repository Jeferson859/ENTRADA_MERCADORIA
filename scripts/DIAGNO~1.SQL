-- ═══════════════════════════════════════════════════════════════════
-- DIAGNÓSTICO: códigos da planilha que NÃO casaram com produto.cod_barras
-- Rode DEPOIS de custo_regiao.sql + carga_custo_regiao.sql
-- ═══════════════════════════════════════════════════════════════════

-- 1) Resumo
SELECT
  (SELECT COUNT(DISTINCT codigo) FROM produto_custo_regiao)                        AS codigos_planilha,
  (SELECT COUNT(DISTINCT pcr.codigo) FROM produto_custo_regiao pcr
     JOIN produto pr ON pr.cod_barras = pcr.codigo)                                AS casaram,
  (SELECT COUNT(DISTINCT pcr.codigo) FROM produto_custo_regiao pcr
     WHERE NOT EXISTS (SELECT 1 FROM produto pr WHERE pr.cod_barras = pcr.codigo)) AS nao_casaram;

-- 2) Lista dos que não casaram (com fornecedor para ajudar a identificar)
SELECT DISTINCT pcr.codigo, pcr.fornecedor
FROM produto_custo_regiao pcr
WHERE NOT EXISTS (SELECT 1 FROM produto pr WHERE pr.cod_barras = pcr.codigo)
ORDER BY pcr.codigo;

-- 3) Possíveis quase-casamentos (diferença de maiúsculas/espaços)
SELECT pcr.codigo AS codigo_planilha, pr.cod_barras AS codigo_banco, pr.nome_produto
FROM produto_custo_regiao pcr
JOIN produto pr ON UPPER(TRIM(pr.cod_barras)) = UPPER(TRIM(pcr.codigo))
WHERE pr.cod_barras <> pcr.codigo
ORDER BY pcr.codigo;
