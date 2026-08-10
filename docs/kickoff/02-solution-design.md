# Solution Design — Distribuição de Metas Comerciais (Bello Alimentos)

> Fonte de verdade: `docs/kickoff/01-problem-brief.md`. Projeto construído do zero;
> nenhuma decisão, nomenclatura ou modelo de versões anteriores foi reutilizado.
> Data: 2026-07-13.

## Resumo da Solução
Aplicativo web interno (monólito modular) que modela a cascata de metas mensais em
KG inteiro do Gerente até o Vendedor, com uma **invariante de fechamento exato**
garantida pela arquitetura (validação transacional independente da fórmula) e um
**ponto de extensão plugável** para as cinco fórmulas de cálculo ainda em aberto.
O isolamento de escopo por ramo é imposto na camada de dados, e o histórico do
Postgres externo é consumido por um **adaptador anticorrupção** que isola o schema
desconhecido do resto do sistema.

## Preferências Declaradas do Usuário

> Preferências informadas pelo usuário **após** a primeira versão deste design.
> São fortes, mas **ainda não 100% travadas**: devem ser respeitadas salvo razão
> técnica forte em contrário. Nenhuma é registrada aqui como "decisão aprovada com
> detalhamento técnico" além do que foi efetivamente dito.

- **Backend + suíte de testes em Python (preferência de linguagem).** O usuário
  declarou que a **linguagem** do backend e dos testes deve ser Python. A escolha do
  **framework** Python (ex.: Django ou FastAPI) permanece **decisão técnica minha**
  dentro dessa restrição. Isso **reforça a Decisão 1** (Django/Python), que já havia
  sido recomendada por fit — a preferência do usuário apenas confirma a linguagem,
  sem o usuário fixar o framework.
- **Frontend: sem framework específico preferido, mas com duas prioridades claras.**
  (1) **Fácil de configurar/rodar** — baixo esforço de setup para um time interno
  pequeno; (2) **Visualmente atraente/chamativo** — boa UI/UX, não uma interface
  crua/só funcional. A escolha do framework de frontend permanece **decisão técnica
  minha**, otimizada para essas duas prioridades. Ver Decisão 4.

## Arquitetura

Estilo: **monólito modular** (não microserviços). Justificativa ligada aos
requisitos: base de usuários pequena e conhecida (1 Gerente, 2 Regionais, 9 Locais,
supervisores/vendedores — dezenas a poucas centenas), forte necessidade de
**consistência transacional** (o fechamento exato é uma invariante ACID por
natureza) e time de manutenção presumivelmente enxuto. Microserviços introduziriam
consistência distribuída sem nenhum benefício exigido pelo brief.

```
┌──────────────────────────────────────────────────────────────────┐
│                        Navegador (usuário interno)                 │
│  UI de distribuição (grade com validação de soma em tempo real)    │
└───────────────┬────────────────────────────────────────────────────┘
                │ HTTPS / API JSON (sessão autenticada)
┌───────────────▼────────────────────────────────────────────────────┐
│                     APLICAÇÃO (monólito modular)                    │
│                                                                    │
│  [Auth/Sessão]  [Autorização de escopo por ramo]                   │
│                                                                    │
│  Módulo Hierarquia     Módulo Catálogo      Módulo Ciclos          │
│  (nós/pessoas)         (grupo/subgrupo)     (mês aberto/fechado)    │
│                                                                    │
│  Módulo Distribuição de Metas                                      │
│   ├─ DistributeGoalService (transação + invariante de fechamento)  │
│   ├─ ClosureValidator (soma == recebido, KG inteiro, >= 0)         │
│   ├─ CycleCompletenessChecker (100% chega ao Vendedor)             │
│   ├─ DistributionStrategy (PLUGÁVEL) ── RoundingPolicy (PLUGÁVEL)   │
│   └─ SuggestionService (usa histórico via porta abaixo)            │
│                                                                    │
│  Porta: SalesHistoryProvider (interface)                           │
│   └─ Adaptador Postgres externo (Anticorruption Layer)             │
└──────┬──────────────────────────────────────┬──────────────────────┘
       │ read/write                            │ SOMENTE LEITURA
┌──────▼───────────────┐            ┌──────────▼──────────────────────┐
│ Postgres da APLICAÇÃO │            │ Postgres EXTERNO (histórico)    │
│ (hierarquia, ciclos,  │            │ schema DESCONHECIDO — ver open  │
│  metas, usuários)     │            │ question; acesso via adaptador  │
└───────────────────────┘            └─────────────────────────────────┘
```

## Componentes
| Componente | Responsabilidade | Tecnologia |
|---|---|---|
| Frontend de distribuição | Grade de distribuição com feedback de soma em tempo real; telas por nível | React SPA (Vite + TypeScript) — ver Decisão 4 |
| Painel do Administrador | CRUD de hierarquia, pessoas, vínculos, catálogo | Django Admin (quase gratuito) |
| Backend / API | Regras de negócio, invariantes, autorização | Django 5.2 LTS + Django REST Framework (Python) — ver Decisão 1 |
| Módulo Hierarquia | Árvore de nós/posições + closure table para consultas de subárvore | ORM + tabela de fechamento |
| Módulo Catálogo | Grupos e subgrupos de produto + mapeamento p/ fonte externa | ORM |
| Módulo Ciclos | Ciclo mensal e estado aberto/fechado | ORM |
| Módulo Distribuição | Serviço transacional, validador de fechamento, checador de completude, estratégias | Serviços de domínio Python |
| SalesHistoryProvider + Adaptador | Anticorruption layer sobre o Postgres externo | Conexão read-only isolada + DTOs |
| Banco da aplicação | Dados transacionais da aplicação | PostgreSQL — ver Decisão 3 |

## Decisões-Chave

### Decisão 1: Stack de backend / arquitetura (decisão mais cara de reverter)
- **Escolha:** **Django 5.2 LTS + Django REST Framework**, como monólito modular,
  com camada de domínio explícita (services) para as regras de meta. **Linguagem
  Python** — o que está agora **alinhado à preferência declarada do usuário**
  (backend + testes em Python; ver "Preferências Declaradas do Usuário").
- **Alternativas consideradas (todas em Python, respeitando a preferência):**
  - **(B) Python FastAPI + SQLAlchemy + SPA React.**
  - **(C) Python Django "puro" (templates/HTMX) sem SPA.**
  - *(Fora da preferência, registrada só como contraste: um stack TypeScript
    full-stack — Next.js — foi descartado por não atender à preferência de
    linguagem Python declarada pelo usuário.)*
- **Trade-offs / por que Django e não as outras — ligado a requisitos do brief:**
  - *Manutenção da hierarquia por um Administrador* (hipótese do brief): o **Django
    Admin** entrega o CRUD de hierarquia/pessoas/catálogo praticamente de graça;
    em (B) esse painel é construído à mão.
  - *Fonte de histórico em Postgres externo separado do banco da app*: Django tem
    suporte **nativo a múltiplos bancos** com database routers, encaixando o
    requisito "banco externo read-only separado" sem gambiarra. (B) exige montar
    isso na mão com um segundo engine/sessão SQLAlchemy.
  - *Cinco fórmulas plugáveis de cálculo de proporção*: Python é forte para lógica
    numérica/estratégias e futura análise de histórico — e é a **linguagem preferida
    do usuário**, o que remove qualquer atrito de escolha aqui.
  - *Invariante transacional*: ambos suportam transações ACID; empate técnico.
  - Contra Django: mais "opinado"/pesado que FastAPI para uma API pura. Mitigado
    porque o **Django Admin** paga esse custo devolvendo o CRUD do Administrador.
- **Reversibilidade:** **cara de reverter** — define framework, ORM, forma dos
  serviços e o painel admin (a **linguagem Python** em si está estabilizada pela
  preferência do usuário). Por isso a decisão recebe alternativas reais.
- **Ressalva (rebaixada de risco para nota — ver O2):** implementações anteriores
  (uma FastAPI/Next.js e uma Django) foram descartadas e o **motivo do descarte é
  desconhecido** para este design (por restrição da task, não consultei versões
  antigas). Isso **não contradiz** a preferência declarada: o usuário quer Python, e
  Python é o que este design recomenda. A ressalva permanece apenas como
  transparência sobre o histórico, não como um veto pendente.

### Decisão 2: Modelo da cascata de metas com alocação encadeada (invariante)
- **Escolha:** cada repasse é uma `GoalAllocation` que aponta para a alocação-pai
  (`parent_allocation`) da qual foi quebrada. A invariante de fechamento é local a
  cada alocação: *soma das alocações-filhas diretas == quantidade da alocação-pai*.
- **Alternativas consideradas:** (B) armazenar apenas os valores por nó sem vínculo
  pai-filho e recalcular somas por convenção; (C) event sourcing das distribuições.
- **Trade-offs:** o encadeamento pai-filho torna a invariante **verificável e
  auditável por linha** (atende "auditável" do brief) e simplifica reabertura. (B)
  perde rastreabilidade da origem de cada meta; (C) é poderoso para auditoria mas
  caro/complexo demais para o MVP.
- **Reversibilidade:** média — é o coração do modelo de dados; escolhido junto da
  Decisão 1 como parte do núcleo arriscado.

### Decisão 3: Banco da aplicação — PostgreSQL
- **Escolha:** PostgreSQL para o banco da aplicação (separado do Postgres externo).
- **Alternativas consideradas:** MySQL/MariaDB; SQLite.
- **Trade-offs:** Postgres oferece CTEs recursivas (consultas de subárvore para
  isolamento de escopo), constraints ricas (CHECK para KG inteiro/>= 0),
  transações robustas e homogeneidade operacional com a fonte já existente. SQLite
  não serve para concorrência multiusuário de escrita.
- **Reversibilidade:** média (fácil se o acesso a dados ficar atrás de repositórios).

### Decisão 4: Frontend — React SPA + Django Admin para o Administrador
- **Escolha:** SPA React (Vite + TypeScript) para as telas de distribuição;
  **Django Admin** para a manutenção de hierarquia/catálogo do Administrador. A
  escolha do framework é **decisão técnica minha**, feita para atender diretamente às
  **duas prioridades declaradas pelo usuário** para o frontend.
- **Alternativas consideradas:** Django templates + HTMX (server-rendered, mais
  enxuto); Next.js como frontend SSR.
- **Trade-offs — amarrados às duas prioridades do usuário:**
  - *Prioridade 1 — fácil de configurar/rodar (time interno pequeno):* Vite oferece
    um **setup de frontend mínimo e rápido** (dev server instantâneo, build simples,
    sem a complexidade de um framework SSR full-stack como Next.js). Para o CRUD do
    Administrador, reaproveitar o **Django Admin** elimina construir a tela mais
    chata do sistema — zero esforço de setup adicional. Isso mantém o esforço de
    configuração baixo, coerente com a prioridade 1.
  - *Prioridade 2 — visualmente atraente/chamativo (boa UI/UX):* a grade de
    distribuição precisa de **feedback de soma em tempo real** ("falta/sobra X KG
    para fechar"), estados interativos e uma experiência de edição fluida — algo em
    que uma SPA React entrega uma UI rica e polida com naturalidade. HTMX faria de
    forma mais enxuta, porém com UX de edição em grade menos fluida, o que conflita
    com a prioridade 2. React deixa o caminho aberto para uma camada visual moderna.
  - *Nota:* a **biblioteca/design system específico de UI ainda não está decidido** e
    **não é registrado aqui como aprovado** — será escolhido na implementação, também
    otimizando para setup fácil + aparência atraente. O que está fixado é o framework
    de renderização (React SPA via Vite/TS), não uma lib de componentes específica.
- **Reversibilidade:** fácil (contrato via API JSON isola o frontend, permitindo
  trocar o framework de UI depois sem tocar no backend).

### Decisão 5: Ponto de extensão para as fórmulas (plugável)
- **Escolha:** interface `DistributionStrategy` + `RoundingPolicy`, selecionadas via
  registry por nível/modo (automático vs. manual). Detalhado em "Ponto de Extensão".
- **Alternativas consideradas:** hardcode das fórmulas quando definidas; regras em
  banco/config.
- **Trade-offs:** a interface isola as 5 pendências de cálculo de todo o resto —
  definir cada fórmula depois vira implementar uma classe, **sem retrabalho
  estrutural** (diretriz do brief). Hardcode violaria a diretriz.
- **Reversibilidade:** fácil, por design.

## Modelo de Dados Conceitual

Entidades principais (nomenclatura nova, sem herança de versões anteriores):

- **User** — credenciais próprias (usuário/senha, hash), `is_admin`, e vínculo 1:1
  (ou 1:N a confirmar) a um `HierarchyNode`. O vínculo é o que ancora escopo e nível.
- **HierarchyNode** — nó/posição da árvore organizacional. Campos: `id`,
  `level` (enum: GERENTE, REGIONAL, LOCAL, SUPERVISOR, VENDEDOR), `parent_id`
  (self-FK), `nome/pessoa`, `ativo`. Um único GERENTE raiz.
- **HierarchyClosure** — closure table (`ancestor_id`, `descendant_id`, `depth`)
  para consultas O(1) de "todos os descendentes de X" (isolamento de escopo) sem
  recursão em runtime. Alternativa equivalente: CTE recursiva; a closure table é
  preferida para consultas frequentes de visibilidade.
- **ProductGroup** — grupo de produto (Embutidos, Frangos, Pescados, Revenda).
- **ProductSubgroup** — subgrupo, FK para `ProductGroup`.
- **Product** (opcional / condicional) — produto individual, FK para subgrupo.
  Necessário **apenas se** a granularidade do Vendedor for produto individual —
  ver open question O1.
- **ExternalProductMapping** — mapeia identificadores da fonte Postgres externa
  (código de grupo/subgrupo/produto lá) para `ProductGroup`/`ProductSubgroup`
  internos. Preenchido quando a open question O3 for respondida.
- **Cycle** — ciclo mensal. Campos: `ano`, `mes`, `status` (ABERTO/FECHADO),
  unicidade por (ano, mes). O estado ABERTO habilita edição/reabertura (hipótese H4).
  A transição ABERTO→FECHADO é **guardada pela checagem de completude** (ver
  "Completude de Ciclo").
- **GoalAllocation** — o repasse de meta. Campos:
  - `cycle_id`
  - `owner_node_id` — nó que **recebe/possui** esta parcela de meta
  - `parent_allocation_id` — alocação da qual esta foi quebrada (`null` na raiz =
    metas globais do Gerente por grupo)
  - `granularity` (enum: GROUP, SUBGROUP, PRODUCT)
  - `group_id` / `subgroup_id` / `product_id` — apenas o campo compatível com a
    granularidade é preenchido (constraint de consistência)
  - `quantity_kg` — inteiro, CHECK `>= 0`
  - `distributed` (bool) — se este nó já repassou esta parcela para baixo. É a base do
    gate de completude: uma alocação de nível não-VENDEDOR com `distributed == false`
    é uma parcela "presa".
  - metadados de auditoria (criado_por, timestamps)

Relações-chave:
- A árvore de metas espelha a árvore hierárquica **por parcela**: a meta global do
  Gerente por grupo é raiz; cada distribuição cria filhos apontando ao pai.
- A mudança de granularidade acontece nas quebras: uma alocação GROUP (recebida pelo
  Coordenador Local) tem filhas SUBGROUP cujos subgrupos pertencem àquele grupo.

## Isolamento de Escopo por Ramo (modelo de autorização)

Princípio: **imposto na camada de dados, nunca só na UI.**

1. **Escopo de leitura:** todo acesso a `HierarchyNode`/`GoalAllocation` passa por um
   manager/repositório base que filtra por `owner_node_id ∈ descendentes(node_do_user)`
   (inclusive o próprio nó), resolvido via `HierarchyClosure`. Assim um usuário só
   enxerga sua subárvore e as metas que possui/distribuiu; ramos irmãos ficam
   invisíveis por construção da query.
2. **Escopo de escrita (object-level):** distribuir só é permitido quando
   `allocation.owner_node == node_do_user` (só distribuo o que recebi) e os destinos
   são **filhos diretos** do meu nó. Checagem no serviço de domínio, não na view.
3. **Admin:** `is_admin` tem escopo próprio (gestão de estrutura), separado da
   cadeia de distribuição.
4. **Defesa em profundidade:** testes automatizados de isolamento (um usuário de um
   ramo nunca resolve nós/metas de outro ramo) como critério de aceite verificável
   (critério de sucesso do brief).

## Integração com o Postgres Externo (Anticorruption Layer)

Como o **schema é desconhecido** (open question O3), o design isola totalmente esse
risco:

- **Porta `SalesHistoryProvider`** (interface no domínio): métodos como
  `sales_kg(dimensao, periodo) -> DTO normalizado`. O domínio depende só da porta.
- **Adaptador Postgres** (implementação): única parte do sistema que conhece o schema
  externo. Usa uma **conexão dedicada, somente leitura**, isolada do banco da app
  (via database router do Django ou pool próprio). Traduz linhas externas em DTOs
  internos (KG por grupo/subgrupo por mês).
- **Sem mapear tabelas externas como models do domínio** — evita acoplar o modelo da
  aplicação a um schema que não controlamos e pode mudar.
- **Fake/Stub Provider:** implementação falsa para desenvolvimento e testes,
  permitindo construir e validar todo o sistema **antes** de a fonte real estar
  configurada (mitiga a dependência externa como bloqueio).
- **Mapeamento de identificadores** (`ExternalProductMapping`) resolve "como grupos e
  subgrupos são identificados lá" quando O3 for respondida — trocar o mapeamento não
  toca o resto do sistema.

## Ponto de Extensão para as Fórmulas (plugável)

Cinco pendências de cálculo do brief, todas atrás de contratos estáveis:

- **`DistributionStrategy`** — dado `total_kg` (inteiro recebido) e a lista de alvos
  (filhos diretos + contexto, ex.: histórico via `SalesHistoryProvider`), retorna
  `{alvo: quantidade_kg}`. Cobre: distribuição Regional→Local, quebra Grupo→Subgrupo,
  distribuição Supervisor→Vendedor.
- **`SuggestionStrategy`** — sugestão automática de metas por grupo para o Gerente,
  a partir do histórico (12 meses, hipótese H2).
- **`RoundingPolicy` / `RemainderAllocation`** — política que transforma proporções
  fracionárias em KG inteiro **e aloca o resto** para fechar exatamente. É a 5ª
  pendência e o núcleo do conflito "fração natural vs. inteiro exato".
- **Modo manual** é apenas uma estratégia onde o usuário fornece os valores; segue
  passando pelo mesmo validador de fechamento.
- **Registry** seleciona a estratégia por nível e por modo (auto/manual).
- **Placeholder não aprovado:** um `RoundingPolicy` default (ex.: método do maior
  resto / Hamilton) pode ser plugado para destravar desenvolvimento, deixando
  **claro que não é a fórmula aprovada** — a definição real vem da discussão de
  proporção do usuário. Nenhuma fórmula está hardcoded no fluxo.

## Invariante de Fechamento Exato (validada em cada repasse)

A exatidão é **garantida pela arquitetura, independente da fórmula** (diretriz do brief):

1. **`ClosureValidator`** (independente da estratégia): dada uma alocação-pai e o
   conjunto de filhas propostas, rejeita se `soma(filhas.quantity_kg) != pai.quantity_kg`,
   se algum valor não for inteiro, ou se algum for `< 0`.
2. **`DistributeGoalService`** executa em **uma transação ACID**: recebe/computa os
   inteiros (via estratégia), passa pelo `ClosureValidator`, e só então persiste as
   filhas atomicamente. Falha na invariante = rollback; nunca existe estado parcial.
3. **Garantias de banco:** CHECK `quantity_kg >= 0` e tipo inteiro no schema; a soma
   é garantida na aplicação dentro da transação (opcionalmente reforçável por trigger
   de constraint deferida como defesa em profundidade).
4. **Reabertura/edição com cascata (H4):** enquanto o ciclo está ABERTO,
   redistribuir apaga/recria as filhas diretas dentro da mesma transação validada — a
   invariante local nunca é violada nem mesmo transitoriamente. Mas quando um total
   **intermediário** muda (ex.: Regional reabre e altera uma parcela já distribuída
   para baixo), a soma local deixaria de bater com **todo o subtree** abaixo daquele
   ramo. A semântica de cascata é definida explicitamente (ver "Semântica de Cascata
   na Reabertura"): os descendentes do ramo afetado são **invalidados** e o ciclo é
   reconduzido a estado incompleto até nova distribuição. Fechar o ciclo bloqueia
   mutações — e só é permitido se a completude do ciclo (abaixo) for satisfeita.
5. Como qualquer estratégia (auto ou manual) desemboca no mesmo validador, **trocar a
   fórmula não pode quebrar o fechamento** — o pior caso de uma fórmula ruim é ser
   rejeitada, nunca produzir sobra/falta persistida.

## Completude de Ciclo — "100% chega ao Vendedor" (invariante end-to-end)

A invariante de fechamento acima é **local** (soma das filhas == pai em cada
repasse). Ela garante que nada se perde num repasse, mas **não** garante, sozinha,
que a meta percorreu a árvore inteira até a ponta: um ciclo poderia ser FECHADO com
parcelas **presas em níveis intermediários** (ex.: uma alocação do Coordenador Local
nunca repassada ao Supervisor/Vendedor). O critério de sucesso do brief — *"100% da
meta chega aos vendedores"* — é uma propriedade **end-to-end distinta** do fechamento
por nível e é imposta arquiteturalmente por uma checagem de completude:

1. **Definição de completude.** Um ramo está completo quando toda **folha da subárvore
   ativa** da árvore de `GoalAllocation` pertence a um nó de `level == VENDEDOR`.
   Equivalentemente: não pode existir nenhuma alocação de nível intermediário
   (GERENTE..SUPERVISOR) com `distributed == false`. O flag `distributed` marca
   exatamente as alocações já repassadas; a completude exige `distributed == true`
   para toda alocação cujo `owner_node.level` **não** seja VENDEDOR. Alocações no nível
   VENDEDOR são folhas legítimas (fim natural da cascata) e não precisam de repasse.
2. **`CycleCompletenessChecker`** (serviço de domínio): percorre a árvore de alocações
   do ciclo — usando `parent_allocation_id` e a `HierarchyClosure` para delimitar a
   subárvore ativa — e retorna os "pontos presos" (alocações intermediárias com
   `distributed == false`) junto do total de KG parado por ramo. Enquanto essa lista
   não estiver vazia, o ciclo está **incompleto**.
3. **Onde roda no fluxo:** (a) de forma **assistiva** durante a distribuição,
   alimentando a UI com "faltam N KG para chegar à ponta" e a lista de nós pendentes;
   e (b) como **gate de fechamento** — `CloseCycleService` invoca o
   `CycleCompletenessChecker` dentro de uma transação e **recusa marcar o ciclo como
   FECHADO** enquanto houver qualquer alocação intermediária pendente. Fechamento e
   completude passam a ser verificados juntos: um ciclo FECHADO implica, por
   construção, soma exata em cada nível **e** 100% da meta materializada no nível
   VENDEDOR.
4. **Coerência com o modelo existente:** a checagem reutiliza `GoalAllocation`
   encadeada, o flag `distributed` e a `HierarchyClosure` já descritos — não introduz
   estrutura de dados nova, apenas uma leitura de completude sobre eles. O tratamento
   de nós inativos / ramos sem vendedor ativo depende da política da subárvore ativa e
   interage com O4/O5 (ver Open Questions).

## Semântica de Cascata na Reabertura (H4)

Quando um total **já distribuído** é reaberto e alterado num nível intermediário, a
mudança precisa se propagar para não deixar o subtree inconsistente com o novo total.
A política é:

1. **Invalidação do ramo afetado.** Editar a `quantity_kg` de uma alocação que já foi
   repassada (`distributed == true`) **invalida suas alocações-filhas**: na mesma
   transação, as filhas diretas do ramo alterado são removidas (ou marcadas como
   obsoletas) e a alocação volta a `distributed == false`. A invalidação é **em
   cascata** por todo o subtree daquele ramo — nenhuma alocação órfã com soma
   inconsistente sobrevive à transação. Assim a **invariante de fechamento exato**
   nunca fica violada no estado persistido.
2. **Volta a incompleto.** Como o ramo passa a ter uma alocação intermediária
   pendente, o `CycleCompletenessChecker` passa a reportar o ciclo como **incompleto**;
   o ciclo **não pode ser fechado** até que a nova distribuição refaça o repasse até o
   nível VENDEDOR, restabelecendo tanto a invariante de fechamento quanto a completude
   end-to-end (GAP acima).
3. **Escopo mínimo da invalidação.** Só o **ramo efetivamente alterado** é invalidado;
   ramos irmãos não tocados permanecem válidos e completos. Isso mantém o esforço de
   redistribuição proporcional à mudança.
4. **Fronteira com política de negócio (O4).** *Reabrir e redistribuir* um total (o
   valor muda, mas o nó dono permanece) está coberto acima. Já a **mudança de
   hierarquia com ciclo aberto** — mover/desativar pessoas ou nós, e para onde vai a
   meta dos nós afetados (reatribuir? zerar? migrar para o pai?) — é **política de
   negócio ainda em aberto (O4)** e permanece pendente ao usuário. O mecanismo de
   invalidação em cascata é a **base técnica** sobre a qual essa política será
   aplicada, mas a **regra** de destino da meta de um nó removido não é decidida aqui.

## Como Endereça Cada Restrição do Brief
| Restrição (Problem Brief) | Como a solução atende |
|---|---|
| Web interno | Monólito modular servindo SPA + Django Admin |
| Login próprio usuário/senha, sem SSO | Módulo Auth com credenciais próprias; sem IdP externo |
| Ciclo mensal | Entidade `Cycle` (ano, mês, status), unicidade por mês |
| KG sempre inteiro | `quantity_kg` inteiro + CHECK; validador rejeita não-inteiros |
| Fechamento exato (rígido) | `ClosureValidator` + serviço transacional, independente da fórmula |
| 100% da meta chega aos vendedores | `CycleCompletenessChecker` como gate de fechamento: só FECHA se toda folha ativa é VENDEDOR (sem alocação intermediária pendente) |
| Isolamento de escopo por ramo | Filtro por subárvore (closure table) na camada de dados + checagem object-level |
| Hierarquia fixa de 5 níveis, granularidade variável | `HierarchyNode.level` + `granularity` por alocação |
| Fórmulas plugáveis sem retrabalho | Interfaces Strategy/RoundingPolicy + registry |
| Auditabilidade | Encadeamento `parent_allocation` + metadados de auditoria |
| Reabertura consistente (H4) | Invalidação em cascata do ramo alterado + retorno a "incompleto" até redistribuir |
| Preferência do usuário: backend + testes em Python | Django 5.2 (Python) + suíte de testes em Python (ver Decisão 1) |
| Preferência do usuário: frontend fácil de rodar + UI atraente | React SPA via Vite/TS (setup mínimo) + Django Admin p/ CRUD (ver Decisão 4) |

## Riscos Técnicos e Mitigação
| Risco | Probabilidade | Mitigação |
|---|---|---|
| Schema/credenciais do Postgres externo desconhecidos (O3) | Alta | Anticorruption layer + Fake Provider permitem construir/testar sem a fonte real; só o adaptador muda quando O3 fechar |
| Fórmula de arredondamento/rateio ainda indefinida | Alta | `RoundingPolicy` plugável; `ClosureValidator` garante exatidão qualquer que seja a fórmula |
| Conflito fração natural vs. KG inteiro exato | Alta | Rounding/remainder é responsabilidade explícita e isolada; validador impede persistir sobra/falta |
| Ciclo fechado com meta presa em nível intermediário (100% não chega à ponta) | Média | `CycleCompletenessChecker` como gate de fechamento; UI assistiva sinaliza KG parado por ramo antes do fechamento |
| Reabertura de total intermediário deixa subtree inconsistente | Média | Invalidação em cascata do ramo (filhas removidas, `distributed=false`) na mesma transação; ciclo volta a "incompleto" até redistribuir |
| Bug de isolamento vaza dados entre ramos | Média | Escopo imposto na camada de dados + suíte de testes de isolamento como critério de aceite |
| Mudança de hierarquia no meio do ciclo afeta metas já distribuídas (H3) | Média | Alocações referenciam nós; base técnica é a invalidação em cascata, mas a **regra** de reatribuição é política de negócio a definir — fora do MVP até validação (O4) |
| Granularidade da ponta (Vendedor) ambígua (O1) | Média | `granularity` genérico (GROUP/SUBGROUP/PRODUCT); `Product` só entra se necessário — decisão adiável |
| Latência/indisponibilidade da fonte externa na sugestão | Média | Sugestão é assistiva, não bloqueante; timeouts + fallback para entrada manual |
| Motivo do descarte das versões anteriores desconhecido (O2) | Baixa | Rebaixado: usuário declarou preferência por Python, alinhada à Decisão 1; permanece só como nota de transparência, não como veto pendente |

## Fora de Escopo Nesta Versão
- Acompanhamento de realizado vs. meta e dashboards de performance (hipótese H1 — MVP
  só distribui).
- Escrita/alteração no ERP ou no Postgres fonte (somente leitura).
- SSO corporativo.
- Fluxo de aprovação formal de metas (H4 permite reabrir sem aprovação no MVP).
- Definição das fórmulas de proporção e do método de arredondamento (pendência do
  usuário; a arquitetura só provê os pontos de extensão).
- Escolha da biblioteca/design system específico de UI do frontend (será decidida na
  implementação, otimizando setup fácil + aparência atraente).
- **Regra de negócio** de reatribuição de metas quando a hierarquia muda no meio do
  ciclo (depende de O4). A **base técnica** (invalidação em cascata) já está no design;
  a política de destino da meta do nó removido é que fica pendente.

## Confiança do Design
**0.73** — O núcleo estrutural (monólito modular, modelo de alocação encadeada,
invariante de fechamento transacional, completude end-to-end até o Vendedor,
isolamento por closure table, anticorruption layer, pontos de extensão plugáveis) é
sólido e mapeado a restrições reais do brief. A confiança sobe levemente porque a
**preferência declarada do usuário por Python** confirma a linguagem da Decisão 1,
removendo o antigo risco de veto (O2 rebaixado).
O que ainda depende de validação: (a) as 5 fórmulas e o método de arredondamento
(pendência de cálculo do usuário — a arquitetura acomoda, mas a fórmula real pode
revelar necessidade de contexto adicional na interface `DistributionStrategy`);
(b) o schema real do Postgres externo (O3); (c) a granularidade exata da ponta
Vendedor (O1); (d) a política de negócio de reatribuição na mudança de hierarquia com
ciclo aberto (O4) — o mecanismo técnico de cascata está definido, a regra não.
Nada disso bloqueia começar pelo núcleo com o Fake Provider.

---

### Open Questions remanescentes (para o usuário real)
- **O1 — Granularidade do Vendedor:** a meta final do Vendedor é por **subgrupo**
  (mesma granularidade do Supervisor, apenas por pessoa) ou por **produto
  individual**? O brief é ambíguo ("individual na ponta" vs. descrições de
  stakeholder). Decide se a entidade `Product` entra no MVP.
- **O2 — Nota/ressalva (NÃO é mais pergunta que muda a decisão):** o usuário
  **declarou preferência por Python** para backend + testes, então **Python deixa de
  ser risco de veto** e reforça a Decisão 1. Permanece apenas a ressalva de que o
  **motivo do descarte das implementações anteriores** (FastAPI/Next.js e Django) é
  desconhecido por restrição desta task — o que **não contradiz** a preferência
  declarada. Nada aqui bloqueia ou reverte a decisão de stack.
- **O3 — Fonte Postgres (herdada do brief):** esquema/tabelas do histórico,
  credenciais (idealmente read-only) e como grupos/subgrupos são identificados no
  banco. Bloqueia apenas a integração real, não o desenvolvimento (Fake Provider).
- **O4 — Hierarquia x metas em andamento (política de negócio pendente):** o que
  acontece com metas já distribuídas quando o Administrador altera pessoas/vínculos
  com o ciclo aberto? O design já define o **mecanismo técnico** (invalidação em
  cascata do ramo afetado + retorno a "incompleto"), mas a **regra de negócio** — para
  onde vai a meta de um nó removido/movido (reatribuir ao pai, ao substituto, zerar,
  migrar), e se isso pode ocorrer com ciclo aberto — continua **ambígua e pendente ao
  usuário**. Regras de reatribuição ficam fora do MVP até essa definição.
- **O5 — Vínculo User↔Node:** um usuário mapeia para exatamente um nó, ou uma pessoa
  pode ocupar mais de uma posição/ramo? Afeta o modelo de escopo e a definição de
  "subárvore ativa" usada pela checagem de completude.
