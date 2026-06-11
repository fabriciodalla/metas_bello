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

A base inicial dos apps ja existe. Neste momento, eles ainda nao possuem modelos Django de dominio. O primeiro servico implementado e `allocations.services.validation.evaluate_distribution_closure`, que valida o fechamento 100% de distribuicoes.

## Fluxo Tecnico Principal

1. Usuario autenticado acessa o ciclo mensal.
2. Sistema verifica perfil e posicao na hierarquia.
3. Gestor cria ou recebe meta em kg.
4. Sistema consulta historico no `erp_readonly`.
5. Servico de sugestao calcula participacoes historicas.
6. Tela apresenta distribuicao sugerida.
7. Gestor ajusta manualmente se necessario.
8. Servico de validacao soma os valores distribuidos.
9. Se a soma fechar 100%, o sistema libera o envio.
10. Se nao fechar, o sistema bloqueia e mostra a diferenca.
11. Evento e status sao registrados no PostgreSQL do sistema.

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

Pendencias:

- Nome do banco/servidor.
- Tipo do banco do ERP.
- Tabelas, views ou consultas autorizadas.
- Regras de filtro por periodo, grupo, subgrupo, equipe e vendedor.
- Politica de timeout e tratamento de indisponibilidade.

### Excel

Uso previsto:

- Importar hierarquia.
- Importar grupos e subgrupos.
- Ajustar cadastros iniciais.

Pendencias:

- Layout oficial das planilhas.
- Validacoes obrigatorias.
- Tratamento de duplicidades.
- Politica de erro: rejeitar arquivo inteiro ou importar linhas validas.

## Autenticacao E Autorizacao

Decisao atual:

- Login proprio do Django no MVP.
- Evolucao futura para login Microsoft/empresa.

Perfis iniciais:

- Administrador.
- Gerente.
- Coordenador Regional.
- Coordenador Local.
- Supervisor.
- Vendedor.

Permissoes devem respeitar hierarquia. Um usuario deve visualizar e alterar somente os ciclos, metas e distribuicoes ligados ao seu papel e escopo.

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
