# Problem Brief — Distribuição de Metas Comerciais (Levo Alimentos)

> **Revisão (2026-07-24):** a hierarquia comercial descrita abaixo foi ajustada de 5 para 4 níveis
> (removido o nível "Coordenador Regional") para refletir a estrutura organizacional real da Levo
> Alimentos — ver [Decisão 14](../decisions.md#decisão-14--remoção-do-nível-coordenador-regional-hierarquia-passa-de-5-para-4-níveis).
> Projeto e empresa renomeados de "Metas Bello"/"Bello Alimentos" para "Metas Levo"/"Levo
> Alimentos" nesta mesma data.

## Problema
A Levo Alimentos precisa distribuir metas comerciais de vendas (em KG) do topo
da operação comercial até cada vendedor individual, passando por vários níveis
hierárquicos. Hoje esse processo — a definição da meta global e sua quebra em
cascata até o vendedor — é feito de forma manual/dispersa, o que gera três dores
principais:

1. **Risco de fechamento incorreto:** a soma das metas distribuídas em cada nível
   pode não bater exatamente com a meta recebida do nível superior (sobra ou
   falta), corrompendo o planejamento comercial.
2. **Falta de base histórica no cálculo:** quem define metas não tem, de forma
   integrada, o histórico de vendas para sugerir números realistas por grupo/
   subgrupo de produto.
3. **Falta de isolamento de escopo:** cada responsável deveria enxergar apenas
   sua própria cadeia de subordinados e as metas que ele distribuiu, sem acesso a
   dados de outros ramos da hierarquia.

O problema real não é "construir um app" — é garantir uma distribuição de metas
**auditável, exata (100% distribuída até a ponta) e informada por histórico**,
com controle de visibilidade por hierarquia.

## Objetivo
Permitir que uma meta comercial global, definida no topo em KG por grupo de
produto, seja distribuída em cascata por todos os níveis hierárquicos até o
vendedor, com a garantia de que **em cada repasse a soma distribuída fecha
exatamente com o valor recebido** (sem sobra nem falta), usando histórico de
vendas como base de sugestão e respeitando isolamento de escopo por ramo.

Sinais mensuráveis de sucesso (a confirmar com o usuário):
- 100% da meta do topo chega aos vendedores sem divergência de fechamento em
  nenhum nível.
- Tempo do ciclo de distribuição de metas reduzido versus o processo manual atual
  (baseline a medir).
- Zero acesso indevido entre ramos distintos da hierarquia.

## Usuários / Stakeholders
- **Gerente (1, topo):** define metas globais por GRUPO de produto (Embutidos,
  Frangos, Pescados, Revenda). Consome sugestão automática baseada em histórico.
  Distribui direto para os Coordenadores Locais, mantendo o nível de GRUPO.
  Escolhe distribuição automática ou manual.
- **Coordenadores Locais (9):** recebem meta em nível de grupo do Gerente
  e quebram para nível de SUBGRUPO, respeitando o total recebido.
- **Supervisores:** recebem metas em nível de subgrupo do Coordenador Local e
  distribuem para os Vendedores sob supervisão.
- **Vendedores:** recebem a meta final individual (consumidores do resultado).
- **Administrador do sistema:** mantém a estrutura hierárquica (níveis, pessoas,
  vínculos) dentro do próprio app — ver hipótese na seção de pendências.
- **Stakeholder de dados:** responsável pelo banco PostgreSQL fonte do histórico
  de vendas (fonte a ser configurada).

## Decisões Fechadas (confirmadas pelo usuário)
- **Plataforma:** aplicativo **WEB interno**.
- **Autenticação:** **login próprio dentro do app (usuário/senha)**, sem SSO
  corporativo nesta fase.
- **Periodicidade do ciclo de metas:** **MENSAL**.

## Restrições
- **Unidade de meta:** KG (quilogramas), **sempre número INTEIRO**, sem casas
  decimais em nenhum nível.
- **Regra de fechamento exato (RÍGIDA e NÃO-NEGOCIÁVEL):** em cada nível, a soma
  do que é distribuído para baixo deve fechar EXATAMENTE com o que foi recebido de
  cima — sem sobra nem falta, em KG inteiro. A meta do topo deve ser 100%
  distribuída até os vendedores. **Este requisito é fixo.** O que fica pendente é
  apenas o MÉTODO (arredondamento/rateio de resto) usado para chegar a esse
  fechamento — ver seção de pendências.
- **Plataforma web interna** (decisão fechada).
- **Login próprio usuário/senha, sem SSO** (decisão fechada).
- **Ciclo de metas mensal** (decisão fechada).
- **Isolamento de escopo:** cada nível só vê seus subordinados diretos/indiretos
  e as metas que ele mesmo distribuiu. Nenhum acesso a estrutura, dados ou metas
  de outras cadeias/ramos.
- **Fonte de histórico:** banco PostgreSQL externo (conexão a ser configurada);
  a aplicação lê histórico de vendas por produto/grupo/subgrupo.
- **Hierarquia de níveis fixa:** Gerente → Coordenador Local → Supervisor →
  Vendedor, com o nível de granularidade de produto mudando ao longo da cascata
  (grupo → subgrupo → subgrupo → individual).

## Não-Objetivos
- Não define, nesta fase, a **fórmula/método exato** de nenhum cálculo automático
  (são pendências conhecidas — ver seção de pendências), incluindo o método de
  arredondamento/rateio de resto.
- Não resolve escrita/alteração no ERP ou no banco fonte — o Postgres é fonte de
  leitura de histórico (a menos que o usuário confirme necessidade de escrita).
- **(Hipótese a confirmar)** Não trata de acompanhamento de realizado vs. meta /
  dashboards de performance — o MVP cobre apenas a DISTRIBUIÇÃO da meta.
- Não define arquitetura, stack, banco de dados da aplicação ou modelo de dados —
  isso é responsabilidade do `solution-architect`.

## Hipóteses a Confirmar (NÃO são decisões aprovadas)
> Assunções conservadoras assumidas para permitir avançar. Precisam de
> confirmação do usuário antes de virarem requisito.
- **Escopo do MVP = apenas a DISTRIBUIÇÃO de metas.** Acompanhamento de realizado
  vs. meta fica FORA do MVP.
- **Período de histórico** usado na sugestão automática = **últimos 12 meses**.
- **Manutenção da hierarquia:** níveis e pessoas são mantidos por um
  **ADMINISTRADOR dentro do próprio sistema**.
- **Edição/reabertura:** uma meta já distribuída pode ser **reaberta/editada pelo
  nível que a distribuiu enquanto o ciclo mensal estiver aberto, SEM fluxo de
  aprovação formal no MVP**.

## Preferências de Solução do Usuário (input, não decisão final)
- Existência de um **banco PostgreSQL como fonte de histórico de vendas** é um
  dado do ambiente (input concreto), não uma escolha de stack da nova aplicação.
- **Plataforma web interna, login próprio (usuário/senha) e ciclo mensal já foram
  DECIDIDOS pelo usuário** (ver Decisões Fechadas) — não são mais preferências em
  aberto. As demais tecnologias da aplicação continuam livres para o
  `solution-architect` avaliar.

## Riscos Conhecidos Nesta Fase
- **Método de fechamento (arredondamento/rateio) ainda não definido** — o
  requisito de fechamento exato em KG inteiro é rígido e não-negociável, mas o
  método para reconciliar frações e alocar o resto está EM ABERTO, agrupado junto
  das demais fórmulas de cálculo de proporção (o usuário indicou que "vai ser de
  acordo com o cálculo de proporção que ainda estamos discutindo"). Nenhum método
  específico está aprovado. O design da solução precisa acomodar esse método como
  plugável sem retrabalho. Risco alto por ser conflito direto entre duas
  restrições críticas (fração natural vs. inteiro exato).
- **Cálculos de proporção ainda não definidos (pendência de cálculo agrupada)** —
  cinco pendências no mesmo grupo, todas dependentes da discussão de proporção em
  andamento: (1) sugestão automática por grupo, (2) distribuição automática
  gerente→local, (3) quebra grupo→subgrupo, (4) distribuição supervisor→vendedor
  e (5) método de arredondamento/rateio de resto. Todos devem ser plugáveis. Isto
  é uma pendência de definição de cálculo, não uma pergunta em aberto ao usuário.
- **Dependência de fonte externa (Postgres)** — disponibilidade, latência,
  esquema e qualidade do histórico impactam a sugestão automática.
- **Consistência do isolamento de escopo** — falha na regra de visibilidade
  expõe dados entre ramos; risco de compliance/confiança interna.
- **Modelagem da hierarquia** — a manutenção por administrador é hipótese; como
  mudanças de pessoas/ramos afetam metas já distribuídas ainda precisa validação.

## Critérios de Sucesso
- [ ] A meta global do Gerente é 100% distribuída até os vendedores, sem sobra
      nem falta, validado automaticamente em cada nível de repasse.
- [ ] Todos os valores de meta, em todos os níveis, são inteiros em KG.
- [ ] Cada usuário só consegue visualizar e distribuir dentro do seu próprio ramo
      hierárquico (isolamento de escopo verificável).
- [ ] O Gerente recebe uma sugestão automática de metas por grupo baseada em
      histórico de vendas do Postgres (fórmula plugável, definida depois).
- [ ] Gerente pode escolher distribuição automática ou manual ao repassar para o
      Coordenador Local; ambas respeitam o fechamento exato.
- [ ] Coordenador Local quebra grupo em subgrupo respeitando o total recebido.
- [ ] Supervisor distribui por subgrupo entre seus vendedores respeitando o total.
- [ ] O fechamento exato (soma distribuída = total recebido, em KG inteiro) é
      garantido em todos os níveis. O método de arredondamento/rateio que produz
      esse fechamento ainda será definido junto das fórmulas de proporção — nenhum
      algoritmo específico está aprovado.
- [ ] Login próprio (usuário/senha) associa cada usuário ao seu nível/ramo.
- [ ] Ciclos de meta são mensais.

## Confiança do Brief
**0.80** — O escopo estrutural (níveis, granularidade por nível, regra de
fechamento exato, unidade KG inteiro, isolamento de escopo) está claro e
confirmado. Plataforma (web interna), autenticação (login próprio usuário/senha)
e periodicidade (mensal) agora são DECISÕES FECHADAS — não estão mais em aberto.
Foram registradas como HIPÓTESES a confirmar: MVP restrito à distribuição,
histórico de 12 meses, manutenção da hierarquia por administrador e
edição/reabertura sem aprovação formal. Continua como PENDÊNCIA DE CÁLCULO
(agrupada na seção de Riscos, não como pergunta ao usuário) o grupo das fórmulas
de cálculo de proporção, incluindo o método de arredondamento/rateio de resto.
A única PERGUNTA AINDA ABERTA ao usuário real são os detalhes da fonte Postgres.

---

### Open Questions (para decisão do usuário real)
1. **Fonte Postgres:** esquema/tabelas do histórico de vendas, credenciais
   (idealmente somente leitura) e como os grupos (Embutidos, Frangos, Pescados,
   Revenda) e subgrupos de produto são identificados no banco.
