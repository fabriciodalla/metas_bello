# Sistema de Gestão de Metas de Vendas — METAS BELLO

---

## Resumo Executivo

O **METAS BELLO** é um sistema web corporativo desenvolvido para a Bello Alimentos LTDA com o objetivo de digitalizar, centralizar e controlar todo o processo de definição, distribuição e acompanhamento das metas mensais de vendas em quilogramas (kg).

O sistema substitui o processo anterior realizado em Power Apps/planilhas manuais, eliminando retrabalho, inconsistências e falta de rastreabilidade. Com ele, a diretoria define a meta global por grupo de produto e o sistema propaga essa meta automaticamente pela hierarquia comercial — do gerente ao vendedor — com sugestões baseadas no histórico real de vendas do ERP.

**Benefícios estratégicos:**

- Visão consolidada e em tempo real das metas por nível hierárquico
- Sugestões automáticas de meta baseadas em histórico de 3 meses ajustado por dias úteis
- Eliminação de planilhas paralelas e inconsistências de dados
- Rastreabilidade completa de cada alteração de meta
- Controle de acesso por perfil: cada usuário vê e edita apenas o que lhe compete

---

## Contexto de Negócio

### Cenário Atual

A Bello Alimentos opera com uma força de vendas distribuída em 9 coordenações locais cobrindo cidades do Centro-Oeste e estados do entorno (Campo Grande, Dourados, Cuiabá, Rio Verde, Corumbá, Aparecida do Taboado, Rondonópolis e dois canais atacarejo). A gestão de metas mensais em kg envolve múltiplos níveis hierárquicos: gerentes, coordenadores regionais, coordenadores locais, supervisores e vendedores.

Anteriormente, esse processo era conduzido via Power Apps integrado ao Dataverse, com planilhas auxiliares e cálculos manuais, o que gerava:

- Risco de divergência entre a meta definida pela diretoria e o que chegava ao vendedor
- Ausência de histórico auditável de alterações
- Dificuldade de atualização quando havia mudança de equipe (troca de supervisor, entrada de novo vendedor)
- Dependência de licenças Microsoft e fragilidade operacional

### Principais Desafios

| Desafio | Impacto |
|---|---|
| Falta de rastreabilidade das metas | Disputas sobre o que foi acordado vs. cobrado |
| Processo manual de distribuição | Erros, retrabalho e delay na chegada da meta ao vendedor |
| Dados de equipe desatualizados | Metas enviadas para vendedores errados ou inativos |
| Sem sugestão automática calibrada | Metas definidas sem base histórica consistente |
| Sem controle de fechamento 100% | Meta total e meta distribuída podiam divergir sem aviso |

### Oportunidades Identificadas

- Calibrar metas com base real de 3 meses de vendas ajustado por dias úteis
- Cruzar projeção histórica com planejamento S&OP para validar metas
- Criar um ciclo mensal estruturado com status de aprovação por etapa
- Disponibilizar a meta final ao vendedor com clareza e antecedência

---

## Objetivos do Sistema

**Objetivo principal:** Digitalizar e automatizar o ciclo mensal de definição e distribuição de metas de vendas em kg, da diretoria ao vendedor, com sugestão baseada em histórico e controle de fechamento 100%.

**Objetivos secundários:**

1. Substituir o Power Apps por uma plataforma web corporativa própria, sem dependência de licenças externas
2. Garantir que a soma das metas distribuídas seja sempre igual a 100% da meta recebida em cada nível
3. Integrar com o ERP para obter histórico de vendas como base de sugestão automática
4. Registrar e manter o histórico completo de alterações de hierarquia e de metas
5. Respeitar o controle de acesso por perfil, garantindo que cada usuário veja somente seu escopo
6. Permitir importação de hierarquia e cadastros via planilha Excel

---

## Principais Funcionalidades

### 1. Gestão de Ciclos Mensais
Cada mês de meta é representado como um ciclo com status próprio (Rascunho → Em Distribuição → Fechado). A diretoria controla quando o ciclo está aberto para edição e quando está encerrado para análise.

### 2. Definição de Meta Global por Grupo de Produto
O gerente/diretoria define a meta mensal em kg para cada grupo de produto (ex: Frango, Suíno, Bovino, etc.). O sistema sugere automaticamente a meta baseada na média diária dos últimos 3 meses, ajustada pelos dias úteis do mês seguinte e comparada com o planejamento S&OP.

### 3. Distribuição Hierárquica de Metas
A meta global é distribuída pelos seguintes níveis:

```
Diretoria/Gerência
    └── Coordenador Regional
            └── Coordenador Local (9 filiais)
                    └── Supervisor
                            └── Vendedor
```

Cada nível recebe uma meta e distribui 100% entre os subordinados imediatos. O sistema bloqueia o envio se a distribuição não fechar exatamente 100%.

### 4. Sugestão Automática por Histórico
O sistema calcula automaticamente a participação histórica de cada vendedor/supervisor/coordenador nos últimos 3 meses de vendas reais (ERP), propondo a distribuição proporcional. O gestor pode aceitar, ajustar e confirmar.

### 5. Gestão de Equipe e Hierarquia
Cadastro e manutenção da hierarquia completa (gerentes, coordenadores, supervisores, vendedores). O sistema registra todas as movimentações (entrada, saída, troca de equipe) com data de vigência, garantindo que a meta histórica reflita a equipe do período correto.

### 6. Planejamento S&OP
O sistema armazena o planejamento de vendas (S&OP) por filial e grupo de produto, permitindo comparar a meta gerencial sugerida com o plano da empresa antes de fechar.

### 7. Importação via Planilha Excel
Hierarquia e cadastros podem ser carregados em lote via arquivos Excel padronizados, agilizando atualizações de início de ano ou reestruturações comerciais.

---

## Fluxo Macro de Operação

```
1. Abertura do Ciclo Mensal
   └── Diretoria/Admin abre o ciclo para o mês seguinte

2. Definição da Meta Global
   └── Gerente consulta sugestão (média 3M × dias úteis)
   └── Compara com S&OP
   └── Confirma a meta global por grupo de produto

3. Distribuição para Coordenadores Regionais
   └── Gerente distribui a meta para cada coordenador regional

4. Distribuição para Coordenadores Locais
   └── Coordenador regional distribui para cada coordenador local (filial)

5. Distribuição para Supervisores
   └── Coordenador local distribui por grupo de produto aos supervisores

6. Distribuição para Vendedores
   └── Supervisor distribui para cada vendedor de sua equipe

7. Encerramento
   └── Todas as distribuições fechadas em 100%
   └── Ciclo é fechado pela diretoria
   └── Metas ficam disponíveis para acompanhamento
```

---

## Benefícios Esperados

### Operacionais

- **Redução de retrabalho:** eliminação do processo manual de consolidação de planilhas
- **Agilidade:** meta chega ao vendedor no mesmo dia em que é definida pela diretoria
- **Confiabilidade:** impossibilidade técnica de distribuir mais ou menos do que 100% da meta
- **Atualização automática da equipe:** movimentações de hierarquia refletem nas metas sem intervenção manual

### Financeiros

- **Eliminação de licenças Power Apps/Dataverse:** redução de custos de plataforma Microsoft
- **Redução de horas improdutivas:** estimativa de 10-20 horas/mês economizadas em consolidação manual
- **Menor risco de metas incorretas:** redução de pagamentos equivocados de comissão por metas erradas

### Estratégicos

- **Dados históricos centralizados:** base para análises de desempenho, sazonalidade e projeção
- **Escalabilidade:** suporte a crescimento da equipe sem aumento de complexidade operacional
- **Independência tecnológica:** sistema próprio, sem dependência de fornecedores externos

### Compliance e Governança

- **Trilha de auditoria completa:** toda alteração de meta, distribuição e movimentação de equipe é registrada com data, hora e usuário responsável
- **Controle de acesso por perfil:** cada usuário vê e edita apenas seu escopo hierárquico
- **Rastreabilidade de metas:** é possível saber quem definiu, quando e com base em quê cada meta foi estabelecida

---

## Indicadores de Sucesso (KPIs)

| Indicador | Meta | Como Medir |
|---|---|---|
| Tempo de ciclo (da definição à meta no vendedor) | ≤ 1 dia útil | Diferença entre data do ciclo e data de envio ao vendedor |
| Taxa de fechamento correto (100%) | 100% dos ciclos | Lotes enviados sem bloqueio / total de lotes |
| Redução de horas manuais no processo | ≥ 70% | Comparação com processo anterior |
| Cobertura de hierarquia ativa cadastrada | 100% dos vendedores ativos | Vendedores com vínculo vigente / total ativo |
| Adoção do sistema pelos gestores | ≥ 90% dos ciclos via sistema | Ciclos criados no sistema vs. realizados |
| Disponibilidade do sistema | ≥ 99,5% no horário comercial | Monitoramento de uptime |

---

## Integrações Relevantes

### ERP Bello Alimentos (Somente Leitura)
O sistema conecta ao banco de dados do ERP exclusivamente para **leitura** do histórico de vendas em kg. Esses dados alimentam o cálculo de sugestão de metas. **Nenhum dado é gravado no ERP.**

### Planilhas Excel
O sistema aceita importação de hierarquia e cadastros via arquivos Excel padronizados. Isso permite atualizações em lote sem necessidade de cadastro manual um a um.

### Futuro: Login Microsoft (Azure AD)
O MVP utiliza login próprio. A evolução planejada é integrar com o login corporativo Microsoft, eliminando a necessidade de gerenciar senhas separadas.

---

## Arquitetura Simplificada

O sistema é uma **aplicação web interna** acessada pelo navegador, hospedada nos servidores da empresa. Não há acesso externo planejado.

```
USUÁRIO (Navegador)
       │
       ▼
SERVIDOR WEB (Sistema METAS BELLO)
       │
       ├──► BANCO DE DADOS PRÓPRIO (PostgreSQL)
       │    └── Metas, Hierarquia, Distribuições, Usuários
       │
       └──► ERP BELLO (Somente Leitura)
            └── Histórico de Vendas em KG
```

- **Banco de dados próprio:** armazena todas as metas, distribuições, usuários e hierarquias. É isolado do ERP.
- **ERP:** consultado apenas para buscar o histórico de vendas passadas, nunca modificado.
- **Sem integrações com internet:** sistema totalmente interno.

---

## Riscos e Mitigações

| Risco | Impacto | Probabilidade | Mitigação |
|---|---|---|---|
| Indisponibilidade do ERP para sugestão | Médio — gestor não vê sugestão automática | Médio | Sistema permite definição manual de meta sem depender do ERP |
| Hierarquia desatualizada no cadastro | Alto — meta enviada para pessoa errada | Médio | Validação que impede distribuição para vendedores sem vínculo vigente |
| Usuário com perfil errado | Alto — acesso indevido a metas de outros | Baixo | Controle de acesso por perfil, com validação no servidor |
| Falha no banco de dados | Alto — sistema indisponível | Baixo | Backup diário automatizado, plano de recuperação definido |
| Resistência à adoção | Médio — processo continua manual | Médio | Treinamento, suporte próximo e migração gradual |
| Meta distribuída sem fechar 100% | Alto — distorção do total | Baixo | Bloqueio técnico: sistema não permite envio sem fechar 100% |

---

## Roadmap Evolutivo

### Curto Prazo (MVP — já em desenvolvimento)
- Cadastro e importação de hierarquia via Excel
- Definição de metas globais com sugestão automática por histórico 3M
- Distribuição hierárquica com validação de fechamento 100%
- Painel de acompanhamento por ciclo
- Controle de acesso por perfil

### Médio Prazo (3–6 meses pós-MVP)
- Telas específicas por perfil (coordenador, supervisor, vendedor)
- Integração com login Microsoft (Azure AD)
- Acompanhamento de realização vs. meta em tempo real (via ERP)
- Notificações automáticas quando meta está pendente de distribuição

### Longo Prazo (6–18 meses)
- Dashboard executivo com comparativo meta vs. realizado por coordenação/filial
- Exportação de relatórios para Excel/PDF
- API para integração com outros sistemas internos
- Módulo de aprovação formal por nível hierárquico
- Histórico de performance por vendedor com análise de tendência

---

## Conclusão Executiva

O METAS BELLO representa uma evolução crítica na gestão comercial da Bello Alimentos. Ao substituir o processo manual e fragmentado em Power Apps por um sistema web corporativo próprio, a empresa ganha controle, rastreabilidade e agilidade no ciclo de metas mensais.

A sugestão automática baseada em histórico real elimina o viés e o subjetivismo nas definições, enquanto o controle de fechamento 100% garante que a meta que chega ao vendedor é exatamente a que a diretoria definiu — sem perdas nem distorções ao longo da cadeia hierárquica.

O sistema está desenhado para crescer com a empresa: cada novo vendedor, novo coordenador ou nova filial se integra ao processo sem necessidade de reestruturação. A decisão de construir sobre tecnologia aberta e banco de dados próprio elimina a dependência de licenças externas e coloca o controle nas mãos da Bello Alimentos.
