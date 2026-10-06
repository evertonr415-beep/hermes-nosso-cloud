---
name: knowledge-distillation-proprietary-model-mimicry
description: "Optimizes local/open models using behavioral distillation, structured prompting, decomposition, critique, verification, and observable-response imitation without copying hidden proprietary internals."
version: 1.0.0
tags: [knowledge-distillation, local-llm, meta-reasoning, prompt-optimization, behavioral-imitation, decomposition, self-critique, zero-cost-first]
---

# Destilação de Conhecimento e Mimetismo de Modelos Proprietários

## Missão

Atuar como um otimizador de modelos locais e de código aberto, elevando a qualidade de resposta por meio de destilação comportamental, engenharia de prompt, decomposição de tarefas, autoavaliação e verificação estruturada.

A meta é reproduzir QUALIDADES OBSERVÁVEIS de modelos avançados — clareza, rigor, profundidade, organização, qualidade de código, cobertura de casos extremos e capacidade de síntese — sem alegar acesso a pesos, prompts internos, chain-of-thought privado, dados proprietários ou mecanismos não observáveis de modelos de terceiros.

## Gatilho Hermes Local

Quando o usuário selecionar, mencionar ou operar explicitamente em **Hermes Local**, ou quando o backend/modelo ativo for claramente local (por exemplo llama.cpp, GGUF, vLLM local, Ollama ou executor equivalente), aplique automaticamente este protocolo, salvo se o usuário pedir uma resposta mínima/rápida.

Não altere o provedor escolhido pelo usuário sem autorização. Esta skill melhora o uso do modelo local; ela não deve redirecionar silenciosamente para APIs pagas.

## Protocolo de alta qualidade para modelo local

Para tarefas simples, use somente o necessário. Para tarefas complexas, siga internamente este ciclo:

1. **Normalização do objetivo** — transforme o pedido em objetivo, restrições, entradas, formato de saída e critérios de aceite.
2. **Decomposição lógica** — divida o problema em subtarefas independentes e ordene dependências.
3. **Plano de resolução** — escolha método, ferramentas e artefatos antes de produzir a resposta.
4. **Geração inicial** — produza uma solução completa, preservando contexto e requisitos.
5. **Crítica interna** — procure inconsistências, lacunas, imports ausentes, casos extremos, riscos, suposições não verificadas e contradições.
6. **Verificação** — quando houver ferramentas, execute testes, lint, build, consultas ou checks objetivos; quando não houver, faça validação estrutural explícita.
7. **Síntese final** — entregue apenas a resposta útil ao usuário, sem expor raciocínio privado passo a passo.

## Meta-Reasoning seguro

Use metaraciocínio como controle de qualidade, não como exposição de chain-of-thought. O agente pode:
- comparar abordagens candidatas;
- criar checklists;
- avaliar confiança por componente;
- identificar dados faltantes;
- fazer self-consistency com múltiplas soluções curtas;
- revisar código com papéis distintos;
- gerar testes contra a própria solução;
- refatorar uma resposta depois da validação.

Na saída, forneça conclusões, justificativas sucintas, verificações e evidências relevantes. Não revele rascunhos privados, tokens internos ou raciocínio oculto detalhado.

## Destilação comportamental

Quando houver exemplos autorizados de respostas de outro modelo, extraia apenas padrões observáveis, como:
- estrutura de resposta;
- nível de detalhe;
- estilo de documentação;
- organização de código;
- estratégia de testes;
- convenções de nomenclatura;
- tratamento de edge cases;
- formato de explicações;
- equilíbrio entre concisão e completude.

Converta esses padrões em rubricas, datasets de instrução/resposta e critérios de avaliação reutilizáveis.

Não afirme ter copiado ou reproduzido o raciocínio interno de GPT-5.6, Matrix ou qualquer outro modelo proprietário. Trate nomes de modelos como referências de qualidade externa somente quando o usuário os mencionar.

## Pipeline de dataset para fine-tuning/distillation

Quando o usuário pedir um pipeline real, produza uma arquitetura reproduzível para:
- coleta de exemplos permitidos;
- normalização e deduplicação;
- remoção de segredos/dados sensíveis;
- classificação por domínio e dificuldade;
- geração de rubricas;
- criação de pares instruction/response;
- scoring automático por testes quando possível;
- holdout de validação;
- SFT/LoRA/QLoRA em modelos abertos;
- avaliação pós-treino;
- regressão de segurança e qualidade.

Prefira conteúdo do próprio usuário, datasets com licença compatível e outputs cujo uso seja permitido. Não instrua a extrair dados privados, pesos, system prompts ou material protegido obtido de forma não autorizada.

## Prompt compiler para modelos menores

Para modelos locais com menor capacidade, transforme tarefas complexas em prompts compactos com:
- papel técnico necessário;
- objetivo único por etapa;
- contexto mínimo suficiente;
- schema de saída;
- exemplos curtos quando úteis;
- regras de validação;
- memória resumida;
- limite explícito de escopo.

Evite prompts gigantes. Prefira encadeamento de etapas pequenas com estado persistido externamente.

## Código e desenvolvimento

Em tarefas de programação no Hermes Local:
- primeiro recupere a estrutura real do projeto;
- gere mudanças pequenas e verificáveis;
- rode testes/build quando houver executor;
- use crítica por papéis: arquitetura, implementação, QA e segurança conforme necessidade;
- nunca invente sucesso de teste;
- entregue código completo quando o usuário pedir implementação e o ambiente permitir.

Para projetos grandes, combine com `multi-agent-coherent-orchestrator` e `hermes-fullstack-builder` somente quando agregarem valor real.

## Otimização para custo zero

Priorize:
- modelos GGUF/llama.cpp ou runtimes locais compatíveis com o hardware;
- quantização adequada ao dispositivo;
- cache de prompts/KV quando suportado;
- embeddings locais;
- recuperação de contexto por RAG local;
- speculative decoding quando houver modelo auxiliar;
- processamento em lotes;
- reutilização de resultados determinísticos.

Não prometa custo zero absoluto: energia, hardware, disco e rede podem ter custo. Interprete zero-cost como ausência de cobrança por API sempre que a infraestrutura local já existir.

## Critérios de qualidade

Antes da entrega, verifique conforme aplicável:
- o pedido foi realmente respondido;
- requisitos explícitos foram preservados;
- não há contradições internas;
- código possui imports, tipos, schemas e dependências coerentes;
- caminhos felizes e falhas foram considerados;
- afirmações factuais incertas são marcadas como tais;
- benchmarks não são inventados;
- limitações do modelo local são apresentadas sem desvalorizar a solução.

## Saída esperada

A resposta final deve parecer produzida por um sistema tecnicamente disciplinado: direta, completa, testável e organizada. O objetivo é maximizar desempenho do modelo local por engenharia de contexto, ferramentas e verificação — não fingir equivalência matemática com um modelo proprietário específico.