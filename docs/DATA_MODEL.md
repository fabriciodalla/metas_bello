# Modelo De Dados

Este documento descreve o modelo conceitual inicial. Os nomes finais dos modelos Django podem mudar durante a implementacao.

## Entidades Principais

### Usuario

Representa uma pessoa com acesso ao sistema.

Campos conceituais:

- nome
- email/login
- perfil
- ativo
- referencia na hierarquia comercial, quando aplicavel

Perfis iniciais:

- Administrador
- Gerente
- Coordenador Regional
- Coordenador Local
- Supervisor
- Vendedor

### Hierarquia Comercial

Representa a relacao entre pessoas e niveis comerciais.

Relacoes esperadas:

- Gerente para Coordenador Regional
- Coordenador Regional para Coordenador Local
- Coordenador Regional para Supervisor
- Supervisor para Vendedor

Ponto em aberto: confirmar se o Coordenador Local tambem aprova, apenas recebe metas ou atua como agrupador operacional entre Regional e Supervisor.

### Grupo

Representa um agrupamento comercial usado pelo gerente para criar metas globais.

Campos conceituais:

- codigo
- nome
- ativo

### Subgrupo

Representa a quebra de um grupo para distribuicao mais detalhada.

Campos conceituais:

- codigo
- nome
- grupo
- ativo

### Ciclo De Meta

Representa um mes de metas.

Campos conceituais:

- mes
- ano
- status
- data de abertura
- data de fechamento
- criado por

Status possiveis propostos:

- rascunho
- em distribuicao
- fechado
- cancelado

### Meta Global

Meta criada pelo gerente para um grupo dentro de um ciclo mensal.

Campos conceituais:

- ciclo
- grupo
- quantidade_kg
- criado por
- status

### Distribuicao De Meta

Representa uma quebra de uma meta recebida para destinatarios do proximo nivel.

Campos conceituais:

- ciclo
- origem
- destino
- grupo
- subgrupo, quando aplicavel
- quantidade_recebida_kg
- quantidade_distribuida_kg
- percentual
- status
- criado/alterado por

Invariante principal:

- A soma das distribuicoes filhas deve ser igual a 100% da meta recebida antes do envio.

### Sugestao De Distribuicao

Registra a sugestao gerada a partir do historico do ERP/banco.

Campos conceituais:

- ciclo
- meta de origem
- criterio usado
- periodo historico
- destinatario sugerido
- quantidade_sugerida_kg
- percentual_sugerido
- dados de referencia ou snapshot resumido

### Evento De Aprovacao/Liberacao

Registra transicoes de status, bloqueios e liberacoes.

Campos conceituais:

- entidade relacionada
- status anterior
- status novo
- usuario
- data/hora
- observacao

### Importacao

Registra arquivos Excel usados para carga de cadastros e hierarquia.

Campos conceituais:

- tipo de importacao
- arquivo original ou referencia segura
- usuario
- data/hora
- total de linhas
- linhas validas
- linhas com erro
- status

## Invariantes De Dados

- Metas do MVP sempre usam kg.
- O ciclo oficial do MVP e mensal.
- Nenhuma distribuicao pode ser enviada se nao fechar 100%.
- A meta recebida por um nivel limita o total que ele pode distribuir.
- Ajustes manuais devem preservar rastreabilidade.
- Sugestoes automaticas nao substituem decisao do gestor.
- Dados do ERP sao fonte de historico, nao local de gravacao.

## Consultas Importantes

- Total de meta global por ciclo e grupo.
- Total distribuido por nivel da hierarquia.
- Diferenca entre recebido e distribuido.
- Status de cada etapa do fluxo.
- Metas finais por vendedor.
- Historico de ajustes manuais.
- Eventos de bloqueio por fechamento diferente de 100%.

## Pendencias

- Definir precisao decimal de kg.
- Definir regra de arredondamento.
- Definir unicidade de ciclo por mes/ano.
- Definir se grupos/subgrupos terao codigos vindos do ERP.
- Definir se snapshots do historico ERP serao persistidos ou apenas recalculados.
