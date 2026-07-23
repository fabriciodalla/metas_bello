# Modelo de Dados Conceitual — Metas Bello

> Entry point: [PROJECT.md](./PROJECT.md). Nomenclatura **nova**, sem herança de versões anteriores.
> Conceitual: nomes de campos são um guia para quem vai codar, não um schema final travado.

## Entidades principais

### User
Credenciais próprias (usuário/senha, hash), `is_admin`, e vínculo **1:N** (`hierarchy_nodes`,
`ManyToManyField` — O5, Decisão 10: uma pessoa pode ocupar mais de uma posição/ramo ao mesmo
tempo) a `HierarchyNode`. O vínculo é o que ancora escopo e nível do usuário — isolamento de
escopo e checagens de posse unem todos os nós do usuário. `create_user(hierarchy_node=...)`
continua disponível como atalho de criação para o caso comum de um nó só.

### HierarchyNode
Nó/posição da árvore organizacional.
- `id`
- `level` — enum: `GERENTE`, `REGIONAL`, `LOCAL`, `SUPERVISOR`, `VENDEDOR`
- `parent_id` — self-FK
- `nome/pessoa`
- `ativo`
- Um único `GERENTE` raiz.

### HierarchyClosure
Closure table (`ancestor_id`, `descendant_id`, `depth`) para consultas O(1) de "todos os descendentes
de X" (isolamento de escopo) sem recursão em runtime. Alternativa equivalente: CTE recursiva; a closure
table é preferida por ser consulta frequente de visibilidade.

### ExternalSalespersonMapping
Liga o nome livre do vendedor no ERP (`salesperson_name`, usado em `DistributionBaseline`/
`ClientPortfolioSnapshot`) ao `HierarchyNode` (nível VENDEDOR) correspondente — O3/O5, Decisão 9.
- `external_name` (`unique`), `hierarchy_node` (FK).
- Populado **manualmente** via Django Admin, de propósito sem casamento automático por nome (nome
  livre pode divergir em grafia, ter homônimo, ou mudar ao longo do tempo).

### FeristaCoverage
Cobertura de férias — Decisão 13. Um ferista **não tem nó próprio na hierarquia**: só liga o nome
livre dele no ERP (`external_name`) ao `HierarchyNode` VENDEDOR titular que ele cobriu
(`covered_node`), num mês específico (`ano`, `mes`).
- `UniqueConstraint(external_name, ano, mes)` — um ferista só cobre uma pessoa por mês.
  `covered_node.level` precisa ser VENDEDOR.
- Consumido por `SalesHistoryProvider.target_history`: redireciona o volume vendido pelo ferista,
  só no(s) mês(es) cobertos, pro histórico do titular — fora disso, o nome não conta pra ninguém.
- Gestão pela função "Feristas" do Administrador (`frontend/src/pages/admin/FeristaManager.tsx`),
  via `FeristaCoverageViewSet` (mesmo padrão de CRUD de hierarquia/catálogo); também no Django Admin.

### ProductGroup
Grupo de produto: **Embutidos, Frangos, Pescados, Revenda**.

### ProductSubgroup
Subgrupo, FK para `ProductGroup`.

### Product (opcional / condicional)
Produto individual, FK para subgrupo. Necessário **apenas se** a granularidade do Vendedor for produto
individual — ver **O1** em [open-questions.md](./open-questions.md).

### ExternalProductMapping
Mapeia identificadores da fonte Postgres externa (código de grupo/subgrupo/produto lá) para
`ProductGroup`/`ProductSubgroup` internos. Preenchido quando **O3** for respondida.

### Cycle
Ciclo mensal.
- `ano`, `mes`
- `status` — `ABERTO` / `FECHADO`
- unicidade por (`ano`, `mes`)
- O estado `ABERTO` habilita edição/reabertura (hipótese H4). A transição `ABERTO → FECHADO` é
  **guardada pela checagem de completude** (ver [architecture.md](./architecture.md#invariante-2--completude-de-ciclo-end-to-end-100-chega-ao-vendedor)).

### GoalAllocation
O repasse de meta — entidade central.
- `cycle_id`
- `owner_node_id` — nó que **recebe/possui** esta parcela de meta
- `parent_allocation_id` — alocação da qual esta foi quebrada (`null` na raiz = metas globais do
  Gerente por grupo)
- `granularity` — enum: `GROUP`, `SUBGROUP`, `PRODUCT`
- `group_id` / `subgroup_id` / `product_id` — apenas o campo compatível com a granularidade é
  preenchido (constraint de consistência)
- `quantity_kg` — inteiro, CHECK `>= 0`
- `distributed` (bool) — se este nó já repassou esta parcela para baixo. É a base do gate de
  completude: uma alocação de nível não-VENDEDOR com `distributed == false` é uma parcela "presa".
- metadados de auditoria (`criado_por`, timestamps)

### AuditLogEntry
Histórico de mudanças em cadastros geridos pelo Administrador — cobre criação, inativação/
reativação e mudança de vínculo (ex.: nó trocando de coordenação/supervisão). Uma única tabela
cobre tanto `HierarchyNode` quanto o catálogo (`ProductGroup`/`ProductSubgroup`/`Product`), via
referência genérica, em vez de uma tabela de histórico por entidade.
- `content_type_id` / `object_id` — referência genérica (Django ContentType) ao registro alterado.
- `action` — enum: `CRIACAO`, `ATUALIZACAO`, `INATIVACAO`, `REATIVACAO`.
- `changes` — snapshot dos campos alterados (de/para).
- `changed_by_id` — usuário Administrador responsável pela mudança.
- `changed_at` — timestamp.

Nesta etapa só a tabela existe. Popular o log automaticamente (signals/serviço) e a tela de
gestão dedicada para hierarquia/catálogo/histórico ficam para uma próxima etapa — ver
[roadmap.md](./roadmap.md).

### AccumulatedSale
Espelho local (no banco da aplicação, não consultado ao vivo) do resultado da query de
acumulado de vendas do Postgres externo (`stage_comercial.st_venda_dinamica` + tabelas de
apoio) — ver Anticorruption Layer em [architecture.md](./architecture.md). Uma linha por
supervisor/vendedor/cliente/subgrupo/data (mesmo agrupamento da query original — o mesmo
vendedor pode aparecer com `nk_supervisor` diferente conforme a empresa da venda).
- `nk_supervisor` / `nk_vendedor` — códigos externos (natural key do ERP), guardados como texto
  simples; **sem** mapeamento para `HierarchyNode` nesta etapa.
- `client_code`, `cnpj`, `client_name` — identificação do cliente.
- `sale_date`, `subgroup_name`, `total_quantity`, `total_value`.
- Repovoada por `SalesHistorySyncService`/`sync_sales_history` (management command), que apaga
  e reinsere por janela de data — sem constraint de unicidade de negócio, a idempotência vem do
  apagar-e-reinserir, não de upsert por chave.

### ClientPortfolioSnapshot
Espelho local da carteira (cliente → vendedor/supervisor atual) — **foto do momento**, sem
dimensão de data. Cada sincronização substitui a tabela inteira (`client_code` é `unique`).

### DistributionBaseline
A base de cálculo para a distribuição de metas (P1–P4) — não um espelho do Postgres externo, e
sim derivada localmente de `AccumulatedSale` + `ClientPortfolioSnapshot`, unidas pelo
`client_code` (clifor, comum às duas). Reatribui cada venda ao vendedor **atual** da carteira do
cliente, não a quem historicamente vendeu — não importa quem vendeu, importa quanto o cliente
comprou, e esse total conta para quem hoje é responsável por ele (mesmo que nunca tenha vendido
pra esse cliente pessoalmente). Clientes do acumulado sem entrada na carteira atual **não ficam
de fora** (Decisão 12): geram uma linha própria com `salesperson_name=NULL`, que conta na soma por
grupo usada na sugestão de meta do Gerente (P1, `SalesHistoryProvider.group_history`), mas não em
nenhuma soma por vendedor específico (P2-P4, `SalesHistoryProvider.target_history`).
- `ano`, `mes`, `salesperson_name` (nome, não código — a carteira só expõe nome; **nullable**,
  `NULL` = sem vendedor vigente na carteira), `subgroup_name`, `total_quantity` (soma do
  agrupamento, sempre **KG inteiro** — `< 0,5` desce, `>= 0,5` sobe, `ROUND_HALF_UP`).
- `UniqueConstraint` em (`ano`, `mes`, `salesperson_name`, `subgroup_name`).
- Reconstruída inteira por `DistributionBaselineService.rebuild()` — chamada automaticamente ao
  final de `sync_sales_history`, ou isoladamente via `rebuild_distribution_baseline` (sem tocar o
  Postgres externo).

As três alimentam as fórmulas ainda pendentes (P1–P4, ver [open-questions.md](./open-questions.md))
quando forem definidas; nenhuma estratégia consome isso automaticamente ainda.

## Relações-chave
- A árvore de metas espelha a árvore hierárquica **por parcela**: a meta global do Gerente por grupo é
  raiz; cada distribuição cria filhas apontando ao pai (`parent_allocation_id`).
- A **mudança de granularidade** acontece nas quebras: uma alocação `GROUP` (recebida pelo Coordenador
  Local) tem filhas `SUBGROUP` cujos subgrupos pertencem àquele grupo.

## Granularidade por nível (cascata)
| Nível | Recebe | Distribui em | Granularidade |
|---|---|---|---|
| Gerente | — (define global) | Regionais | GROUP |
| Coordenador Regional | GROUP | Locais | GROUP |
| Coordenador Local | GROUP | Supervisores | SUBGROUP (quebra grupo→subgrupo) |
| Supervisor | SUBGROUP | Vendedores | SUBGROUP |
| Vendedor | SUBGROUP **ou** PRODUCT (ver O1) | — (folha) | SUBGROUP ou PRODUCT |

## Invariantes que tocam o modelo
- **KG inteiro `>= 0`:** garantido por tipo inteiro + CHECK no schema.
- **Fechamento local:** `soma(filhas.quantity_kg) == pai.quantity_kg`, garantido na transação do
  `DistributeGoalService` (não é uma constraint estática de linha).
- **Consistência de granularidade:** só o campo de produto compatível com `granularity` é preenchido.
- **Completude:** nenhuma alocação de nível intermediário com `distributed == false` num ciclo FECHADO.

Detalhe das invariantes em [architecture.md](./architecture.md).
