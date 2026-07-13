# Layouts De Importacao Excel

Este documento define os layouts oficiais de importacao informados pelo usuario em 2026-06-11.

Os arquivos de origem usados como referencia foram:

- `SUBGRUPOS_BELLO.xlsx`
- `hierarquia_bello.xlsx`

Esses layouts devem ser tratados como contrato do importador. Nao criar nomes alternativos de colunas sem nova decisao.

## Regras Gerais

- Formato esperado: `.xlsx`.
- Aba esperada: `Planilha1`.
- Cabecalho obrigatorio na primeira linha.
- O importador deve validar colunas obrigatorias antes de gravar dados.
- O importador deve registrar erros de linhas invalidas.
- O importador nao deve consultar nem gravar no ERP.

## Subgrupos

Arquivo de referencia: `SUBGRUPOS_BELLO.xlsx`.

Colunas obrigatorias, nesta ordem:

| Ordem | Coluna | Uso no sistema |
| --- | --- | --- |
| 1 | `ID GRUPO` | Codigo do grupo |
| 2 | `ID SUBGRUPO` | Codigo do subgrupo |
| 3 | `SUBGRUPO` | Nome do subgrupo |
| 4 | `GRUPO` | Nome do grupo |

Exemplo de linha:

| ID GRUPO | ID SUBGRUPO | SUBGRUPO | GRUPO |
| --- | --- | --- | --- |
| `GRP_01` | `PRO_149` | `EMBUTIDOS MORTADELA` | `EMBUTIDOS` |

Validacoes esperadas:

- Todas as quatro colunas sao obrigatorias.
- `ID GRUPO` nao pode estar vazio.
- `ID SUBGRUPO` nao pode estar vazio.
- `SUBGRUPO` nao pode estar vazio.
- `GRUPO` nao pode estar vazio.
- O mesmo `ID GRUPO` deve apontar sempre para o mesmo `GRUPO`.
- O mesmo `ID SUBGRUPO` deve apontar sempre para o mesmo `SUBGRUPO` e para o mesmo `ID GRUPO`.

Observacao:

- O layout atual de subgrupos nao possui coluna de status.

## Hierarquia

Arquivo de referencia: `hierarquia_bello.xlsx`.

Cada linha representa o caminho completo da hierarquia ate um vendedor.

Colunas obrigatorias, nesta ordem:

| Ordem | Coluna | Uso no sistema |
| --- | --- | --- |
| 1 | `ID COORDENADOR REGIONAL` | Codigo do coordenador regional |
| 2 | `COORDENADOR REGIONAL` | Nome do coordenador regional |
| 3 | `ID GERENCIA` | Codigo da gerencia/gerente |
| 4 | `GERENCIA` | Nome da gerencia/gerente |
| 5 | `ID COORDENADOR LOCAL` | Codigo do coordenador local |
| 6 | `COORDENADOR LOCAL` | Nome do coordenador local |
| 7 | `ID SUPERVISOR` | Codigo do supervisor |
| 8 | `SUPERVISOR` | Nome do supervisor |
| 9 | `ID VENDEDOR` | Codigo do vendedor |
| 10 | `VENDEDOR` | Nome do vendedor |
| 11 | `STATUS` | Status do vinculo |

Exemplo de linha:

| ID COORDENADOR REGIONAL | COORDENADOR REGIONAL | ID GERENCIA | GERENCIA | ID COORDENADOR LOCAL | COORDENADOR LOCAL | ID SUPERVISOR | SUPERVISOR | ID VENDEDOR | VENDEDOR | STATUS |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `REG_01` | `DIVINO REGINALDO RODRIGUES` | `GER_01` | `FABIO SHAEN` | `COO_04` | `ANTONIO DA SILVA CAMPOS` | `SUP_08` | `WISLEY SOUZA DE OLIVEIRA` | `VEN_124` | `LUIS HENRIQUE LOPES FAGUNDES` | `ATIVO` |

Validacoes esperadas:

- Todas as onze colunas sao obrigatorias.
- Campos de codigo nao podem estar vazios.
- Campos de nome nao podem estar vazios.
- `STATUS` deve aceitar os valores informados na origem, inicialmente `ATIVO` e `INATIVO`.
- O mesmo codigo de pessoa deve apontar sempre para o mesmo nome dentro do arquivo.
- Cada linha deve preservar o caminho completo: gerencia, coordenador regional, coordenador local, supervisor e vendedor.

Observacoes:

- No sistema, a coluna `GERENCIA` corresponde ao papel de Gerente.
- Coordenador Local e etapa obrigatoria entre Coordenador Regional e Supervisor.
