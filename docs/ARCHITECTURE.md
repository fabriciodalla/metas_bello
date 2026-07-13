# Arquitetura

## Resumo

O sistema sera um monolito modular em Django, com banco PostgreSQL proprio para dados operacionais do sistema de metas e conexao separada somente leitura com o banco/ERP para obter historico de vendas em kg.

Essa arquitetura privilegia velocidade de entrega, controle de permissoes, auditoria e manutencao simples para um app interno.

A execucao do projeto deve acontecer em containers Docker Compose, com um servico `web` para Django e um servico `db` para PostgreSQL.

## Componentes

- Django web app: telas, regras de negocio, autenticacao, permissoes e rotas.
- PostgreSQL do sistema: usuarios, hierarquia, metas, distribuicoes, status e logs.
- Adaptador ERP read-only: consultas ao historico de vendas em kg.
- Importador Excel: carga inicial e manutencao de cadastros/hierarquia.
- Admin de cadastros: manutencao diaria de hierarquia, grupos, subgrupos e movimentacoes.
- Servico de sugestao: calcula distribuicao inicial a partir do historico.
- Servico de validacao: garante fechamento 100% antes de liberar envio.
- Auditoria interna: registra eventos relevantes de criacao, alteracao e liberacao.

## Apps Django Criados

- `accounts`: usuarios, perfis e permissoes.
- `hierarchy`: gerente, coordenadores regionais, coordenadores locais, supervisores e vendedores.
- `catalog`: grupos e subgrupos.
- `goals`: ciclos mensais, metas globais e metas recebidas.
- `allocations`: distribuicoes, ajustes manuais e validacao de fechamento.
- `approvals`: status, liberacoes, bloqueios e trilha de aprovacao.
- `imports`: importacao Excel e validacao de arquivos.
- `erp_readonly`: adaptadores de consulta ao banco/ERP.
- `audit`: eventos e historico operacional.

A base inicial dos apps ja existe. Os primeiros modelos Django de dominio foram criados em `catalog`, `hierarchy`, `goals` e `allocations`.

Modelos de `catalog`:

- `ProductGroup`: grupo comercial.
- `ProductSubgroup`: subgrupo vinculado a um grupo por chave estrangeira.
- `ProductGroupMovement`: historico de inclusao, inativacao, reativacao e remocao logica de grupos.
- `ProductSubgroupMovement`: historico de inclusao, movimentacao entre grupos, inativacao, reativacao e remocao logica de subgrupos.

Modelos de `accounts`:

- `UserProfile`: perfil operacional ligado 1:1 ao usuario Django, com escopo comercial opcional para gerente, coordenador regional, coordenador local, supervisor ou vendedor.

Modelos de `hierarchy`:

- `SalesManager`: gerente.
- `RegionalCoordinator`: coordenador regional.
- `LocalCoordinator`: coordenador local.
- `Supervisor`: supervisor.
- `Seller`: vendedor.
- `HierarchyAssignment`: vinculo historico com caminho completo gerente, regional, local, supervisor e vendedor, com vigencia.
- `HierarchyMovement`: operacao administrativa para mover coordenador regional, coordenador local, supervisor ou vendedor para nova hierarquia.

Modelos de `goals`:

- `GoalCycle`: ciclo mensal unico por mes/ano.
- `GlobalGoal`: meta global em kg por grupo dentro de um ciclo.

Modelos de `allocations`:

- `AllocationBatch`: lote de distribuicao com meta recebida, origem, grupo/subgrupo e status.
- `AllocationLine`: destino e quantidade em kg distribuida dentro de um lote.
- `AllocationBatchEvent`: trilha de tentativas de envio, bloqueios, envios e cancelamentos.

O primeiro servico implementado e `allocations.services.validation.evaluate_distribution_closure`, que valida o fechamento 100% de distribuicoes.
O servico `allocations.services.batches.evaluate_allocation_batch_closure` aplica esse contrato a um lote de distribuicao.
O servico `allocations.services.batches.attempt_send_allocation_batch` registra a tentativa e muda o status do lote para `ENVIADA` ou `BLOQUEADA`.
O servico `allocations.services.hierarchy_scope` valida se a origem possui vinculo vigente em `HierarchyAssignment` e se cada destino esta ativo, dentro do escopo hierarquico vigente e no proximo nivel direto permitido.

Telas server-rendered implementadas:

- Painel inicial em `/`.
- Ciclos e metas globais em `/ciclos/`.
- Distribuicoes em `/distribuicoes/`.
- Login proprio em `/login/`.
- Admin Django em `/admin/`.

## Fluxo Tecnico Principal

1. Usuario autenticado acessa o ciclo mensal.
2. Sistema verifica perfil e posicao na hierarquia.
3. Gestor cria ou recebe meta em kg.
4. Sistema consulta historico no `erp_readonly`.
5. Servico de sugestao calcula participacoes historicas.
6. Tela apresenta distribuicao sugerida.
7. Gestor ajusta manualmente se necessario.
8. Servico de escopo valida se os destinos pertencem a cadeia hierarquica da origem e respeitam a matriz Gerente -> Regional -> Local -> Supervisor -> Vendedor.
9. Servico de validacao soma os valores distribuidos.
10. Se a soma fechar 100%, o sistema libera o envio.
11. Se nao fechar, o sistema bloqueia e mostra a diferenca.
12. Evento e status sao registrados no PostgreSQL do sistema.

## Dados

O PostgreSQL do sistema guarda os dados operacionais e historicos do fluxo de metas. O banco/ERP permanece como fonte de historico de vendas e deve ser acessado somente para leitura.

Principios:

- Nunca gravar dados no ERP.
- Nao depender de tabelas internas instaveis sem documentar a consulta.
- Manter snapshots ou referencias suficientes para explicar sugestoes passadas.
- Registrar alteracoes manuais feitas sobre sugestoes automaticas.

## Integracoes

### ERP/Banco Somente Leitura

Uso previsto:

- Buscar historico de vendas em kg.
- Apoiar calculo de participacao historica por nivel da hierarquia.
- Fornecer dados para sugestao automatica.

Contrato esperado da consulta de historico:

- `cr8be_mes_emissao`: mes de emissao no formato `YYYY-MM`.
- `cr8be_nk_supervisor1`: codigo auxiliar de supervisor/carteira vindo do ERP.
- `cr8be_nome_vendedor1`: nome do vendedor usado para localizar a hierarquia vigente.
- `cr8be_ds_subgrupo`: nome do subgrupo, igual ao cadastro interno.
- `cr8be_total_ps_atendido`: total vendido em kg.

Regras do consumo:

- A query pode usar tabela ou view real do ERP, mas deve devolver as colunas acima.
- O mapeamento hierarquico da sugestao usa sempre o vendedor em `HierarchyAssignment`.
- O subgrupo do historico e associado ao grupo pelo cadastro interno `ProductSubgroup`.
- Registros sem vendedor/supervisor entram em um bucket de volume sem vendedor do gerente, preservando o total da unidade sem atribuir automaticamente esse volume a regional, local, supervisor ou vendedor.
- Testes automatizados devem usar fake/mock desse contrato, nunca o ERP real.

Pendencias:

- Nome do banco/servidor.
- Tipo do banco do ERP.
- Tabelas, views ou consultas autorizadas em producao.
- Regras de filtro por periodo, grupo, subgrupo, equipe e vendedor.
- Politica de timeout e tratamento de indisponibilidade.

### Excel

Uso previsto:

- Importar hierarquia.
- Importar grupos e subgrupos.
- Apoiar cargas iniciais ou atualizacoes grandes em lote.

Comando implementado:

```powershell
docker compose run --rm -v "C:\Users\FABRICIO.DALLA\Downloads:/input:ro" web python manage.py import_reference_data --subgroups /input/SUBGRUPOS_BELLO.xlsx --hierarchy /input/hierarquia_bello.xlsx --effective-on 2026-06-11 --skip-name-conflicts
```

Dependencia:

- `openpyxl` para leitura de arquivos `.xlsx`.

Ajustes rotineiros:

- Devem ser feitos pelo Django Admin ou por telas administrativas futuras.
- Nao devem exigir nova importacao completa quando houver novo vendedor, supervisor, coordenador, grupo ou subgrupo.
- Remocoes operacionais devem inativar registros e preservar historico.
- Pessoas inativas permanecem no banco para historico, mas ficam fora das novas distribuicoes operacionais.
- Mudancas de hierarquia devem ser feitas por `HierarchyMovement`, que encerra vinculos vigentes e cria novos vinculos com data de vigencia.

Codigos internos:

- `source_id` preserva os codigos de origem e permite novas sequencias internas.
- No Admin, a informacao principal exibida deve ser o nome.
- Ao cadastrar manualmente sem codigo, o sistema gera o proximo codigo pelo prefixo do modelo.

Layout oficial:

- `docs/IMPORT_LAYOUTS.md`

Pendencias:

- Validacoes obrigatorias.
- Tratamento de duplicidades.
- Politica de erro: rejeitar arquivo inteiro ou importar linhas validas.

## Autenticacao E Autorizacao

Decisao atual:

- Login proprio do Django no MVP.
- Evolucao futura para login Microsoft/empresa.
- Usuarios usam `auth.User` do Django com `accounts.UserProfile` para perfil e escopo comercial.

Perfis iniciais:

- Administrador.
- Gerente.
- Coordenador Regional.
- Coordenador Local.
- Supervisor.
- Vendedor.

Permissoes devem respeitar hierarquia. Um usuario deve visualizar e alterar somente os ciclos, metas e distribuicoes ligados ao seu papel e escopo.
O servico `accounts.services.scopes.active_hierarchy_assignments_for_user` retorna os vinculos vigentes e ativos que pertencem ao escopo do usuario.

## Regras Operacionais De Distribuicao

- Coordenador Local e etapa obrigatoria entre Coordenador Regional e Supervisor.
- A matriz de transicao direta permitida e Gerente -> Coordenador Regional -> Coordenador Local -> Supervisor -> Vendedor.
- Quantidades operacionais em kg usam `DecimalField(max_digits=14, decimal_places=0)`.
- Calculos e sugestoes automaticas devem arredondar kg para nenhuma casa decimal antes de gravar metas ou distribuicoes.

## Seguranca

- Usar variaveis de ambiente para credenciais.
- Nao versionar `.env` com segredos reais.
- Usar conexao somente leitura para ERP.
- Registrar eventos de alteracao de metas e distribuicoes.
- Validar uploads Excel antes de persistir dados.
- Aplicar permissoes por perfil e escopo hierarquico.
- Evitar exposicao de dados comerciais fora do ambiente interno.

## Testes

Prioridades de teste:

- Fechamento 100% de distribuicoes.
- Bloqueio quando houver sobra ou falta.
- Permissoes por perfil e hierarquia.
- Calculo de sugestao por historico.
- Importacao Excel com dados validos e invalidos.
- Fluxo mensal do gerente ate vendedor.
- Conexao ERP mockada ou isolada em testes.

Suite inicial antes do Django:

- `tests/test_documentation_guardrails.py`: protege decisoes criticas documentadas.
- `tests/test_security_guardrails.py`: procura segredos obvios em arquivos do projeto.
- `tests/test_erp_readonly_guardrails.py`: impede SQL de escrita no futuro app `erp_readonly`.
- `tests/test_allocation_closure_contract.py`: define contrato para validacao de fechamento 100%.

Comando atual:

```powershell
docker compose run --rm web python -m unittest discover -s tests -v
```

## Operacao

Pendencias antes de producao:

- Definir ambiente interno de deploy.
- Definir rotina de backup do PostgreSQL.
- Definir monitoramento de erros.
- Definir estrategia de logs.
- Definir quem administra usuarios e cadastros.
- Definir periodicidade de revisao da hierarquia.

## Decisoes E Trade-offs

- Django foi escolhido por atender bem usuarios, permissoes, formularios, admin, banco relacional e regras internas.
- PostgreSQL separado reduz acoplamento com ERP e preserva controle do sistema.
- Leitura direta no ERP acelera o MVP, mas exige cuidado com seguranca, performance e estabilidade das consultas.
- Login proprio acelera o inicio, mas o login Microsoft deve ser considerado quando o MVP estabilizar.
