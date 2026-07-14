# Decisões-Chave — Metas Bello

> Entry point: [PROJECT.md](./PROJECT.md). Registro das decisões de arquitetura, alternativas
> descartadas e reversibilidade. Fonte: `docs/kickoff/02-solution-design.md`.

## Decisão 1 — Stack de backend / arquitetura (mais cara de reverter)
- **Escolha:** **Django 5.2 LTS + Django REST Framework**, como monólito modular, com camada de
  domínio explícita (services) para as regras de meta. **Linguagem Python**, alinhada à preferência
  declarada do usuário (backend + testes em Python).
- **Alternativas descartadas (todas em Python, respeitando a preferência):**
  - (B) FastAPI + SQLAlchemy + SPA React.
  - (C) Django "puro" (templates/HTMX) sem SPA.
  - *(Contraste, fora da preferência): stack TypeScript full-stack (Next.js), descartado por não
    atender à preferência de linguagem Python.)*
- **Trade-offs ligados ao brief:**
  - *Manutenção da hierarquia por Administrador (hipótese):* o **Django Admin** entrega o CRUD de
    hierarquia/pessoas/catálogo quase de graça; em (B) esse painel seria construído à mão.
  - *Fonte de histórico em Postgres externo separado:* Django tem suporte **nativo a múltiplos bancos**
    (database routers), encaixando "banco externo read-only separado" sem gambiarra; (B) exige montar
    isso na mão.
  - *5 fórmulas plugáveis:* Python é forte para lógica numérica/estratégias e é a linguagem preferida.
  - *Invariante transacional:* ambos suportam ACID — empate técnico.
  - *Contra Django:* mais opinado/pesado que FastAPI para API pura — mitigado pelo Django Admin, que
    paga esse custo devolvendo o CRUD do Administrador.
- **Reversibilidade:** **cara de reverter** (define framework, ORM, forma dos serviços e o painel
  admin). A linguagem Python em si está estabilizada pela preferência do usuário.
- **Ressalva (ver O2):** implementações anteriores (FastAPI/Next.js e Django) foram descartadas e o
  **motivo do descarte é desconhecido** por restrição da task. Isso **não contradiz** a preferência
  declarada por Python. Permanece só como transparência, não como veto pendente.

## Decisão 2 — Modelo da cascata com alocação encadeada (invariante)
- **Escolha:** cada repasse é uma `GoalAllocation` que aponta para a alocação-pai
  (`parent_allocation`). A invariante de fechamento é local a cada alocação:
  *soma das filhas diretas == quantidade do pai*.
- **Alternativas descartadas:** (B) armazenar só valores por nó sem vínculo pai-filho e recalcular
  somas por convenção; (C) event sourcing das distribuições.
- **Trade-offs:** o encadeamento pai-filho torna a invariante **verificável e auditável por linha**
  (atende "auditável") e simplifica reabertura. (B) perde rastreabilidade da origem de cada meta;
  (C) é poderoso para auditoria mas caro/complexo demais para o MVP.
- **Reversibilidade:** média — é o coração do modelo de dados; escolhido junto da Decisão 1 como parte
  do núcleo arriscado.

## Decisão 3 — Banco da aplicação: PostgreSQL
- **Escolha:** PostgreSQL para o banco da aplicação (separado do Postgres externo de histórico).
- **Alternativas descartadas:** MySQL/MariaDB; SQLite.
- **Trade-offs:** Postgres oferece CTEs recursivas (subárvore para isolamento), constraints ricas
  (CHECK para KG inteiro/`>= 0`), transações robustas e homogeneidade operacional com a fonte já
  existente. SQLite não serve para concorrência multiusuário de escrita.
- **Reversibilidade:** média (fácil se o acesso a dados ficar atrás de repositórios).

## Decisão 4 — Frontend: React SPA + Django Admin
- **Escolha:** SPA React (Vite + TypeScript) para as telas de distribuição; **Django Admin** para o
  CRUD do Administrador. Escolha do framework de frontend feita para atender às **duas prioridades
  declaradas pelo usuário**.
- **Alternativas descartadas:** Django templates + HTMX (server-rendered, mais enxuto); Next.js (SSR).
- **Trade-offs — amarrados às prioridades do usuário:**
  - *Prioridade 1 — fácil de configurar/rodar:* Vite oferece setup mínimo e rápido (dev server
    instantâneo, build simples, sem a complexidade de um framework SSR). Reaproveitar o Django Admin
    elimina construir a tela mais chata do sistema — zero setup adicional.
  - *Prioridade 2 — visualmente atraente:* a grade de distribuição precisa de feedback de soma em
    tempo real ("falta/sobra X KG"), estados interativos e edição fluida — em que uma SPA React entrega
    UI rica com naturalidade. HTMX seria mais enxuto porém com UX de edição em grade menos fluida.
- **Nota:** a **biblioteca/design system de UI ainda NÃO está decidida** e **não é registrada como
  aprovada** — será escolhida na implementação, otimizando setup fácil + aparência atraente. O que está
  fixado é o framework de renderização (React SPA via Vite/TS), não uma lib de componentes.
- **Reversibilidade:** fácil (contrato via API JSON isola o frontend do backend).

## Decisão 5 — Ponto de extensão para as fórmulas (plugável)
- **Escolha:** interfaces `DistributionStrategy` + `RoundingPolicy`, selecionadas via registry por
  nível/modo (automático vs. manual).
- **Alternativas descartadas:** hardcode das fórmulas quando definidas; regras em banco/config.
- **Trade-offs:** a interface isola as 5 pendências de cálculo de todo o resto — definir cada fórmula
  depois vira implementar uma classe, **sem retrabalho estrutural**. Hardcode violaria a diretriz do
  brief.
- **Reversibilidade:** fácil, por design.

## Decisão 6 — Fórmula de cálculo para P1-P4: tendência + sazonalidade sobre 12 meses
- **Escolha atual:** para as 4 pendências de proporção (P1 sugestão ao Gerente, P2 Regional→Local,
  P3 quebra Local→Supervisor, P4 Supervisor→Vendedor), a fórmula aprovada é uma **decomposição
  clássica multiplicativa (tendência linear × índice sazonal por mês do calendário)** sobre uma
  janela de **12 meses** de histórico, projetando o mês seguinte:
  1. **Tendência:** regressão linear simples (mínimos quadrados, método fechado — não é machine
     learning) sobre os 12 pontos, extrapolada um mês à frente.
  2. **Sazonalidade:** para cada mês do calendário presente no histórico, calcula-se a razão entre
     o valor real e o valor da reta de tendência naquele ponto; essas razões (normalizadas para
     média 1) formam o índice sazonal por mês.
  3. **Projeção:** tendência extrapolada × índice sazonal do mês seguinte.
  Em P1, o resultado é o valor absoluto sugerido por grupo. Em P2-P4, o resultado por alvo vira
  peso relativo, normalizado pelo `RoundingPolicy` (P5) para fechar exatamente com o total recebido.
  Implementado em `SeasonalTrendSuggestionStrategy` e `SeasonalTrendDistributionStrategy`
  (`backend/apps/allocations/strategies.py`), registradas como modo `AUTO` para os níveis
  REGIONAL/LOCAL/SUPERVISOR (não GERENTE, que não tem pendência de distribuição automática nomeada).
- **Limitação conhecida e aceita pelo usuário:** com apenas 12 meses (1 ano) de histórico, cada
  índice sazonal por mês do calendário vem de **uma única observação** — não distingue padrão
  sazonal real de um evento pontual naquele mês específico (uma ruptura de estoque, uma promoção).
  Ficaria mais robusto com 24-36 meses (múltiplas observações por mês), mas o usuário confirmou
  operar com a janela de 12 meses disponível mesmo assim.
- **Histórico da decisão (revisões, mantidas para rastreabilidade):**
  - *Primeira versão descartada:* média móvel ponderada linear simples sobre 6 meses (sem
    sazonalidade) — descartada porque 6 meses nunca cobre os 12 meses do calendário, então
    nenhum índice sazonal seria calculável; a fórmula só refletia tendência recente.
  - *Revisão para 12 meses + fórmula mais aprimorada:* o usuário decidiu que a janela de 6 meses
    era só um parâmetro (não muda o algoritmo de média ponderada) e pediu explicitamente um
    cálculo mais aprimorado com 12 meses, escolhendo a combinação tendência + sazonalidade entre as
    opções apresentadas (as outras eram: só ajuste sazonal; só projeção de tendência).
  - *Alternativa descartada em ambas as rodadas:* Holt-Winters/suavização exponencial tripla —
    também não é ML, mas ajusta parâmetros (alpha/beta/gamma) por otimização, o que é menos
    transparente/auditável do que a decomposição clássica com componentes explícitos e inspecionáveis.
- **Trade-offs:** a decomposição clássica é auditável componente a componente (dá pra mostrar a um
  Gerente "a tendência projeta X, o índice sazonal de dezembro é Y% acima da média, então a
  sugestão é Z") e reage tanto a tendência recente quanto a padrão sazonal — mais completa que a
  versão anterior (só tendência). Em troca, tem mais camadas de cálculo para auditar e a
  sazonalidade é frágil com só 1 ano de dado (ver limitação acima).
- **Bloqueio conhecido:** as classes recebem a série histórica **já resolvida** por
  `ProductGroup.id`/`HierarchyNode.id` via parâmetro (`MonthlyQuantity` com `ano`/`mes` explícitos)
  — não fazem o casamento entre texto do ERP (`subgroup_name`, `salesperson_name`/`nk_vendedor`) e
  as entidades internas. Isso depende de O3/O5 (ver [open-questions.md](./open-questions.md)) e não
  foi inventado aqui.
- **Workflow associado (não uma decisão de arquitetura nova, só confirmação):** o resultado de
  P1-P4 é sempre uma **sugestão revisável** — o usuário do nível aprova como está ou corrige valores
  específicos antes de confirmar; nenhuma alocação é persistida sem esse toque humano, e o mesmo
  endpoint/serviço de `distribute` já existente cobre os dois casos (manual e auto).
- **Reversibilidade:** fácil — troca de `RoundingPolicy`/`DistributionStrategy` por design (Decisão 5).

## Decisão 7 — Método de arredondamento (P5): maior resto / Hamilton
- **Escolha:** para fechar proporções fracionárias em KG inteiro batendo exato com o total recebido,
  a fórmula aprovada é o **método do maior resto (Hamilton)**: arredonda toda proporção para baixo,
  calcula quanto sobrou (`total_kg - soma dos arredondamentos`), e distribui esse resto, 1 kg de
  cada vez, para quem tem a maior fração perdida no arredondamento — até fechar exato. Implementado
  em `LargestRemainderRoundingPolicy` (`backend/apps/allocations/strategies.py`).
- **Contexto:** era o mesmo placeholder que já existia desde o início do projeto
  (`UnapprovedLargestRemainderRoundingPolicy`), plugado só para destravar dev enquanto P5 não tinha
  aprovação. O usuário aprovou exatamente esse método ao escolher entre as opções apresentadas —
  a mudança foi só remover o rótulo de não-aprovado, sem alterar o algoritmo (já testado desde antes).
- **Alternativas descartadas:**
  - *Método dos divisores (D'Hondt):* atribui uma unidade de cada vez a quem tem o maior quociente
    (`valor / (unidades já dadas + 1)`), repetindo até fechar. Evita alguns paradoxos teóricos do
    maior resto, mas é mais complexo de explicar a um Gerente/Coordenador e exigiria implementação
    nova.
  - *Maior alvo absorve a diferença:* todo mundo arredonda, e quem tem a maior quantidade absorve
    sozinho toda a sobra/falta. Mais simples ainda, mas concentra sempre no mesmo alvo a variação de
    arredondamento, mês após mês — descartado por ser potencialmente percebido como injusto.
- **Trade-offs:** maior resto é auditável linha a linha ("faltava fechar 3 kg, foram para os 3 alvos
  com maior fração perdida") e é um método clássico e bem entendido (usado em apuração de cadeiras
  parlamentares). Em troca, tem uma limitação teórica conhecida (paradoxo de Alabama: aumentar o
  total pode, em casos raros, reduzir a parcela de um alvo específico) — aceitável dado o volume e
  a escala pequena de alvos por repasse neste produto.
- **Reversibilidade:** fácil — troca de `RoundingPolicy` por design (Decisão 5); `DistributeGoalService`
  e o `ClosureValidator` não mudam com a troca.

## Decisão 8 — Mecanismo de reabertura em cascata (H4): apagar + registrar no AuditLogEntry
- **Escolha:** ao reabrir uma alocação já distribuída, a sub-árvore de filhas invalidada é
  **apagada de verdade** (hard delete, da folha mais profunda para cima, respeitando
  `on_delete=PROTECT` em `parent_allocation`), e o evento (o que foi invalidado, quem reabriu,
  quando) é registrado no `AuditLogEntry` já existente no projeto — que passou a cobrir
  `GoalAllocation` além de `HierarchyNode`/catálogo, usando o mesmo `GenericForeignKey` (ação nova:
  `REABERTURA`). Implementado em `ReopenAllocationService`
  (`backend/apps/allocations/services.py`), exposto via `POST /api/allocations/{id}/reopen/`. Depois
  de reaberta (`distributed == False`), a mesma `DistributeGoalService.distribute()` — **sem
  nenhuma mudança nela** — refaz o repasse normalmente.
- **Alternativas descartadas:**
  - *Hard delete sem registro:* mais simples ainda (zero mudança em `audit`), mas perde qualquer
    rastro de que uma reabertura aconteceu — não combina com a ênfase do produto em auditabilidade
    (ver Invariante de auditabilidade em [architecture.md](./architecture.md)).
  - *Soft delete (marcar como obsoleta):* manteria as linhas antigas no banco (histórico mais
    completo, dá pra reconstruir a alocação inteira como estava antes), mas exigiria um campo novo
    em `GoalAllocation` (migração) e atualizar todas as queries que já filtram esse model
    (`visible_to`, `CycleCompletenessChecker.stuck_allocations`, `GoalAllocationViewSet`) para
    excluir os registros obsoletos — custo maior de mudança para um ganho de histórico que o
    `AuditLogEntry` já cobre (guarda `id`, `owner_node_id` e `quantity_kg` de cada filha invalidada
    em `changes`, suficiente para reconstruir "o que existia antes").
- **Escopo do mecanismo:** cobre só *reabrir e redistribuir* um total já existente, pelo mesmo nível
  que distribuiu (checagem de posse igual à de `DistributeGoalService`) e só com o ciclo `ABERTO`.
  Não decide a política de O4 (mudança de hierarquia com ciclo aberto) — ver
  [open-questions.md](./open-questions.md).
- **Reversibilidade:** média — trocar para soft delete depois exigiria migração + atualizar as
  queries citadas acima, mas o contrato público (`ReopenAllocationService.reopen()`,
  `POST /reopen/`) não mudaria.

## Decisão 9 — Mapeamento texto→entidade para o histórico real (O3): curadoria manual, sem casamento automático por nome
- **Escolha:** `DistributionBaseline` só tem texto solto do ERP (`subgroup_name`,
  `salesperson_name`, sem código estável) — para ligar isso às fórmulas de P1-P4
  (`SeasonalTrendSuggestionStrategy`/`SeasonalTrendDistributionStrategy`, Decisão 6), dois
  mapeamentos explícitos, **populados manualmente** (Django Admin), sem qualquer tentativa de
  casar nomes automaticamente:
  - **`ExternalProductMapping`** (já existia em `apps/catalog/models.py`, sem uso real até agora):
    `subgroup_name` → `ProductSubgroup` (o grupo vem de graça via `ProductSubgroup.group`).
  - **`ExternalSalespersonMapping`** (novo, `apps/hierarchy/models.py`): `salesperson_name` →
    `HierarchyNode`.
  - **`SalesHistoryProvider`** (`apps/sales_history/provider.py`): usa os dois mapeamentos para
    resolver `DistributionBaseline` em séries `MonthlyQuantity` — `group_history()` soma todos os
    subgrupos mapeados de um grupo (P1); `target_history()` soma o histórico de todo Vendedor
    descendente de um nó (via `ScopeResolver`/`HierarchyClosure` — cobre P2 Regional→Local, P3
    Local→Supervisor e P4 Supervisor→Vendedor, cada um agregando na granularidade certa), com
    filtro opcional por grupo/subgrupo. Meses sem dado entram com quantidade zero — as estratégias
    exigem série mensal consecutiva, sem buracos.
- **Alternativa descartada:** casamento automático por nome (ex.: normalizar e comparar
  `salesperson_name` contra `HierarchyNode.nome`) — mais rápido de popular, mas nome livre não é
  identificador confiável (variação de formatação, homônimos, nome mudando ao longo do tempo);
  atribuir histórico de vendas ao vendedor errado seria pior do que não ter o histórico. Descartado
  por ser exatamente o tipo de heurística inventada que a regra de ouro do CLAUDE.md proíbe.
- **Trade-offs:** curadoria manual tem custo operacional (alguém precisa popular e manter os dois
  mapeamentos conforme o ERP muda), mas é auditável e não arrisca atribuição errada. Vendedores ou
  subgrupos sem mapeamento simplesmente não contribuem para o histórico (tratados como peso zero),
  não travam o cálculo nem geram erro.
- **Reversibilidade:** fácil — os mapeamentos são tabelas independentes; trocar por uma fonte de
  identificação melhor (ex.: se o ERP passar a expor código estável) não muda o contrato do
  `SalesHistoryProvider` nem das estratégias.

## Decisão 10 — Reatribuição de meta em mudança de hierarquia (O1, O4, O5)

**O1 — Granularidade do Vendedor: subgrupo.** A meta final do Vendedor é distribuída por subgrupo
(mesma granularidade do Supervisor, só que por pessoa) — não por produto individual. `Product`
não entra no MVP. Nenhuma mudança de código: `granularity` já era genérico e o modelo `Product`
permanece existindo, sem uso ativo, como ponto de extensão caso a decisão mude no futuro.

**O4 — Política de reatribuição: meta volta pro nó pai.**
- **Escolha:** quando um nó da hierarquia é **desativado** (`ativo` vira `False`) ou **reparentado**
  (`parent` muda) enquanto tem meta em ciclo `ABERTO`, a alocação **pai** (quem tinha distribuído
  para esse nó) é reaberta automaticamente — a mesma mecânica de H4 (Decisão 8), só que disparada
  pela mudança de hierarquia em vez de por pedido voluntário do dono. Implementado em
  `HierarchyChangeReassignmentService.reassign_open_cycle_allocations()`
  (`backend/apps/allocations/services.py`), acionado por `HierarchyNodeAdmin.save_model()`
  (`backend/apps/hierarchy/admin.py`) — único lugar onde a hierarquia é editada (Decisão 4).
  `ReopenAllocationService` ganhou um segundo ponto de entrada,
  `reopen_for_hierarchy_change()`, que reaproveita toda a lógica de cascata/audit já existente
  mas **pula a checagem de posse** (`reopen()` original exige que quem chama seja o dono da
  alocação — aqui é o Administrador mudando a hierarquia, não o dono pedindo).
- **Escopo real da reabertura:** como `distributed` é tudo-ou-nada por alocação, reabrir a
  alocação-pai invalida em cascata **toda** a sub-árvore abaixo dela — inclusive irmãos do nó
  afetado que não mudaram. Não dá pra "devolver" só a fatia do nó afetado sem redistribuir o total
  de novo; quem redistribui (o dono do nó pai) decide para onde vai cada parte, inclusive a do nó
  removido/movido.
- **Alternativas descartadas:**
  - *Reatribuir a um substituto indicado:* exigiria que quem muda a hierarquia já soubesse, no
    mesmo ato, quem herda a meta — acopla uma decisão de negócio (quem substitui) a uma operação de
    cadastro; descartado em favor de deixar essa escolha para quem redistribui depois.
  - *Zerar a meta do nó removido:* perderia KG da meta global sem motivo — violaria o espírito da
    invariante de fechamento (nada deveria desaparecer sem ser redistribuído).
  - *Bloquear mudança de hierarquia com ciclo aberto:* mais simples (nenhuma política de
    reatribuição seria necessária), mas o usuário preferiu permitir a mudança e resolver via
    reatribuição ao pai.
- **Gatilho técnico:** `HierarchyNodeAdmin.save_model()` compara o estado anterior do nó (buscado
  do banco antes de salvar) com o novo, e dispara a reatribuição só quando `ativo` vai de
  `True`→`False` ou `parent_id` muda — criação de nó novo ou edição de outros campos (nome, etc.)
  não dispara nada.

**O5 — Cardinalidade User↔Node: 1:N.**
- **Escolha:** uma pessoa pode ocupar mais de uma posição/ramo ao mesmo tempo. `User.hierarchy_node`
  (antes `OneToOneField`) virou `User.hierarchy_nodes` (`ManyToManyField` para `HierarchyNode`,
  `related_name="users"`). Isolamento de escopo (`HierarchyNode.objects.visible_to`,
  `GoalAllocation.objects.visible_to`) e checagens de posse (`DistributeGoalService`,
  `ReopenAllocationService`) passaram a **unir** os nós do usuário em vez de comparar contra um
  único `hierarchy_node_id`. `ScopeResolver.descendant_ids()` (`apps/hierarchy/services.py`) foi
  generalizado para aceitar um id **ou** uma lista de ids, mantendo compatibilidade com quem já
  chamava com um único id (ex.: `SalesHistoryProvider`).
- **Conveniência de criação:** `UserManager.create_user()`/`create_superuser()` (custom, em
  `apps/accounts/models.py`) aceitam `hierarchy_node=` (singular) como atalho pro caso comum de um
  usuário com um nó só — internamente vira `user.hierarchy_nodes.add(node)`. Isso evitou reescrever
  as ~30 chamadas de teste existentes que já usavam esse padrão; a atribuição de mais de um nó usa
  `user.hierarchy_nodes.add(node_a, node_b)` diretamente (testado em `MultiNodeUserScopeTests`,
  `apps/allocations/test_isolation.py`).
- **Migração:** `accounts.0002_...` remove o campo antigo e adiciona o M2M — sem migração de dados
  (o vínculo 1:1 existente, se houvesse, seria perdido). Aceitável: banco de desenvolvimento local,
  sem dado de produção ainda.
- **Alternativa descartada:** manter `hierarchy_node` (1:1) como "nó principal" ao lado de um novo
  `hierarchy_nodes` (M2M) para não quebrar nada — descartado por duplicar a fonte de verdade
  (qual dos dois vale?) e ser exatamente o tipo de shim de compatibilidade que o CLAUDE.md pede pra
  evitar quando dá pra só mudar o código.
- **Trade-off aceito:** com 1:N, uma alocação distribuída por "Fulano" não identifica mais
  sozinha *qual* das posições de Fulano a criou — só que ele tinha posse de alguma delas no
  momento. Não é um problema hoje (nenhuma tela/relatório depende disso), mas vale revisitar se
  isso passar a importar (ex.: auditoria por posição, não só por pessoa).
- **Reversibilidade:** média — voltar pra 1:1 exigiria decidir qual nó "vence" para usuários que
  hoje tenham mais de um.

---

### Ressalva de rastreabilidade (transparência)
A preferência do usuário por **Python** (backend + testes) e as **prioridades de frontend** (setup
fácil + UI atraente) foram declaradas **após** a 1ª versão do design. A decisão de stack **também se
sustenta por fit técnico independente** dessas preferências — elas confirmam e reforçam a Decisão 1,
não a originaram. Registrado para honestidade de histórico, não como pendência.

Open questions relacionadas (O1–O5) e pendências de cálculo: ver [open-questions.md](./open-questions.md).
