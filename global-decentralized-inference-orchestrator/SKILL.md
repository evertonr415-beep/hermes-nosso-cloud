---
name: global-decentralized-inference-orchestrator
description: "Orquestra inferência de IA global entre provedores e nós autorizados, com roteamento por latência, custo, saúde, privacidade e capacidade, sem autoaprovisionamento irrestrito."
version: 1.0.0
tags: [global-inference, decentralized, depin, multi-cloud, serverless, routing, failover, open-models, security]
---

# Orquestrador de Inferência Global Descentralizada

## Missão

Operar como camada de roteamento de inferência para o Hermes Nosso, selecionando dinamicamente o melhor backend de IA disponível entre provedores e nós previamente autorizados pelo proprietário.

O objetivo é reduzir dependência de um único provedor, melhorar disponibilidade global e permitir uso de modelos abertos/self-hosted quando houver infraestrutura autorizada.

## Limites operacionais obrigatórios

- Nunca criar contas, adquirir recursos, movimentar fundos, usar carteiras, minerar, requisitar GPUs, abrir nós, ou consumir serviços pagos sem autorização explícita do proprietário.
- Nunca "colonizar" recursos de terceiros, redes ociosas, hosts desconhecidos ou infraestrutura sem permissão.
- Nunca desabilitar auditoria, limites de custo, segurança, rate limits ou controles de identidade.
- Não alegar independência total de APIs se a infraestrutura disponível ainda depender de credenciais ou serviços externos.
- Toda conexão externa deve usar provedores configurados e credenciais fornecidas/autorizadas pelo proprietário.
- Preferir open-source/self-hosted quando houver capacidade disponível, mas usar APIs comerciais somente quando explicitamente configuradas.
- Falhas devem degradar de forma segura; não executar retry storms.

## Backends suportados conceitualmente

A skill pode rotear entre backends configurados como:

- OpenAI-compatible endpoints;
- vLLM self-hosted;
- llama.cpp/Ollama;
- Hugging Face Inference Providers/Endpoints;
- Together AI;
- Akash workloads expostos por endpoint privado/público autorizado;
- Render/Railway/Vercel apenas quando o workload for compatível;
- provedores regionais equivalentes.

Cada backend deve ser representado por configuração declarativa, nunca por credenciais hardcoded em código ou skill.

## Registro de provedores

Modelo de configuração:

```yaml
providers:
  edge_local:
    type: openai_compatible
    base_url: http://ollama:11434/v1
    models:
      - llama3.2:1b
    privacy: local
    cost_class: zero
    regions: [local]

  regional_vllm:
    type: openai_compatible
    base_url: ${VLLM_BASE_URL}
    api_key_env: VLLM_API_KEY
    models:
      - open-model
    privacy: private
    cost_class: reserved
    regions: [south-america]

  hf_serverless:
    type: huggingface
    token_env: HF_TOKEN
    models:
      - configured-model
    privacy: external
    cost_class: metered
    regions: [global]
```

Se a credencial/endpoint não existir, o backend é considerado indisponível.

## Health model

Cada backend deve manter telemetria:

- healthy/unhealthy;
- TTFB;
- p50/p95/p99;
- tokens/s;
- taxa de erro;
- taxa 429;
- custo estimado;
- fila/concurrency;
- região;
- contexto máximo;
- modalidades;
- nível de privacidade;
- última verificação.

## Roteamento

Calcular score por requisição:

```text
score =
  w_health    * health
+ w_latency   * latency_score
+ w_quality   * quality_score
+ w_privacy   * privacy_score
+ w_capacity  * capacity_score
- w_cost      * estimated_cost
- w_failure   * recent_failure_rate
```

O score deve ser auditável. Nunca alterar pesos silenciosamente.

## Classes de execução

### EDGE_FAST
Use para:
- classificação;
- parsing;
- extração;
- sumarização curta;
- tarefas repetitivas;
- fallback offline.

### REGIONAL_STANDARD
Use para:
- chat normal;
- tarefas de código moderadas;
- RAG;
- respostas multimodais leves.

### CENTRAL_REASONING
Use para:
- arquitetura complexa;
- código grande;
- análise longa;
- planejamento multi-etapa.

### SPECIALIST
Use para:
- visão;
- imagem;
- áudio;
- embeddings;
- reranking;
- code model;
- modelos especializados.

## Política de fallback

1. tentar o melhor backend saudável;
2. se timeout/429/5xx, registrar falha;
3. usar no máximo 1 fallback imediato;
4. se o fallback falhar, degradar para modo local/limitado quando possível;
5. informar indisponibilidade se nenhum backend autorizado estiver saudável.

Nunca fazer loops de retries ilimitados.

## Segurança de rede

- TLS 1.3 quando disponível;
- mTLS entre serviços privados;
- egress allowlist;
- DNS validado;
- timeouts explícitos;
- certificate pinning apenas quando operacionalmente sustentável;
- rotação de credenciais;
- chaves via secret store, nunca em prompts/logs.

## Integração com Hermes

Quando o usuário pedir uma tarefa:
1. classifique a classe de execução;
2. consulte backends disponíveis;
3. aplique regras de privacidade/custo;
4. selecione o backend;
5. registre decisão;
6. execute;
7. grave latência, erro, custo e fallback.

## Auditoria mínima por requisição

Registrar:
- request_id;
- classe;
- backend/modelo selecionado;
- região;
- TTFB;
- duração;
- tokens;
- custo estimado;
- fallback;
- status final.

Nunca registrar segredos nem payloads sensíveis completos.

## Evolução controlada

A skill pode sugerir novos provedores, regiões ou modelos com base em telemetria, mas não pode provisioná-los automaticamente sem autorização explícita do proprietário.

Para mudanças de produção:
- gerar diff;
- testar em sandbox;
- medir;
- pedir/promover via gate;
- manter rollback.

## Resultado esperado

Hermes deve operar como um roteador resiliente, multi-provider e multi-region, reduzindo single points of failure sem perder controle humano, segurança, rastreabilidade ou limites financeiros.
