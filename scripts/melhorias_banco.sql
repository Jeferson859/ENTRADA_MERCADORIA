-- ============================================================================
-- MELHORIAS DE BANCO — ENTRADA_MERCADORIA (AdriLar)
-- ============================================================================
-- Rodar manualmente no Postgres como ADMIN.
-- Gerado em 2026-07-09 a partir da análise da camada de dados do app Streamlit.
--
-- ESTRUTURA:
--   1. Índices de performance (seguros, IF NOT EXISTS)
--   2. Queries de AUDITORIA (somente SELECT — não alteram nada)
--   3. UPDATEs de correção — COMENTADOS. Revisar resultado da auditoria
--      correspondente ANTES de descomentar e executar.
--   4. Sugestão de coluna id_empresa em pedido (comentada)
-- ============================================================================


-- ============================================================================
-- 1. ÍNDICES DE PERFORMANCE
-- ============================================================================
-- Aceleram os filtros de período, tipo/status e os JOINs de itens usados
-- em praticamente todas as consultas do db.py.

CREATE INDEX IF NOT EXISTS idx_pedido_data
    ON pedido (data);

CREATE INDEX IF NOT EXISTS idx_pedido_tipo_status
    ON pedido (tipo_pedido, status);

CREATE INDEX IF NOT EXISTS idx_pedido_itens_id_pedido
    ON pedido_itens (id_pedido);

CREATE INDEX IF NOT EXISTS idx_pedido_itens_id_produto
    ON pedido_itens (id_produto);

-- Busca textual (ILIKE '%termo%') em produto: exige pg_trgm + índice GIN.
-- Usado por buscar_pedidos_por_produto e buscar_ids_por_produto.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_produto_nome_trgm
    ON produto USING gin (nome_produto gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_produto_cod_barras_trgm
    ON produto USING gin (cod_barras gin_trgm_ops);


-- ============================================================================
-- 2. AUDITORIA (somente SELECT — não altera dados)
-- ============================================================================

-- 2.1 Inconsistência de cancelamento: cancelado_em preenchido mas status
--     diferente de CANCELADO (o filtro dos dashboards ignora esses pedidos
--     de qualquer forma, mas o dado está inconsistente).
SELECT id, data, status, cancelado_em, valor_total
FROM pedido
WHERE cancelado_em IS NOT NULL
  AND status != 'CANCELADO'
ORDER BY data DESC;

-- 2.2 Inverso: status CANCELADO sem cancelado_em preenchido.
SELECT id, data, status, cancelado_em, valor_total
FROM pedido
WHERE status = 'CANCELADO'
  AND cancelado_em IS NULL
ORDER BY data DESC;

-- 2.3 Pedidos PRE-VENDA válidos sem rota (ficam fora da aba Rotas do dashboard).
SELECT id, data, id_cliente, id_vendedor, status, valor_total
FROM pedido
WHERE tipo_pedido = 'PRE-VENDA'
  AND cancelado_em IS NULL
  AND status != 'CANCELADO'
  AND id_rota IS NULL
ORDER BY valor_total DESC;

-- 2.4 Pedidos cujo valor_total do cabeçalho difere da soma dos itens ATIVOS
--     (explica divergência entre abas Rotas e Produtos do dashboard).
SELECT p.id,
       p.data,
       p.status,
       ROUND(p.valor_total::numeric, 2) AS valor_pedido,
       ROUND(COALESCE(SUM(pi.valor_total)
             FILTER (WHERE COALESCE(pi.status, 'ATIVO') = 'ATIVO'), 0)::numeric, 2) AS valor_itens,
       ROUND((COALESCE(SUM(pi.valor_total)
             FILTER (WHERE COALESCE(pi.status, 'ATIVO') = 'ATIVO'), 0) - p.valor_total)::numeric, 2) AS diferenca
FROM pedido p
JOIN pedido_itens pi ON pi.id_pedido = p.id
GROUP BY p.id, p.data, p.status, p.valor_total
HAVING ROUND(COALESCE(SUM(pi.valor_total)
       FILTER (WHERE COALESCE(pi.status, 'ATIVO') = 'ATIVO'), 0)::numeric, 2)
       <> ROUND(p.valor_total::numeric, 2)
ORDER BY ABS(COALESCE(SUM(pi.valor_total)
       FILTER (WHERE COALESCE(pi.status, 'ATIVO') = 'ATIVO'), 0) - p.valor_total) DESC;

-- 2.5 Itens de pedido com status NULL (o app trata NULL como 'ATIVO' via
--     COALESCE; ideal é normalizar na base).
SELECT pi.id, pi.id_pedido, pi.id_produto, pi.quantidade, pi.valor_total, pi.status
FROM pedido_itens pi
WHERE pi.status IS NULL
ORDER BY pi.id_pedido;

-- 2.6 Clientes sem data de nascimento (ficam fora da análise por faixa etária).
SELECT id_cliente, nome_cliente, data_nascimento, cep_cliente
FROM clientes
WHERE deleted_at IS NULL
  AND data_nascimento IS NULL;

-- 2.7 Clientes sem CEP válido (caem no estado 'Outro' no dashboard
--     vendedor × estado). CEP válido = começa com 5 dígitos.
SELECT id_cliente, nome_cliente, cep_cliente
FROM clientes
WHERE deleted_at IS NULL
  AND (cep_cliente IS NULL OR cep_cliente !~ '^\d{5}');


-- ============================================================================
-- 3. CORREÇÕES — COMENTADAS
-- ============================================================================
-- ATENÇÃO: revisar o resultado da auditoria correspondente (seção 2) ANTES
-- de descomentar. Rodar dentro de uma transação (BEGIN; ... ROLLBACK/COMMIT;)
-- e conferir o número de linhas afetadas.

-- 3.1 Marcar como CANCELADO pedidos com cancelado_em preenchido (ver 2.1):
-- UPDATE pedido
-- SET status = 'CANCELADO'
-- WHERE cancelado_em IS NOT NULL
--   AND status != 'CANCELADO';

-- 3.2 Preencher cancelado_em em pedidos já CANCELADO (ver 2.2).
--     Usa updated_at como melhor aproximação da data de cancelamento:
-- UPDATE pedido
-- SET cancelado_em = COALESCE(updated_at, created_at)
-- WHERE status = 'CANCELADO'
--   AND cancelado_em IS NULL;

-- 3.3 Normalizar status NULL dos itens para 'ATIVO' (ver 2.5):
-- UPDATE pedido_itens
-- SET status = 'ATIVO'
-- WHERE status IS NULL;

-- 3.4 Pedidos PRE-VENDA sem rota (ver 2.3): NÃO há correção automática —
--     a rota correta depende do vendedor/região. Atribuir manualmente, ex.:
-- UPDATE pedido SET id_rota = <id_rota_correta> WHERE id = <id_pedido>;

-- 3.5 Divergência valor_total × soma dos itens (ver 2.4): decidir caso a caso
--     qual valor é o correto. Se o cabeçalho deve refletir os itens ativos:
-- UPDATE pedido p
-- SET valor_total = sub.valor_itens
-- FROM (
--     SELECT pi.id_pedido,
--            COALESCE(SUM(pi.valor_total)
--                FILTER (WHERE COALESCE(pi.status, 'ATIVO') = 'ATIVO'), 0) AS valor_itens
--     FROM pedido_itens pi
--     GROUP BY pi.id_pedido
-- ) sub
-- WHERE sub.id_pedido = p.id
--   AND ROUND(sub.valor_itens::numeric, 2) <> ROUND(p.valor_total::numeric, 2);


-- ============================================================================
-- 4. SUGESTÃO ESTRUTURAL — id_empresa em pedido (COMENTADA)
-- ============================================================================
-- Hoje a empresa do pedido é inferida pelo vendedor
-- (p.id_vendedor IN (SELECT id_vendedor FROM vendedor WHERE id_empresa = X)),
-- o que quebra se um vendedor trocar de empresa. Materializar a coluna:

-- ALTER TABLE pedido
--     ADD COLUMN id_empresa INT REFERENCES empresa(id_empresa);

-- Backfill via vendedor do pedido:
-- UPDATE pedido p
-- SET id_empresa = v.id_empresa
-- FROM vendedor v
-- WHERE v.id_vendedor = p.id_vendedor
--   AND p.id_empresa IS NULL;

-- Índice de apoio após o backfill:
-- CREATE INDEX IF NOT EXISTS idx_pedido_id_empresa ON pedido (id_empresa);

-- Depois disso, ajustar db.py para filtrar por p.id_empresa diretamente.
