# Manutencao Da Documentacao

## Objetivo

Manter a documentacao util para pessoas e para IA durante a construcao do sistema de metas.

## Regra Geral

Documentacao deve acompanhar decisoes reais. Evite criar texto especulativo como se fosse regra aprovada.

Use estes status quando necessario:

- `approved`: decisao confirmada pelo usuario.
- `proposed`: proposta tecnica ainda nao aprovada.
- `assumption`: hipotese inferida.
- `needs-user-decision`: pendencia que precisa de decisao humana.

## Quando Atualizar Cada Arquivo

### README.md

Atualize quando:

- houver codigo Django criado;
- comandos de setup/teste/execucao mudarem;
- o objetivo do projeto mudar;
- novos documentos importantes forem adicionados.

### docs/PROJECT.md

Atualize quando:

- regras de negocio mudarem;
- escopo do MVP mudar;
- novo perfil de usuario surgir;
- fluxo de distribuicao/aprovacao mudar.

### docs/ARCHITECTURE.md

Atualize quando:

- stack ou arquitetura mudar;
- apps Django forem criados, removidos ou reorganizados;
- integracoes mudarem;
- estrategia de seguranca/testes/operacao mudar.

### docs/DATA_MODEL.md

Atualize quando:

- modelos Django forem criados ou alterados;
- relacionamentos mudarem;
- invariantes de dados mudarem;
- novas consultas criticas forem identificadas.

### docs/DECISION_LOG.md

Atualize quando:

- uma decisao for tomada;
- uma hipotese virar decisao;
- uma decisao aprovada for substituida;
- uma pendencia importante for aberta.

### docs/TESTING.md

Atualize quando:

- a estrategia de testes mudar;
- novos contratos obrigatorios forem criados;
- o comando de testes mudar;
- surgirem fixtures, mocks ou dependencias de teste relevantes;
- regras de seguranca ou ERP passarem a exigir novos testes.

### AGENTS.md

Atualize quando:

- Codex precisar seguir uma nova regra permanente;
- surgirem comandos seguros reais;
- areas sensiveis mudarem;
- fluxos de trabalho mudarem.

## Auditoria Leve

Antes de encerrar uma mudanca relevante, confira:

- A mudanca contradiz alguma decisao aprovada?
- Alguma hipotese foi escrita como fato?
- `DECISION_LOG.md` precisa de nova linha?
- `AGENTS.md` precisa de regra nova?
- O README ainda ajuda alguem a entrar no projeto?

## Pendencias Documentais Atuais

- Incluir comandos reais depois da criacao do Django.
- Documentar fonte ERP depois de confirmada.
- Criar docs de seguranca, testes e operacao separados se o projeto crescer.
