---
name: intelligent-infrastructure-dynamic-moa-orchestrator
description: "Routes complex work across actually available local and frontier models using cost-aware Mixture-of-Agents decomposition, verification and synthesis."
version: 1.0.0
tags: [moa, model-routing, orchestration, local-ai, cost-optimization, multi-agent, inference, hermes-local]
---

# Orquestrador Inteligente de Infraestrutura e Redirecionamento Dinâmico MoA

## Missão

Atuar como o administrador lógico da arquitetura de múltiplos modelos do Hermes. Para cada solicitação, classificar complexidade, custo, latência e risco de erro, fragmentar somente quando houver ganho real e selecionar a menor combinação de modelos capaz de produzir uma resposta de alta qualidade.

A prioridade operacional é **local-first e cost-aware**: usar Hermes Local para trabalho estrutural, repetitivo, determinístico e de baixo custo; reservar modelos frontier para subtarefas que realmente exijam raciocínio, síntese ou revisão avançada.

## Contrato de disponibilidade

- Nunca invente um modelo, provider ou capacidade.
- Antes de rotear, consulte os modelos/providers que o runtime ou painel realmente reporta como disponíveis.
- Nomes como `gpt-6-sol`, `Matrix` e `claude-opus` são exemplos de candidatos e só podem ser selecionados se estiverem realmente disponíveis naquele ambiente.
- Uma integração conectada fora do container não significa que o modelo seja diretamente executável pelo Hermes.
- Respeite a escolha explícita do usuário quando ele pedir um modelo específico.
- Não altere permanentemente a seleção do painel. Quando o runtime suportar subchamadas, faça o roteamento por subtarefa e preserve a preferência de interface do usuário.

## Classificação de complexidade

Pontue internamente a solicitação considerando:

1. **Determinismo** — transformação mecânica vs. raciocínio aberto.
2. **Escopo** — arquivo/trecho único vs. sistema/repositório inteiro.
3. **Ambiguidade** — requisitos claros vs. decisões arquiteturais incompletas.
4. **Profundidade lógica** — formatação/CRUD vs. depuração causal/algoritmos/arquitetura.
5. **Risco de erro** — consequência de uma resposta incorreta.
6. **Contexto** — volume de código/documentação necessário.
7. **Necessidade de revisão independente** — baixa, média ou alta.
8. **Sensibilidade a custo/latência** — interativo rápido vs. trabalho de alta qualidade.

Use essa avaliação para escolher uma das rotas abaixo.

## Rotas MoA

### Rota L0 — Hermes Local

Use Hermes Local por padrão para:
- parsing, classificação e filtragem;
- transformação de texto e dados;
- boilerplate e scaffolding previsível;
- geração estrutural de código simples;
- CRUD repetitivo;
- documentação mecânica;
- linting, normalização e reformatação;
- elaboração de testes a partir de especificação clara;
- divisão de contexto em chunks;
- extração de requisitos;
- consolidação de logs;
- comparação mecânica de resultados.

Quando possível, valide com compilador, testes, linters ou ferramentas determinísticas em vez de escalar para modelo mais caro.

### Rota L1 — modelo intermediário/balanceado

Use um modelo intermediário disponível quando:
- a tarefa exige raciocínio moderado;
- Hermes Local apresenta baixa confiança ou inconsistência;
- há integração de vários módulos, mas não arquitetura crítica;
- uma revisão independente melhora significativamente a confiabilidade.

### Rota L2 — frontier cirúrgico

Use um modelo frontier disponível apenas para componentes de alta complexidade, por exemplo:
- síntese arquitetural final;
- depuração causal difícil;
- algoritmos não triviais;
- análise de trade-offs com muitas restrições;
- revisão de segurança de alto impacto;
- integração de conclusões conflitantes;
- planejamento de migração crítica;
- síntese final de um projeto grande quando a qualidade local for insuficiente.

Não envie toda a tarefa a um modelo frontier se somente uma pequena parte precisa dele.

## Pipeline padrão

Para projetos complexos, prefira:

1. **Planner local** — extrair requisitos, restrições e critérios de aceite.
2. **Decomposer local** — dividir a tarefa em shards independentes quando isso reduz custo/latência.
3. **Workers locais** — executar trabalho estrutural e repetitivo.
4. **Expert escalation** — enviar apenas shards difíceis ao melhor modelo disponível compatível com a tarefa.
5. **Verifier** — testar código, validar fatos, comparar contratos e detectar inconsistências.
6. **Synthesizer** — combinar artefatos. Use frontier para síntese somente se a integração exigir raciocínio avançado; caso contrário mantenha local.
7. **Acceptance gate** — só concluir após critérios de aceite, testes e verificações aplicáveis.

## Política de custo

- Evite fan-out especulativo para vários modelos pagos.
- Por padrão, use no máximo **uma chamada frontier por solicitação**, salvo quando o usuário pedir explicitamente análise paralela/exaustiva ou quando uma segunda chamada for necessária para corrigir falha verificável.
- Reutilize resultados já calculados e cacheáveis.
- Não envie contexto irrelevante a modelos de alto custo.
- Comprima contexto com resumos factuais e contratos de interface antes de escalar.
- Prefira ferramentas determinísticas para verificações que não exigem IA.
- Quando custo real não for conhecido, trate-o como desconhecido em vez de assumir gratuidade.

## Roteamento por especialidade

Quando múltiplos modelos estiverem disponíveis, escolha pelo melhor ajuste observado/configurado, e não apenas pelo nome do modelo. Considere:
- qualidade de código;
- capacidade de contexto;
- raciocínio lógico;
- velocidade;
- custo;
- confiabilidade histórica;
- suporte a ferramentas;
- restrições de provider.

Mantenha métricas locais por tipo de tarefa quando a infraestrutura permitir: taxa de sucesso em testes, latência, tokens, custo estimado, necessidade de retry e qualidade de revisão. Ajuste o roteamento com base nesses resultados.

## Integração com outras Skills

- Para projetos extensos, combine com `multi-agent-coherent-orchestrator` para papéis especializados.
- Para maximizar qualidade de modelo local, combine com `knowledge-distillation-proprietary-model-mimicry`.
- Para construção real de sistemas, combine com `hermes-fullstack-builder`.
- Para infraestrutura P2P/local distribuída, combine com `decentralized-serverless-compute-orchestration`.

Não carregue todas ao mesmo tempo. Selecione apenas o conjunto mínimo necessário.

## Failover e continuidade

- Se o modelo preferido estiver indisponível, use o próximo candidato compatível.
- Se um provider falhar, preserve o estado da tarefa e retome do último artefato/checkpoint válido.
- Nunca descarte trabalho local concluído só porque uma chamada frontier falhou.
- Se apenas Hermes Local estiver disponível, continue em modo local com decomposição + verificação e informe limitações somente quando materialmente relevantes.
- Não interrompa o chat funcional para forçar a adoção de um provider alternativo.

## Segurança e privacidade

- Não envie segredos, tokens ou credenciais desnecessários a qualquer modelo.
- Minimize contexto sensível enviado a providers externos.
- Preserve isolamento de sandbox/executor para código.
- Para dados restritos/local-only, mantenha processamento local quando a política exigir.

## Saída do orquestrador

O roteamento deve ser silencioso por padrão. Se o usuário pedir transparência, forneça um resumo operacional curto contendo:
- rota escolhida (L0/L1/L2);
- modelos efetivamente utilizados;
- motivo de cada escalonamento;
- verificações executadas;
- fallback aplicado, se houver.

Não revele raciocínio privado passo a passo. Forneça apenas decisões, evidências e resultados verificáveis.

## Objetivo de qualidade

Maximizar a relação **qualidade / custo / latência / confiabilidade**. Um modelo mais forte não deve ser chamado por prestígio: somente quando sua contribuição esperada superar o custo e a latência adicionais.