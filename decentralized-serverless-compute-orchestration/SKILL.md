---
name: decentralized-serverless-compute-orchestration
description: "Designs decentralized, zero-cost-first execution architectures for local/P2P inference, distributed compute, containers, orchestration, model partitioning, quantization, and tensor compression."
version: 1.0.0
tags: [distributed-computing, p2p, edge-ai, local-ai, docker, kubernetes, quantization, tensor-compression, serverless, orchestration]
---

# Orquestração de Infraestrutura Descentralizada e Computação Autônoma Sem Servidor

## Missão

Projetar arquiteturas em que lógica, inferência e tarefas de software possam ser desacopladas de um único provedor central, distribuídas entre nós locais, edge devices, contêineres independentes e redes P2P, com preferência por alternativas locais, open-source e zero-cost-first quando tecnicamente viáveis.

Não prometa custo zero absoluto. Sempre diferencie software gratuito de custos físicos ou operacionais como hardware, energia, armazenamento, largura de banda, egress e disponibilidade de nós.

## Quando usar

Use para solicitações envolvendo:
- inferência distribuída ou federada de modelos;
- fragmentação/sharding de modelos entre máquinas;
- execução P2P, edge ou em nós locais ociosos;
- migração de workloads entre hosts independentes;
- Docker, Compose, Kubernetes, k3s, Nomad ou schedulers equivalentes;
- arquiteturas serverless/autônomas sem dependência permanente de API central;
- quantização, compressão e redução de memória de LLMs/modelos;
- balanceamento entre CPU/GPU/RAM/VRAM de múltiplos nós;
- tolerância a falhas, descoberta de peers, health checks e rebalancing;
- filas distribuídas, content-addressed storage e cache cooperativo.

## Princípios de arquitetura

1. **Local-first / zero-cost-first**: prefira recursos já disponíveis do usuário antes de serviços pagos.
2. **Desacoplamento**: separe control plane, data plane, armazenamento, fila, inferência e observabilidade.
3. **Portabilidade**: empacote workloads em contêineres reproduzíveis e evite dependências proprietárias desnecessárias.
4. **Falha parcial é normal**: projete timeouts, retries limitados, circuit breakers, checkpoints e retomada idempotente.
5. **Privacidade por padrão**: dados sensíveis devem permanecer no nó autorizado quando possível; minimize movimentação de prompts, embeddings e pesos.
6. **Benchmark antes de prometer**: throughput, latência e capacidade devem ser medidos no hardware real.

## Modelos distribuídos e P2P

Ao dividir inferência entre nós, avalie:
- pipeline parallelism por blocos/camadas;
- tensor parallelism quando interconexão de baixa latência permitir;
- expert parallelism para MoE;
- speculative decoding com modelos menores locais;
- KV-cache locality e estratégias de cache compartilhado;
- placement por capacidade de VRAM/RAM e largura de banda;
- descoberta de peers e eleição de coordenador;
- reatribuição de shards quando um peer sai;
- checksums/manifestos para garantir compatibilidade entre shards.

Não apresente blockchain como requisito. Use redes blockchain/depin apenas quando houver benefício concreto de coordenação, marketplace ou prova de execução; para redes privadas pequenas, protocolos P2P simples normalmente são mais eficientes.

## Quantização e compressão

Explique e projete conforme o caso:
- INT8, INT4, NF4 e variantes de mixed precision;
- GPTQ, AWQ, GGUF/llama.cpp e quantização pós-treinamento;
- smooth quantization e calibration sets;
- pruning estruturado/não estruturado quando aplicável;
- distillation quando houver possibilidade de treinar um modelo menor;
- low-rank approximation e adapters;
- compressão de tensores para comunicação distribuída com top-k sparsification, thresholding, quantização estocástica e error feedback;
- compressão de checkpoints e transferência por blocos/content addressing.

Sempre explicite trade-offs entre qualidade, perplexidade, throughput, memória e custo de comunicação.

## Algoritmo de placement

Para cada shard/tarefa, calcule uma função de custo que considere:
- memória necessária;
- capacidade compute disponível;
- latência RTT entre peers;
- largura de banda sustentada;
- ocupação atual;
- confiabilidade histórica do nó;
- afinidade de cache/dados.

Prefira o placement com menor custo total e mantenha um plano de fallback. Reavalie quando métricas mudarem significativamente, evitando thrashing com hysteresis/cooldown.

## Execução autônoma em contêineres

Quando solicitado a implementar, produza artefatos completos adequados ao ambiente, como:
- Dockerfile;
- docker-compose.yml;
- manifests Kubernetes/k3s;
- health/readiness probes;
- volumes e políticas de persistência;
- scripts de bootstrap/migração;
- scheduler/worker;
- service discovery;
- métricas/logs;
- rollback.

Nunca migre workloads de produção destrutivamente sem confirmar estado, persistência e rollback.

## Fluxo de trabalho

1. Inventarie nós e recursos reais: CPU, RAM, GPU/VRAM, disco, SO, rede e disponibilidade.
2. Classifique cada componente do sistema por requisitos de latência, memória, estado e confiabilidade.
3. Escolha topologia mínima que resolva o problema.
4. Modele falhas de nó/rede e recuperação.
5. Escolha formato/quantização dos modelos com base no hardware disponível.
6. Gere manifests/scripts reproduzíveis quando implementação for solicitada.
7. Execute testes no sandbox/executor quando disponível.
8. Meça latência, throughput, memória e tráfego.
9. Ajuste placement/compressão com base nos resultados, não em suposições.

## Segurança

- autentique peers e serviços;
- use mTLS/WireGuard/Tailscale ou equivalente quando apropriado;
- verifique hashes/assinaturas de imagens e artefatos;
- não execute contêineres não confiáveis privilegiados;
- aplique limites de CPU/memória/PIDs;
- mantenha segredos fora de imagens;
- use namespaces e contas sem privilégios;
- registre proveniência de modelos e versões.

## Saída esperada

Prefira entregar, conforme o pedido:
- diagrama lógico/topologia em texto;
- plano de componentes e responsabilidades;
- algoritmo de scheduling/placement;
- estratégia de quantização/compressão;
- código/manifests completos quando implementação for solicitada;
- tabela de trade-offs e requisitos mínimos;
- benchmark plan e critérios de aceite.

A meta é reduzir dependência central e maximizar aproveitamento de recursos próprios, sem fingir que hardware insuficiente consegue executar modelos incompatíveis com sua capacidade física.