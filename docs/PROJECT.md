# Projeto

## Problema

A criacao e distribuicao de metas comerciais por hierarquia tende a gerar retrabalho, falta de rastreabilidade, risco de divergencia nos totais e dificuldade para validar se os valores distribuidos fecham exatamente a meta recebida.

O sistema busca centralizar o ciclo mensal de metas em kg, mantendo cada etapa controlada pela hierarquia comercial.

## Objetivo

Criar um app web interno para cadastrar metas globais por grupo, sugerir distribuicoes com base no historico de vendas, permitir ajustes manuais e liberar o fluxo somente quando os totais fecharem 100%.

## Usuarios

- Gerente: cria metas globais por grupo e distribui para coordenadores regionais.
- Coordenador Regional: recebe metas por grupo, distribui para coordenadores locais e quebra metas de grupos em subgrupos para supervisores.
- Coordenador Local: papel confirmado como parte da hierarquia, mas suas responsabilidades detalhadas ainda precisam ser refinadas.
- Supervisor: recebe metas por subgrupo e distribui para vendedores.
- Vendedor: recebe meta final em kg.
- Administrador do sistema: mantem usuarios, permissoes, cadastros, importacoes e parametros.

## Valor De Negocio

- Reduzir divergencias entre meta global e metas distribuidas.
- Aumentar rastreabilidade de quem distribuiu, ajustou e liberou cada etapa.
- Acelerar a criacao mensal de metas com sugestao automatica baseada em historico.
- Dar aos gestores controle para ajustar a distribuicao antes do envio.
- Criar uma base historica organizada de ciclos de metas.

## Fluxo Principal

1. Gerente cria ciclo mensal de metas.
2. Gerente cadastra metas globais por grupo em kg.
3. Sistema consulta historico de vendas no banco/ERP em modo somente leitura.
4. Sistema sugere distribuicao inicial.
5. Gerente ajusta se necessario e distribui grupos para coordenadores regionais.
6. Coordenadores regionais distribuem metas de grupo para coordenadores locais, seguindo a hierarquia.
7. Coordenadores regionais quebram metas de grupos em subgrupos.
8. Coordenadores regionais distribuem valores de subgrupos para supervisores.
9. Supervisores distribuem metas de subgrupos para vendedores.
10. Em cada envio, o sistema valida se a soma distribuida fecha 100% da meta recebida.
11. Se fechar 100%, o fluxo pode seguir para o proximo nivel.
12. Se nao fechar 100%, o envio fica bloqueado ate correcao.

## Escopo Inicial

- Login proprio no Django.
- Cadastro de usuarios e perfis.
- Cadastro/importacao de hierarquia comercial por Excel.
- Cadastro/importacao de grupos e subgrupos.
- Criacao de ciclo mensal.
- Criacao de metas globais por grupo em kg.
- Sugestao automatica baseada em historico do ERP/banco.
- Ajuste manual da sugestao.
- Distribuicao hierarquica.
- Validacao de fechamento 100%.
- Historico basico de status, responsaveis e datas.

## Fora Do Escopo Inicial

- Login Microsoft/empresa em producao.
- Aplicativo mobile.
- Escrita no banco/ERP.
- Metas financeiras em R$.
- Metas por unidade configuravel.
- Acompanhamento semanal.
- Motor avancado de excecoes por variacao historica.
- Aprovacao manual para distribuicao que nao fecha 100%.

## Regras De Negocio

- A meta oficial do MVP e mensal.
- A unidade oficial do MVP e kg.
- Toda meta distribuida deve somar exatamente 100% da meta recebida.
- O envio para o proximo nivel fica bloqueado se houver sobra ou falta.
- A sugestao automatica nao e obrigatoria: o gestor pode ajustar antes de enviar.
- A hierarquia e os cadastros podem ser importados por Excel e ajustados manualmente.
- O historico do ERP/banco deve ser usado apenas para leitura.
- O sistema deve registrar quem criou, alterou, distribuiu e liberou cada etapa.

## Hipoteses

- O historico em kg esta disponivel no ERP/banco com granularidade suficiente para grupo, subgrupo, equipe e vendedor.
- O Django usara templates ou componentes server-rendered no MVP, salvo decisao futura por frontend separado.
- O PostgreSQL sera usado tanto em desenvolvimento quanto nos ambientes internos principais.

## Pendencias

- Confirmar a fonte exata do historico de vendas no ERP/banco.
- Definir se a sugestao usa 3, 6, 12 meses ou outro periodo de historico.
- Definir regra de arredondamento em kg.
- Definir responsabilidade detalhada do coordenador local.
- Definir se vendedores podem apenas consultar ou tambem confirmar recebimento da meta.
- Definir telas prioritarias do MVP.
