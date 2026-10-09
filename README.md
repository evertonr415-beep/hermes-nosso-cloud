---
title: Hermes-Nosso-Cloud
emoji: 🤖
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8080
---

# Hermes Nosso Cloud — preparado para Hugging Face Spaces

Este repositório mantém o **Hermes Cloud** (agente e gateway) e sua **interface web integrada**. A imagem `Dockerfile` usa o Hermes existente e publica a interface integrada em `0.0.0.0:8080` no Hugging Face Spaces. Não utiliza Railway para executar o Space.

> **Importante:** o serviço Railway separado chamado `hermes-web` **não é iniciado** por este único contêiner. A interface web disponibilizada aqui é a do próprio Hermes Cloud. Migrar a interface separada, com seus recursos específicos, exigirá uma segunda implantação ou integração posterior.

## Criar um Docker Space

1. Crie um novo Space em https://huggingface.co/new-space, selecione **Docker**, e configure-o como **Private** caso trate informações pessoais.
2. Envie os arquivos deste repositório para o **repositório Git do Space** (um commit no GitHub, sozinho, não inicia deploy no HF). Mantenha o `README.md` com o bloco YAML acima e o `Dockerfile` na raiz.
3. Em **Settings → Variables and secrets**, crie os segredos necessários. Nunca os salve no GitHub:
   - `HF_TOKEN`: token com permissão para Inference Providers;
   - `HERMES_DASHBOARD_BASIC_AUTH_PASSWORD` / demais configurações de acesso exigidas pelo Hermes;
   - `HERMES_MEMORY_AES_KEY`, `HERMES_MEMORY_SYNC_TOKEN`, `HERMES_MEMORY_SYNC_URL` se quiser restaurar a sincronização privada de memória Supabase com as **mesmas chaves antigas**;
   - Demais credenciais de integrações que você efetivamente usar.
4. Variáveis não secretas recomendadas: `HERMES_GLOBAL_ROUTER_ENABLED=1`, `HERMES_GLOBAL_KEYLESS_ALLOW=0`, `HERMES_HF_MODEL=meta-llama/Llama-3.1-8B-Instruct`. Alternativa: `Qwen/Qwen2.5-14B-Instruct`.
5. O Space deve publicar a **porta 8080**. Internamente, o gateway/interface do Hermes continua atendendo na porta 9119, com um encaminhamento `socat` habilitado automaticamente por `SPACE_ID`.

## Modelo de IA e limites reais

A API oficial é `https://router.huggingface.co/v1/chat/completions`. O roteador Hermes usa `HF_TOKEN` e faz uma chamada curta de pré-validação antes de alternar o chat principal.

- Modelo inicial: `meta-llama/Llama-3.1-8B-Instruct`.
- Alternativa permitida: `Qwen/Qwen2.5-14B-Instruct`.
- A disponibilidade dos modelos e a eventual aprovação de licença de acesso dependem do provedor.
- **Esses modelos não garantem inferência gratuita.** Hugging Face Inference Providers concede apenas créditos mensais limitados a contas gratuitas; HTTP 402 indica cobrança/cota. Não habilite cobrança automaticamente. O modelo anterior é preservado se o preflight falhar.
- O Space Docker gratuito **não carrega os pesos do modelo 8B/14B localmente**: a inferência usa um serviço externo, com suas políticas de disponibilidade e privacidade. Serviços e limites gratuitos podem mudar.

## Persistência e segurança

Um Space gratuito não deve ser tratado como armazenamento persistente do `/opt/data`. Para manter o histórico, dados e memória, restaure explicitamente os segredos/integrações de Supabase ou adicione armazenamento persistente apropriado antes de operar em produção. **Não copie arquivos privados, chaves ou tokens do Railway para o repositório público.** Revogue tokens expostos em mensagens ou logs e gere novos.

Guia oficial: https://huggingface.co/docs/hub/spaces-sdks-docker

---
**Estado:** preparação do repositório para migração. Publicar arquivos no GitHub não cria nem executa um Space automaticamente.
