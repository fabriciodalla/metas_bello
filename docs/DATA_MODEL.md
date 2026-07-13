# Modelo De Dados

Este documento descreve o modelo conceitual inicial. Os nomes finais dos modelos Django podem mudar durante a implementacao.

## Entidades Principais

### Usuario

Representa uma pessoa com acesso ao sistema.

Modelo Django implementado:

- `accounts.UserProfile`: perfil operacional ligado ao usuario padrao do Django.

Campos conceituais do usuario:

- nome
- email/login
- perfil
- ativo
- referencia na hierarquia comercial, quando aplicavel

Campos de `UserProfile`:

- usuario
- perfil
- gerente, quando perfil for Gerente
- coordenador regional, quando perfil for Coordenador Regional
- coordenador local, quando perfil for Coordenador Local
- supervisor, quando perfil for Supervisor
- vendedor, quando perfil for Vendedor

Perfis iniciais:

- Administrador
- Gerente
- Coordenador Regional
- Coordenador Local
- Supervisor
- Vendedor

Regras:

- Cada usuario pode ter apenas um `UserProfile`.
- Administrador nao deve ter escopo comercial obrigatorio.
- Perfis comerciais devem informar exatamente o escopo correspondente ao perfil.
- O escopo comercial informado deve estar ativo.
- O servico `active_hierarchy_assignments_for_user` usa o perfil para retornar os vinculos vigentes e ativos do usuario.

### Hierarquia Comercial

Representa a relacao entre pessoas e niveis comerciais.

Modelos Django implementados:

- `SalesManager`: gerente.
- `RegionalCoordinator`: coordenador regional.
- `LocalCoordinator`: coordenador local.
- `Supervisor`: supervisor.
- `Seller`: vendedor.
- `HierarchyAssignment`: vinculo historico com o caminho completo da hierarquia.
- `HierarchyMovement`: operacao administrativa de mudanca de hierarquia.

Relacoes esperadas no vinculo:

- Gerente para Coordenador Regional.
- Coordenador Regional para Coordenador Local.
- Coordenador Local para Supervisor.
- Supervisor para Vendedor.

Regra aprovada:

- Coordenador Local e etapa obrigatoria entre Coordenador Regional e Supervisor.

Origem de importacao:

- O layout oficial esta em `docs/IMPORT_LAYOUTS.md`.
- Cada linha do arquivo de hierarquia representa o caminho completo ate um vendedor.
- A coluna `GERENCIA` da planilha corresponde ao papel de Gerente no sistema.
- Os codigos `ID GERENCIA`, `ID COORDENADOR REGIONAL`, `ID COORDENADOR LOCAL`, `ID SUPERVISOR` e `ID VENDEDOR` devem ser preservados como identificadores da origem.

Regras de movimentacao:

- Inclusoes criam registros nas tabelas do respectivo papel.
- Remocoes operacionais devem ser inativacoes, nunca exclusao fisica.
- Movimentacoes devem criar ou encerrar vinculos em `HierarchyAssignment`, preservando datas de vigencia.
- Cada vendedor pode ter apenas um vinculo vigente sem data de fim.
- Vendedores e demais papeis comerciais inativos permanecem no banco, mas novas distribuicoes usam somente pessoas ativas com vinculo vigente.
- `HierarchyMovement` permite mover coordenador regional, coordenador local, supervisor ou vendedor.
- Ao aplicar uma mudanca, vinculos vigentes afetados sao encerrados e novos vinculos sao criados com a nova hierarquia.

Codigos internos:

- `source_id` deve ser preservado para rastreabilidade e importacao.
- No cadastro manual, se o codigo vier vazio, o sistema deve gerar o proximo valor sequencial conforme prefixo do papel.
- A exibicao principal para o usuario administrador deve ser o nome, nao o codigo.

### Grupo

Representa um agrupamento comercial usado pelo gerente para criar metas globais.

Modelo Django implementado:

- `ProductGroup`

Campos conceituais:

- codigo
- nome
- ativo

Origem de importacao:

- `ID GRUPO`
- `GRUPO`

### Subgrupo

Representa a quebra de um grupo para distribuicao mais detalhada.

Modelo Django implementado:

- `ProductSubgroup`

Campos conceituais:

- codigo
- nome
- grupo
- ativo

Origem de importacao:

- `ID SUBGRUPO`
- `SUBGRUPO`
- vinculo com grupo por `ID GRUPO`

Regras de movimentacao:

- Subgrupo pertence a um grupo por chave estrangeira.
- Inclusao, inativacao, reativacao, remocao logica e troca de grupo devem ser registradas em `ProductSubgroupMovement`.
- Grupo possui historico proprio em `ProductGroupMovement`.
- No cadastro manual, se o codigo vier vazio, o sistema deve gerar o proximo codigo sequencial de grupo ou subgrupo.
- A exibicao principal para o usuario administrador deve ser o nome, nao o codigo.

### Ciclo De Meta

Representa um mes de metas.

Modelo Django implementado:

- `GoalCycle`

Campos:

- mes
- ano
- status
- aberto em
- fechado em
- criado por

Status:

- rascunho
- em distribuicao
- fechado
- cancelado

Regras:

- Cada par mes/ano deve existir apenas uma vez.
- O mes deve estar entre 1 e 12.
- A data de fechamento, quando preenchida, nao pode ser anterior a data de abertura.

### Meta Global

Meta criada pelo gerente para um grupo dentro de um ciclo mensal.

Modelo Django implementado:

- `GlobalGoal`

Campos:

- ciclo
- grupo
- quantidade_kg
- criado por
- status

Status:

- rascunho
- em distribuicao
- fechada
- cancelada

Regras:

- Cada ciclo pode ter apenas uma meta global por grupo.
- A quantidade em kg deve ser maior que zero.
- A quantidade em kg e persistida sem casas decimais.
- Sugestoes e distribuicoes automaticas devem arredondar kg para nenhuma casa decimal.

### Distribuicao De Meta

Representa uma quebra de uma meta recebida para destinatarios do proximo nivel.

Modelos Django implementados:

- `AllocationBatch`: lote de distribuicao de uma meta recebida.
- `AllocationLine`: linha filha de distribuicao para um destino.
- `AllocationBatchEvent`: historico de tentativas de envio, bloqueios e cancelamentos.

Campos de `AllocationBatch`:

- ciclo
- meta global
- grupo
- subgrupo, quando aplicavel
- nivel de origem
- origem correspondente ao nivel
- quantidade recebida em kg
- status
- criado/alterado por

Campos de `AllocationLine`:

- lote
- nivel de destino
- destino correspondente ao nivel
- quantidade distribuida em kg
- percentual calculado em relacao ao lote
- criado/alterado por

Campos de `AllocationBatchEvent`:

- lote
- tipo de evento
- status anterior
- novo status
- quantidade recebida em kg
- total distribuido em kg
- diferenca em kg
- criado por
- data/hora

Invariante principal:

- A soma das distribuicoes filhas deve ser igual a 100% da meta recebida antes do envio.

Regras implementadas:

- Quantidade recebida e distribuida devem ser maiores que zero.
- A origem deve corresponder ao nivel de origem informado.
- O destino deve corresponder ao nivel de destino informado.
- A origem do lote deve possuir vinculo vigente e ativo em `HierarchyAssignment`.
- O destino da linha deve estar ativo, pertencer ao escopo vigente da origem em `HierarchyAssignment` e ser o proximo nivel direto permitido.
- A matriz obrigatoria de transicoes e Gerente -> Coordenador Regional -> Coordenador Local -> Supervisor -> Vendedor.
- O grupo do lote deve ser o mesmo da meta global.
- O subgrupo, quando informado, deve pertencer ao grupo do lote.
- O servico `evaluate_allocation_batch_closure` soma as linhas de um lote e reutiliza o validador de fechamento 100%.
- O servico `attempt_send_allocation_batch` altera o status para `ENVIADA` quando fecha 100% ou `BLOQUEADA` quando ha diferenca.
- Cada tentativa de envio registra um `AllocationBatchEvent` com recebido, distribuido e diferenca.

Ponto ainda pendente:

- Definir cancelamento e demais transicoes do fluxo de aprovacao.

### Sugestao De Distribuicao

Registra a sugestao gerada a partir do historico do ERP/banco.

Contrato do historico ERP:

- mes de emissao no formato `YYYY-MM`
- codigo auxiliar de supervisor/carteira
- nome do vendedor
- nome do subgrupo
- total vendido em kg

Campos conceituais:

- ciclo
- meta de origem
- criterio usado
- periodo historico
- destinatario sugerido
- quantidade_sugerida_kg
- percentual_sugerido
- total historico em kg
- total historico alocavel em kg
- volume sem vendedor agrupado no gerente
- volume com vendedor sem correspondencia vigente na hierarquia
- dados de referencia ou snapshot resumido

Regras:

- O vendedor do historico e a chave operacional para localizar o vinculo vigente em `HierarchyAssignment`.
- O codigo de supervisor do ERP nao substitui a hierarquia vigente do sistema.
- O nome do subgrupo vindo do ERP deve corresponder exatamente ao nome cadastrado em `ProductSubgroup`.
- Linhas sem vendedor/supervisor preservam o volume do gerente, mas nao geram linha automatica para destinos inferiores.
- A sugestao final para destinos validos deve ser arredondada para kg inteiro e fechar a quantidade recebida quando houver historico alocavel.

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
- Hierarquia, grupos e subgrupos nao devem ser apagados fisicamente quando ja puderem ter impacto historico; usar inativacao e movimentacao.

## Consultas Importantes

- Total de meta global por ciclo e grupo.
- Total distribuido por nivel da hierarquia.
- Diferenca entre recebido e distribuido.
- Status de cada etapa do fluxo.
- Metas finais por vendedor.
- Historico de ajustes manuais.
- Eventos de bloqueio por fechamento diferente de 100%.

## Pendencias

- Definir se snapshots do historico ERP serao persistidos ou apenas recalculados.
