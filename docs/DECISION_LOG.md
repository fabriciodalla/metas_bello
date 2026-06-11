# Log De Decisoes

| Data | Topico | Status | Decisao | Motivo | Docs |
| --- | --- | --- | --- | --- | --- |
| 2026-06-10 | Formato do sistema | approved | App web interno | Melhor equilibrio para cadastro, distribuicao, acompanhamento e evolucao interna. | README.md, docs/PROJECT.md |
| 2026-06-10 | Escopo do MVP | approved | Metas com aprovacao/liberacao por hierarquia | O processo precisa seguir os niveis comerciais e manter rastreabilidade. | docs/PROJECT.md |
| 2026-06-10 | Hierarquia de distribuicao | approved | Gerente cria metas globais por grupos; Regionais distribuem para Locais e quebram grupos em subgrupos; Supervisores distribuem para Vendedores. | Reflete o fluxo informado pelo usuario. | docs/PROJECT.md, docs/DATA_MODEL.md |
| 2026-06-10 | Regra de aprovacao | approved | Aprovacao mista, com bloqueio quando a soma distribuida nao fecha 100%. | Mantem agilidade, mas impede divergencia de total. | docs/PROJECT.md, docs/ARCHITECTURE.md |
| 2026-06-10 | Excecao principal | approved | Se a soma nao fechar 100%, o envio fica bloqueado ate correcao. | Qualquer sobra ou falta invalida a distribuicao. | docs/PROJECT.md, docs/DATA_MODEL.md |
| 2026-06-10 | Cadastros e hierarquia | approved | Modelo hibrido: importacao Excel mais ajustes manuais no sistema. | Permite iniciar rapido e corrigir excecoes no app. | docs/PROJECT.md, docs/ARCHITECTURE.md |
| 2026-06-10 | Tipo de meta | approved | Meta por volume/quantidade. | O MVP nao trabalhara com valor financeiro. | README.md, docs/PROJECT.md |
| 2026-06-10 | Unidade da meta | approved | kg | Unidade escolhida para cadastro, distribuicao e validacao. | README.md, docs/PROJECT.md |
| 2026-06-10 | Ciclo de metas | approved | Mensal | Alinha o sistema ao ciclo oficial definido para o MVP. | docs/PROJECT.md |
| 2026-06-10 | Metodo de distribuicao | approved | Sugestao automatica mais ajuste manual. | Acelera o trabalho sem tirar controle dos gestores. | docs/PROJECT.md |
| 2026-06-10 | Base da sugestao | approved | Historico direto do banco/ERP. | Usa dados reais da operacao comercial. | docs/ARCHITECTURE.md |
| 2026-06-10 | Integracao ERP | approved | Leitura direta em banco somente leitura. | Acelera o MVP mantendo restricao de seguranca para nao gravar no ERP. | docs/ARCHITECTURE.md |
| 2026-06-10 | Tecnologia web | approved | Django | Boa aderencia a usuarios, permissoes, formularios, admin e banco relacional. | README.md, docs/ARCHITECTURE.md |
| 2026-06-10 | Banco do sistema | approved | PostgreSQL para o sistema e leitura separada do ERP. | Evita acoplamento operacional com o ERP. | README.md, docs/ARCHITECTURE.md |
| 2026-06-10 | Login | approved | Login proprio no MVP, login Microsoft/empresa depois. | Permite iniciar rapido sem perder caminho corporativo futuro. | docs/ARCHITECTURE.md |
| 2026-06-10 | Estrategia inicial de testes | approved | Suite inicial com `unittest`, guardrails de documentacao/seguranca/ERP e contratos para os futuros apps Django. | Permite validar regras criticas sem depender ainda de Django, banco ou rede. | docs/TESTING.md, tests/README.md |
| 2026-06-11 | Execucao em containers | approved | Todo desenvolvimento e execucao do projeto devem acontecer via Docker Compose. | Padroniza ambiente, evita dependencia de instalacao local e alinha PostgreSQL/Django desde o inicio. | README.md, docs/ARCHITECTURE.md, docs/TESTING.md, AGENTS.md |
| 2026-06-11 | Base Django inicial | approved | Criar projeto Django `config`, apps modulares por dominio e PostgreSQL em servico Docker separado. | Comeca a implementacao preservando a arquitetura documentada de monolito modular e banco proprio. | README.md, docs/ARCHITECTURE.md |
| 2026-06-11 | Primeiro contrato de dominio | approved | Implementar `allocations.services.validation.evaluate_distribution_closure` com `Decimal`, `can_send` e `difference_kg`. | Ataca primeiro a regra mais critica do MVP: bloquear envio quando a distribuicao nao fecha 100%. | docs/TESTING.md, tests/test_allocation_closure_contract.py |
| 2026-06-10 | Frontend inicial | assumption | Django server-rendered/templates no MVP. | Inferencia tecnica por simplicidade; ainda nao foi aprovado explicitamente. | docs/ARCHITECTURE.md |
| 2026-06-10 | Papel do coordenador local | needs-user-decision | Responsabilidade detalhada ainda pendente. | A hierarquia inclui o papel, mas o limite entre Regional, Local e Supervisor precisa ser fechado. | docs/PROJECT.md, docs/DATA_MODEL.md |
