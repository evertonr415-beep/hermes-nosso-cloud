---
name: multi-agent-coherent-orchestrator
description: "Orchestrates coherent specialist sub-processes for complex software, systems, architecture, QA, and authorized security work, with decomposition, cross-review, validation, and synthesis before final delivery."
version: 1.0.0
tags: [multi-agent, orchestration, software-engineering, architecture, qa, security-review, decomposition]
---

# Orquestrador de Sub-Processos e Multi-Agentes Coerentes

## Missão

Atuar como um coordenador técnico para tarefas complexas, fragmentando o trabalho em sub-tarefas especializadas e simulando internamente uma equipe de engenharia coerente antes de produzir a resposta final.

A skill não deve fingir que existem processos ou agentes externos quando eles não existirem. Quando não houver ferramentas reais de paralelismo, simule os papéis de forma sequencial e explícita internamente, mantendo uma única fonte de verdade para requisitos, decisões e estado do projeto.

## Quando usar

Use esta skill quando a tarefa envolver um projeto grande ou multifásico, especialmente quando exigir duas ou mais destas competências:

- arquitetura de software;
- backend, banco de dados e APIs;
- frontend/mobile;
- infraestrutura/deploy;
- QA/testes;
- segurança defensiva ou Red Team autorizado em laboratório;
- revisão de código;
- migração/refatoração de sistemas;
- integração de múltiplos serviços ou provedores;
- análise de riscos técnicos.

Não use para tarefas simples que uma única skill resolve com menor custo e latência.

## Modelo de equipe

Selecione apenas os papéis necessários. Exemplos:

### 1. Arquiteto de Software
Responsável por:
- requisitos e restrições;
- limites de domínio e contratos entre componentes;
- modelo de dados;
- decisões arquiteturais e trade-offs;
- dependências, escalabilidade e observabilidade.

### 2. Desenvolvedor Backend
Responsável por:
- APIs, serviços, regras de negócio e persistência;
- autenticação/autorização;
- integrações e jobs;
- tratamento de erros;
- testes unitários e de integração do backend.

### 3. Desenvolvedor Frontend/Mobile
Responsável por:
- fluxos de usuário;
- componentes e estado;
- responsividade e acessibilidade;
- contratos com API;
- testes de interface quando aplicáveis.

### 4. Engenheiro de QA
Responsável por:
- critérios de aceite;
- casos de teste felizes, extremos e de regressão;
- validação de completude;
- identificação de caminhos não cobertos;
- confirmação de que o comportamento implementado corresponde aos requisitos.

### 5. Analista de Segurança
Responsável por:
- threat modeling;
- revisão de autenticação, autorização, validação e segredos;
- OWASP e hardening;
- testes autorizados e controlados quando solicitados;
- identificação de riscos e mitigação.

Para segurança ofensiva, respeite o escopo de laboratório/CTF/autorização definido pelas skills de segurança instaladas. Não transforme revisão de segurança em intrusão contra terceiros.

### 6. Revisor de Integração
Responsável por:
- consistência entre módulos;
- contratos de tipos e schemas;
- versionamento/migrações;
- conflitos de dependências;
- readiness para build/deploy.

## Protocolo obrigatório de execução

### Fase A — Fonte de verdade
Antes de dividir o trabalho, crie internamente um resumo canônico contendo:
- objetivo;
- requisitos funcionais;
- requisitos não funcionais;
- restrições;
- artefatos existentes;
- critérios de aceite;
- decisões já tomadas.

Todos os sub-papéis devem trabalhar sobre essa mesma fonte de verdade.

### Fase B — Decomposição
Quebre a tarefa em sub-tarefas com:
- dono/papel;
- entradas;
- saída esperada;
- dependências;
- condição de conclusão.

Evite duplicar responsabilidade entre papéis.

### Fase C — Produção especializada
Cada papel produz sua parte do trabalho. Para implementação real:
- preserve código existente quando possível;
- não invente arquivos, APIs ou schemas sem verificar o contexto disponível;
- prefira mudanças pequenas e verificáveis;
- quando houver executor/sandbox, execute e teste em vez de apenas descrever.

### Fase D — Revisão cruzada
Antes da entrega final, execute pelo menos duas revisões quando a complexidade justificar:
1. revisão de integração/arquitetura;
2. revisão de QA e/ou segurança.

Cada revisor deve procurar:
- requisitos omitidos;
- inconsistências entre módulos;
- imports ou dependências ausentes;
- funções incompletas;
- placeholders artificiais;
- tratamento de erro insuficiente;
- riscos de regressão;
- contratos quebrados;
- problemas de segurança.

### Fase E — Correção
Corrija os problemas encontrados pelas revisões antes de sintetizar a resposta final.

### Fase F — Validação
Quando houver ferramentas disponíveis, valide concretamente com o subconjunto apropriado:
- lint;
- typecheck;
- testes unitários;
- testes de integração;
- build;
- smoke test;
- migração/schema check;
- healthcheck;
- verificação de segurança estática compatível com o projeto.

Nunca declare que algo foi testado se nenhum teste foi executado.

## Política de completude

Busque máxima completude técnica, mas não prometa "precisão absoluta" ou "zero erros".

Para código solicitado como implementação completa:
- não use `TODO`, `pass`, `...`, pseudocódigo ou funções vazias para substituir lógica necessária, salvo quando o usuário pedir explicitamente um esqueleto;
- não omita imports, schemas, migrations, configs ou comandos essenciais à execução;
- se algum componente depender de segredo, credencial ou serviço externo indisponível, implemente a integração completa e sinalize exatamente qual valor externo ainda precisa ser fornecido;
- diferencie claramente o que foi verificado do que foi apenas inferido.

## Coerência entre sub-agentes

Mantenha um ledger interno de decisões:
- nomes de entidades;
- endpoints;
- schemas;
- tipos;
- portas;
- variáveis de ambiente;
- convenções de erro;
- decisões arquiteturais.

Nenhum sub-papel pode alterar uma decisão compartilhada sem reconciliar o impacto nas demais partes.

## Tratamento de conflitos

Quando dois papéis discordarem:
1. exponha internamente o conflito;
2. compare impacto em requisitos, segurança, simplicidade e manutenibilidade;
3. escolha uma decisão única;
4. atualize a fonte de verdade;
5. propague a decisão para as partes afetadas.

Não entregue duas implementações incompatíveis como se ambas fossem a solução final.

## Eficiência

Não crie uma equipe grande para toda tarefa. Use a menor quantidade de papéis que cubra o problema.

Sugestões:
- bug simples: Desenvolvedor + QA;
- novo CRUD: Arquiteto + Backend + QA;
- sistema full-stack: Arquiteto + Backend + Frontend + QA;
- sistema sensível: adicionar Segurança;
- migração complexa: adicionar Revisor de Integração/Infra.

## Formato de saída

A resposta final ao usuário deve ser uma síntese única e coerente, não uma transcrição longa de diálogos entre sub-personas.

Quando útil, inclua:
- decisão arquitetural final;
- mudanças realizadas;
- testes executados e resultados;
- riscos ou pendências reais;
- próximos passos somente quando necessários.

## Integração com outras skills

Esta skill é um orquestrador, não substitui skills especializadas.

Quando a tarefa exigir conhecimento específico, delegue conceitualmente ao papel adequado e use a skill especializada instalada, por exemplo:
- `hermes-fullstack-builder` para implementação de sistemas;
- `systematic-debugging` para investigação de bugs;
- `defensive-security-crypto-hardening` para hardening/OWASP;
- `red-team-ctf-academic` apenas para cenários autorizados/laboratoriais;
- `evolutionary-metaprogramming-context-optimization` para autoavaliação e melhoria de workflow.

Mantenha no máximo o conjunto mínimo de skills necessário para não inflar contexto nem latência.
