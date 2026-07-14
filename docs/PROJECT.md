# Metas Bello — Distribuição de Metas Comerciais

> App web interno da Bello Alimentos para distribuir metas comerciais de vendas (em KG inteiro),
> em cascata, do Gerente até cada Vendedor — com fechamento exato e auditável em cada repasse.

## Problema que resolve
Hoje a Bello quebra a meta comercial global até o vendedor de forma manual/dispersa, o que gera
risco de fechamento incorreto (sobra/falta entre níveis), falta de base histórica para sugerir
números realistas e falta de isolamento de escopo entre ramos da hierarquia. O objetivo é uma
distribuição **auditável, exata (100% distribuída até a ponta) e informada por histórico**.

## Como funciona (visão de 30 segundos)
Uma meta global em KG por grupo de produto desce por 5 níveis fixos
(**Gerente → Coordenador Regional → Coordenador Local → Supervisor → Vendedor**), com a
granularidade de produto mudando ao longo do caminho (grupo → grupo → subgrupo → subgrupo →
individual). Cada repasse é uma alocação de meta encadeada ao pai. Uma **invariante de fechamento
exato** (validação transacional independente da fórmula) garante que a soma distribuída bate com o
recebido em cada nível, e uma **checagem de completude** garante que 100% chega ao Vendedor antes de
o ciclo mensal poder fechar. As fórmulas de cálculo já têm decisão aprovada e ficam atrás de
**estratégias plugáveis** (podem ser revistas sem retrabalho estrutural). O histórico de vendas vem
de um Postgres externo read-only isolado por uma camada anticorrupção. Detalhe completo em
[architecture.md](./architecture.md).

## Stack (resumo)
- **Backend / núcleo:** Python — Django 5.2 LTS + Django REST Framework (monólito modular).
- **Frontend:** React SPA (Vite + TypeScript). Lib de UI ainda não decidida.
- **Admin (CRUD de hierarquia/catálogo):** Django Admin.
- **Banco da aplicação:** PostgreSQL. **Fonte de histórico:** Postgres externo (read-only, via adaptador).

Justificativa e alternativas em [decisions.md](./decisions.md).

## Documentação
| Arquivo | Conteúdo |
|---|---|
| [architecture.md](./architecture.md) | Componentes, invariantes (fechamento e completude), isolamento de escopo, anticorruption layer, pontos de extensão plugáveis |
| [data-model.md](./data-model.md) | Entidades conceituais (User, HierarchyNode, GoalAllocation, Cycle, catálogo) e relações |
| [decisions.md](./decisions.md) | Registro das decisões-chave, alternativas descartadas e reversibilidade |
| [open-questions.md](./open-questions.md) | Pendências de cálculo, hipóteses a confirmar, open questions ao usuário e ressalvas do gate de qualidade |
| [roadmap.md](./roadmap.md) | Fora de escopo nesta versão e próximos passos de codificação |

## Ressalvas do Plano (aprovado COM RESSALVAS pelo gate de qualidade) — todas resolvidas
A revisão de qualidade **aprovou o plano com ressalvas**, na época com várias pendências em aberto.
O usuário já resolveu todas elas diretamente:
- **5 pendências de cálculo — todas resolvidas.** P1-P4 (Decisão 6, decomposição tendência +
  sazonalidade sobre 12 meses) e P5 (Decisão 7, maior resto/Hamilton) têm fórmula aprovada e
  implementada.
- **4 hipóteses assumidas — todas confirmadas.** H1 (MVP só distribui), H2 (12 meses de histórico),
  H3 (Administrador cuida de toda a gestão dentro da ferramenta) e H4 (reabertura sem aprovação
  formal, implementada — `ReopenAllocationService`).
- **5 open questions ao usuário — todas resolvidas.** O1 (granularidade do Vendedor: subgrupo), O3
  (Postgres externo + mapeamento texto→entidade, Decisão 9), O4 (reatribuição ao nó pai quando a
  hierarquia muda com ciclo aberto, Decisão 10) e O5 (User↔Node é 1:N, Decisão 10).
- **Ressalva de rastreabilidade:** a preferência por Python e as prioridades de frontend foram
  declaradas *após* a 1ª versão do design; a decisão de stack também se sustenta por fit técnico.

Detalhes e histórico de cada decisão em [open-questions.md](./open-questions.md) e
[decisions.md](./decisions.md). **Não invente respostas para qualquer pendência nova que surgir** —
o mesmo padrão de confirmação explícita vale daqui pra frente.

## Estado atual da codificação
O núcleo de backend, o frontend e as 10 decisões de arquitetura/fórmula já estão implementados —
ver o passo a passo completo em [roadmap.md](./roadmap.md#próximos-passos-de-codificação). Resumo
do que falta hoje, puramente operacional (nenhuma decisão de design pendente):
- Popular `ExternalProductMapping`/`ExternalSalespersonMapping` com dados reais da Bello (O3).
- Um endpoint/UI que use as estratégias `AUTO` (P1-P4) para gerar sugestão de fato, hoje só a via manual está exposta.
