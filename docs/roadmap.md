# Roadmap — Metas Levo

> Entry point: [PROJECT.md](./PROJECT.md). O que está fora de escopo nesta versão e por onde começar a
> codificar.

## Migração de código concluída — remoção do nível Coordenador Regional (Decisão 14)
O código já reflete a hierarquia de 4 níveis (**Gerente → Coordenador Local → Supervisor →
Vendedor**, ver [Decisão 14](./decisions.md#decisão-14--remoção-do-nível-coordenador-regional-hierarquia-passa-de-5-para-4-níveis)):
`HierarchyNode.level` (enum sem `REGIONAL` + migração `hierarchy/0004_remove_regional_level.py`),
`strategies.py` (registry `AUTO`/`MANUAL` para GERENTE/LOCAL/SUPERVISOR), `services.py`
(`VendedorAllocationRow.gerente_nome`, era `regional_nome`), `seed_demo.py`, serializers/views e
toda a suíte de testes backend/frontend foram atualizados — banco de dev tratado como resetável
(sem dado real de nó Regional a migrar, confirmado com o usuário).

**Ainda não rodado neste ambiente (Docker indisponível durante a mudança) — rodar antes de dar a
tarefa como concluída:**
- `docker compose exec backend python manage.py makemigrations --check` (confirmar que
  `0004_remove_regional_level.py` cobre o `AlterField` sem gerar migração adicional) e
  `python manage.py migrate`.
- `docker compose exec backend black . && ruff check --fix .`
- `docker compose exec backend python manage.py check`
- `docker compose exec backend pytest`
- `docker compose exec frontend npm run build` (`tsc -b && vite build`) + teste manual no
  navegador (login, tela de distribuição Gerente→Local, Distribuir Produtos, Meta Supervisor).

## Fora de escopo nesta versão
- **Acompanhamento de realizado vs. meta** e dashboards de performance (hipótese H1 — o MVP só
  distribui).
- **Escrita/alteração no ERP ou no Postgres fonte** (somente leitura).
- **SSO corporativo** (login próprio usuário/senha, sem SSO).
- **Fluxo de aprovação formal de metas** (H4 permite reabrir sem aprovação no MVP — `ReopenAllocationService`
  já implementado, ver Decisão 8 em [decisions.md](./decisions.md)).
- **Escolha da biblioteca/design system de UI** do frontend (decidida na implementação).

## Próximos passos de codificação
Ordem recomendada, começando pelo **núcleo de backend em Python**. Os passos 2 a 5 foram construídos
sem depender das fórmulas de proporção (`ClosureValidator`, `CycleCompletenessChecker`, isolamento de
escopo e os pontos de extensão plugáveis) — as fórmulas de P1–P5 **já foram todas definidas e
implementadas depois** (ver [decisions.md](./decisions.md), Decisões 6 e 7), sem retrabalho
estrutural nesses passos. O3 (fonte Postgres externa) **foi respondida**: credenciais read-only e as
duas queries reais (acumulado, carteira) já foram fornecidas, validadas e sincronizadas (passo 6
concluído nessa parte).

1. **Fundação Django + modelo de dados.** Projeto Django 5.2 + DRF; models e migrações para
   `HierarchyNode`, `HierarchyClosure`, `ProductGroup`/`ProductSubgroup`, `Cycle`, `GoalAllocation`,
   `User`, `AuditLogEntry` (histórico de mudanças em hierarquia/catálogo). CHECK de KG inteiro
   `>= 0`. Ver [data-model.md](./data-model.md).
2. **Invariante de fechamento.** `ClosureValidator` + `DistributeGoalService` transacional (ACID). É a
   regra rígida do brief — priorizar e cobrir com testes.
3. **Completude end-to-end.** `CycleCompletenessChecker` + `CloseCycleService` (gate que recusa fechar
   ciclo com parcela presa em nível intermediário).
4. **Isolamento de escopo.** Manager/repositório base filtrando por subárvore (`HierarchyClosure`) +
   checagem object-level na escrita. **Suíte de testes de isolamento** como critério de aceite.
5. **Pontos de extensão plugáveis — CONCLUÍDO.** Interfaces `DistributionStrategy`,
   `SuggestionStrategy`, `RoundingPolicy` + registry. Inicialmente só com um `RoundingPolicy`
   placeholder marcado como não-aprovado para destravar o fluxo; **todas as 5 pendências (P1-P5)
   já têm fórmula aprovada e implementada** (ver Decisões 6 e 7 em [decisions.md](./decisions.md)).
6. **Anticorruption layer — CONCLUÍDO.** `SalesHistorySyncService` + `sync_sales_history`
   (management command) rodam as duas queries reais (acumulado, carteira) contra o Postgres
   externo (conexão dedicada read-only, alias `sales_history`) e gravam em
   `AccumulatedSale`/`ClientPortfolioSnapshot`, no banco da aplicação — **sem Fake Provider**.
   Janela confirmada e já em produção: **12 meses** (default `--months=12`, H2 resolvida — ver
   Decisão 6). `DistributionBaselineService.rebuild()` (também disparado ao final do sync, ou
   isolado via `rebuild_distribution_baseline`) deriva `DistributionBaseline`: reatribui o
   acumulado ao vendedor **atual** da carteira (join por `client_code`/clifor) e agrupa por
   ano/mês/vendedor/subgrupo — a base de fato que P1–P4 consomem. Validado contra dados reais
   (116 mil linhas de acumulado → 7,4 mil linhas de base). **P1-P4 já têm fórmula aprovada e
   implementada** (`SeasonalTrendSuggestionStrategy`/`SeasonalTrendDistributionStrategy` —
   decomposição tendência linear + índice sazonal por mês sobre 12 meses — ver Decisão 6). A porta
   `SalesHistoryProvider` (`apps/sales_history/provider.py`) faz o join entre `DistributionBaseline`
   (texto do ERP) e `ProductGroup`/`HierarchyNode` internos, via `ExternalProductMapping`/
   `ExternalSalespersonMapping` (O3, ver Decisão 9 em [decisions.md](./decisions.md)) — falta só
   popular esses dois mapeamentos com dados reais (curadoria manual, sem casamento automático por
   nome) antes de valer em produção.
7. **API DRF + Django Admin — CONCLUÍDO.** Sessão autenticada (`/api/auth/csrf`, `login`, `logout`,
   `me`); `/api/hierarchy/nodes/` (escopo via `visible_to`); `/api/cycles/` +
   `completeness`/`close`; `/api/allocations/` + `distribute` + `reopen` (H4, `ReopenAllocationService`)
   — todas as escritas passam pelos serviços de domínio já existentes (`DistributeGoalService`,
   `CloseCycleService`, `ReopenAllocationService`), nunca persistência direta na view. Django Admin
   segue sendo o CRUD de hierarquia/catálogo/histórico (Decisão 4) — a API não duplica isso. Detalhe
   dos endpoints em [architecture.md](./architecture.md#api-drf-sessão-autenticada).
8. **Frontend React (Vite/TS) — CONCLUÍDO.** SPA em `frontend/` (Vite dev server, proxy `/api` →
   backend, sem CORS/porta cruzada). Duas telas: (a) grade de distribuição — lista alocações
   pendentes/distribuídas do usuário, formulário multi-linha com feedback de soma em tempo real
   ("faltam/sobram X kg"/"fecha exatamente"), cobre inclusive a quebra grupo→subgrupo
   (Local→Supervisor, com seletor de subgrupo); (b) **tela de gestão do Administrador** —
   visão de leitura da hierarquia (árvore) e do catálogo, com link para o Django Admin para
   edição de fato (CRUD continua lá, Decisão 4 — não duplicado na SPA). Testado ponta a ponta
   num navegador real (Playwright): login, distribuição simples, quebra grupo→subgrupo com duas
   linhas de subgrupos diferentes, e a tela do Administrador — sem erros.
   `manage.py seed_demo` povoa um cenário mínimo para explorar isso localmente.

## Handoff recomendado
- **Núcleo/backend:** `python-developer` — passos 1 a 6 (a stack aponta para Python).
- **Frontend:** passos 7–8 concluídos.

## Critérios de aceite herdados do brief
- [ ] Meta global 100% distribuída até os vendedores, sem sobra nem falta, validado em cada repasse.
- [ ] Todos os valores de meta inteiros em KG.
- [ ] Isolamento de escopo verificável (usuário só vê/distribui no próprio ramo).
- [ ] Sugestão automática por grupo baseada em histórico (fórmula aprovada — Decisão 6 — e ligada ao
      dado real via `SalesHistoryProvider` — Decisão 9 —; falta popular os mapeamentos com dados
      reais e ligar um endpoint/UI que use isso).
- [ ] Gerente escolhe distribuição automática ou manual ao repassar para o Coordenador Local; ambas respeitam o fechamento.
- [ ] Coordenador Local quebra grupo em subgrupo respeitando o total recebido.
- [ ] Supervisor distribui por subgrupo entre vendedores respeitando o total.
- [ ] Login próprio (usuário/senha) associa cada usuário ao seu nível/ramo.
- [ ] Ciclos de meta são mensais.
