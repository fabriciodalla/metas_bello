# Pendências e Open Questions — Metas Levo

> Entry point: [PROJECT.md](./PROJECT.md). Esta página nasceu como a **seção visível de ressalvas**
> do plano, aprovado **COM RESSALVAS** pelo gate de qualidade — todas já foram resolvidas
> diretamente pelo usuário desde então (ver resumo no final da página).
>
> **Regra de ouro para quem for codar:** NÃO resolva pendência nova aqui inventando — qualquer
> item futuro precisa de confirmação explícita do usuário antes de virar requisito ou fórmula
> definitiva, do mesmo jeito que P1-P5/H1-H4/O1-O5 foram.

## 1. Pendências de cálculo (5) — todas resolvidas
A arquitetura provê os **pontos de extensão plugáveis** (ver
[architecture.md](./architecture.md#ponto-de-extensão-para-as-fórmulas-plugável)) — fórmula
aprovada não significa fórmula travada: seguem plugáveis por design, caso alguma precise ser revista.

| # | Pendência | Onde encaixa | Status |
|---|---|---|---|
| P1 | Sugestão automática de metas por grupo (para o Gerente) | `SuggestionStrategy` | **RESOLVIDA** — ver Decisão 6 |
| P2 | Distribuição automática Gerente → Coordenador Local | `DistributionStrategy` | **RESOLVIDA** — ver Decisão 6 |
| P3 | Quebra grupo → subgrupo pelo Coordenador Local | `DistributionStrategy` | **RESOLVIDA** — ver Decisão 6 |
| P4 | Distribuição Supervisor → Vendedores | `DistributionStrategy` | **RESOLVIDA** — ver Decisão 6 |
| P5 | **Método de arredondamento / rateio de resto** para fechar em KG inteiro | `RoundingPolicy` | **RESOLVIDA** — ver Decisão 7 |

> **P1-P4 (Decisão 6, ver [decisions.md](./decisions.md#decisão-6--fórmula-de-cálculo-para-p1-p4-tendência--sazonalidade-sobre-12-meses)):**
> decomposição clássica multiplicativa — tendência linear (regressão simples) × índice sazonal por
> mês do calendário — sobre uma janela de **12 meses** de histórico, projetando o mês seguinte.
> Implementada em `SeasonalTrendSuggestionStrategy`/`SeasonalTrendDistributionStrategy`
> (`backend/apps/allocations/strategies.py`), com testes. **Limitação aceita:** com só 12 meses (1
> ano), cada índice sazonal vem de uma única observação por mês — não distingue padrão real de
> evento pontual naquele mês; ficaria mais robusto com 24-36 meses. **Ligação ao histórico real
> resolvida (O3, Decisão 9):** `SalesHistoryProvider` (`apps/sales_history/provider.py`) resolve
> `DistributionBaseline` para as séries que essas classes esperam, via `ExternalProductMapping`/
> `ExternalSalespersonMapping`. Falta só popular esses mapeamentos com dados reais e ligar um
> endpoint que chame o registry em modo `AUTO`. **Refinamento de P2-P4 (Decisão 6, 2026-07-21):** o
> peso de cada alvo usa sempre o histórico do **grupo inteiro**, nunca de subgrupo — quem ligar o
> endpoint `AUTO` deve chamar `target_history(..., group_id=X, subgroup_id=None)`.
>
> **P5 (Decisão 7, ver [decisions.md](./decisions.md#decisão-7--método-de-arredondamento-p5-maior-resto--hamilton)):**
> método do maior resto / Hamilton — arredonda toda proporção para baixo, depois distribui o KG
> restante, um de cada vez, para quem tem a maior fração perdida. Implementado em
> `LargestRemainderRoundingPolicy` (`backend/apps/allocations/strategies.py`), com testes; era o
> mesmo placeholder que já existia, só sem o rótulo de não-aprovado agora. O `ClosureValidator`
> continua garantindo o fechamento exato independente da fórmula de P1-P5.

## 2. Hipóteses assumidas — todas confirmadas
Assunções conservadoras para permitir avançar, todas confirmadas pelo usuário diretamente.

| # | Hipótese | Impacto se mudar |
|---|---|---|
| H1 | **CONFIRMADA** — MVP = **apenas distribuição** (sem acompanhamento de realizado vs. meta / dashboards) | Amplia escopo do MVP; seria uma frente de produto nova, não um ajuste |
| H2 | **RESOLVIDA** — histórico usado no cálculo (P1-P4) = **últimos 12 meses** (ver Decisão 6) | `--months=12` já é o default de `sync_sales_history`; `period_months=12` é o padrão esperado ao chamar as estratégias |
| H3 | **CONFIRMADA** — Administrador é responsável por **toda a gestão dentro da ferramenta** (hierarquia, pessoas, catálogo) via Django Admin | Nenhum — já é como o sistema foi construído (Decisão 4) |
| H4 | **RESOLVIDA/IMPLEMENTADA** — meta reabrível pelo nível que a distribuiu, enquanto o ciclo está aberto, sem aprovação formal | `ReopenAllocationService` (`POST /api/allocations/{id}/reopen/`), ver Decisão 8 em [decisions.md](./decisions.md) |

## 3. Open questions ao usuário real (do gate de qualidade e do design)

### O1 — Granularidade do Vendedor (RESOLVIDA)
A meta final do Vendedor é por **subgrupo** — mesma granularidade do Supervisor, só que por pessoa.
`Product` **não entra no MVP**. Nenhuma mudança de código foi necessária: `granularity` já é
genérico (`GROUP`/`SUBGROUP`/`PRODUCT`) e o modelo `Product` continua existindo (não removido —
mantido como extensão point caso a granularidade precise mudar no futuro, sem retrabalho
estrutural), só que sem uso ativo no fluxo de distribuição.

### O2 — Nota/ressalva (NÃO muda a decisão)
O usuário **declarou preferência por Python** para backend + testes, então Python **deixa de ser risco
de veto** e reforça a Decisão 1. Permanece só a ressalva de que o **motivo do descarte das
implementações anteriores** (FastAPI/Next.js e Django) é desconhecido por restrição da task — o que
**não contradiz** a preferência declarada. Nada aqui bloqueia ou reverte a stack.

### O3 — Fonte Postgres externa (RESOLVIDA)
Credenciais read-only e as duas queries reais (acumulado, carteira) foram fornecidas, conectadas
e sincronizadas para tabelas locais (`AccumulatedSale`/`ClientPortfolioSnapshot`, ver
[data-model.md](./data-model.md) e passo 6 do [roadmap.md](./roadmap.md)) — sem Fake Provider. A
janela de histórico foi confirmada (H2 → 12 meses). O mapeamento texto→entidade interna, que
faltava para ligar isso às fórmulas de P1-P4, está resolvido (Decisão 9): `ExternalProductMapping`
(já existia, agora em uso real) liga `subgroup_name` a `ProductSubgroup`/`ProductGroup`;
`ExternalSalespersonMapping` (novo, em `apps/hierarchy/models.py`) liga `salesperson_name` a
`HierarchyNode`. `SalesHistoryProvider` consome os dois para alimentar
`SeasonalTrendSuggestionStrategy`/`SeasonalTrendDistributionStrategy` diretamente. **O que resta
não é mais técnico:** os dois mapeamentos precisam ser **populados com dados reais** (curadoria
manual — Django Admin —, sem casamento automático por nome, de propósito) antes de valerem em
produção.
>
> **Estado real dos dados (2026-07-22):** `ExternalProductMapping` já está populado (101
> registros). `ExternalSalespersonMapping` está **vazio (0 registros)** — os 86 nós VENDEDOR da
> hierarquia real não têm nenhum vínculo com os `salesperson_name` do histórico sincronizado. É
> por isso que `target_history` (histórico por nó — Local/Supervisor/Vendedor, usado
> tanto em P2-P4 quanto no contexto histórico da tela de distribuição) sempre volta vazio hoje: o
> mecanismo de "subir" o histórico do Vendedor até qualquer ancestral via a hierarquia (closure
> table) já está implementado e testado — falta só o vínculo Vendedor↔`salesperson_name` para ele
> ter o que somar. Checagem de nome exato entre os 86 nós e os 99 `salesperson_name` distintos do
> histórico encontrou **74 pares idênticos** — os outros 12 nós da hierarquia e 25 nomes do
> histórico sem par exato precisam de olho humano (variação de grafia, gente que saiu, gente nova
> ainda sem nó). Curadoria pendente — não é decisão de design, é trabalho operacional único. Parte
> desses nomes sem par são **feristas** (cobrem férias, não têm nó próprio) — ver Decisão 13 em
> [decisions.md](./decisions.md#decisão-13--cobertura-de-férias-feristacoverage-redireciona-histórico-do-ferista-pro-titular-coberto-por-mês).

### O4 — Hierarquia × metas em andamento (RESOLVIDA)
Quando o Administrador desativa ou reparenta um nó da hierarquia com o ciclo aberto, a meta que
esse nó tinha recebido **volta pro nó pai** — `HierarchyChangeReassignmentService`
(`backend/apps/allocations/services.py`, Decisão 10) reabre automaticamente a alocação-pai
(reaproveitando a mecânica de cascata de H4/Decisão 8), acionado por
`HierarchyNodeAdmin.save_model()`. Quem redistribui o pai decide para onde vai cada parte,
inclusive a do nó removido/movido — o sistema não tenta adivinhar isso sozinho.

### O5 — Vínculo User ↔ Node (RESOLVIDA)
Uma pessoa pode ocupar **mais de uma posição/ramo** ao mesmo tempo — **1:N** (Decisão 10).
`User.hierarchy_nodes` (`ManyToManyField`, era `hierarchy_node` 1:1). Isolamento de escopo
(`visible_to`) e posse (`DistributeGoalService`, `ReopenAllocationService`) já unem todos os nós do
usuário. `create_user(hierarchy_node=...)` continua funcionando como atalho para o caso de um nó só.

## 4. Ressalva de rastreabilidade
Preferência por Python e prioridades de frontend foram declaradas **após** a 1ª versão do design — a
decisão de stack **também se sustenta por fit técnico independente** disso. É transparência de
histórico, **não** pendência que bloqueia. Texto completo em
[decisions.md](./decisions.md#ressalva-de-rastreabilidade-transparência).

## Resumo de impacto — situação atual
Todas as pendências de cálculo (P1-P5), hipóteses (H1-H4) e open questions (O1-O5) estão
resolvidas e implementadas. O que resta não é mais decisão de design, é trabalho operacional:

| Item | Status | O que falta, se algo |
|---|---|---|
| P1–P5 (fórmulas) | Resolvidas e implementadas (Decisões 6 e 7) | Ligação ao histórico real (O3) já existe; falta só popular os mapeamentos com dados reais |
| H1–H4 (hipóteses) | Todas confirmadas | H2 (12 meses) e H4 (Decisão 8) já implementadas |
| O1 (granularidade) | Resolvida — subgrupo | Nenhum |
| O3 (Postgres externo) | Resolvida (Decisão 9) | `ExternalProductMapping` populado (101). `ExternalSalespersonMapping` **vazio** — curadoria pendente (ver detalhe acima) |
| O4 (reatribuição) | Resolvida (Decisão 10) | Nenhum |
| O5 (User↔Node) | Resolvida — 1:N (Decisão 10) | Nenhum |

Frente que já foi aberta, fora do escopo das 5 pendências/4 hipóteses/5 open questions originais:
contexto histórico por alvo na tela de distribuição (Gerente→Local — decisão do
usuário, 2026-07-22), servido por `GET /allocations/{id}/distribution-context/`
(`DistributionContextService`, `backend/apps/allocations/services.py`). Gerente→Local
(P2) já liga a estratégia `AUTO` pra pré-preencher uma meta sugerida,
fechando exato com o pai (extensão do modo `AUTO` para GERENTE também pedida pelo usuário em
2026-07-22, ver refinamento na Decisão 6). Guia pra quando mais níveis usarem isso: P2-P4
pesam sempre pelo histórico do grupo inteiro do alvo, nunca por subgrupo
(ver refinamento de 2026-07-21 na Decisão 6 em
[decisions.md](./decisions.md#decisão-6--fórmula-de-cálculo-para-p1-p4-tendência--sazonalidade-sobre-12-meses)).
**Sem efeito prático até a curadoria de `ExternalSalespersonMapping` (ver O3 acima)** — hoje a API
responde, mas com histórico/sugestão vazios pra todo mundo.
