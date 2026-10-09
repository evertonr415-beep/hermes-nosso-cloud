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
4. Variáveis não secretas recomendadas: `HERMES_GLOBAL_ROUTER_ENABLED=1`, `HERMES_GLOBAL_KEYLESS_ALLOW=0`, `HERMES_HF_MODEL=Qwen/Qwen3-4B-Instruct-2507`. Alternativa: `Qwen/Qwen2.5-14B-Instruct`.
5. O Space deve publicar a **porta 8080**. Internamente, o gateway/interface do Hermes continua atendendo na porta 9119, com um encaminhamento `socat` habilitado automaticamente por `SPACE_ID`.

## Modelo de IA e limites reais

A API oficial é `https://router.huggingface.co/v1/chat/completions`. O roteador Hermes usa `HF_TOKEN` e faz uma chamada curta de pré-validação antes de alternar o chat principal.

- Modelo inicial: `Qwen/Qwen2.5-7B-Instruct`.
- Alternativa permitida: `Qwen/Qwen2.5-14B-Instruct`.
- A disponibilidade dos modelos e a disponibilidade do serviço de inferência dependem do provedor.
- **Esses modelos não garantem inferência gratuita.** Hugging Face Inference Providers concede apenas créditos mensais limitados a contas gratuitas; HTTP 402 indica cobrança/cota. Não habilite cobrança automaticamente. O modelo anterior é preservado se o preflight falhar.
- O Space Docker gratuito **não carrega os pesos do modelo 7B/14B localmente**: a inferência usa um serviço externo, com suas políticas de disponibilidade e privacidade. Serviços e limites gratuitos podem mudar.

## Persistência e segurança

Um Space gratuito não deve ser tratado como armazenamento persistente do `/opt/data`. Para manter o histórico, dados e memória, restaure explicitamente os segredos/integrações de Supabase ou adicione armazenamento persistente apropriado antes de operar em produção. **Não copie arquivos privados, chaves ou tokens do Railway para o repositório público.** Revogue tokens expostos em mensagens ou logs e gere novos.

Guia oficial: https://huggingface.co/docs/hub/spaces-sdks-docker

---
**Estado:** preparação do repositório para migração. Publicar arquivos no GitHub não cria nem executa um Space automaticamente.

## Render — modo leve (chat)

O modo leve usa a porta `8080` e o modelo `Qwen/Qwen2.5-7B-Instruct` por padrão, sem depender do `s6-overlay` para servir a interface. A alternativa é `Qwen/Qwen2.5-14B-Instruct`, selecionável em `HERMES_HF_MODEL`. Configurar `HF_TOKEN` como segredo no **Render → Environment** (com permissão *Make calls to Inference Providers*) é obrigatório para obter respostas do modelo.

O roteador tenta no máximo duas vezes quando ocorre timeout, limitação temporária de requisições ou indisponibilidade do provedor. **HTTP 401, 402 e 403 não são repetidos**: o chat apresenta um aviso específico, pois trocar o modelo não corrige problemas de credenciais, permissão ou créditos. A página `/health` indica apenas que o servidor está de pé, não que a API do Hugging Face está respondendo.

## Correção de compatibilidade com Inference Providers

O Hermes usa o catálogo oficial `GET https://router.huggingface.co/v1/models` para reconhecer modelos de chat com provedor em estado `live`, com cache de 10 minutos. O padrão de preferência é `Qwen/Qwen3-4B-Instruct-2507`, seguido por modelos Qwen2.5 que constem como disponíveis no catálogo. Para o Qwen3, quando o catálogo confirma `nscale`, a rota utiliza explicitamente `:nscale`.

Se o modelo escolhido for rejeitado com HTTP 400, 404 ou 422, será tentado **no máximo mais um modelo Qwen listado como ativo**. Erros HTTP 401, 402, 403 e 429 não provocam mudança de modelo ou cobrança adicional. O chat mostra o código HTTP exato e o identificador do modelo utilizado, sem mostrar segredos.

O endpoint `/health` confirma apenas que o servidor web iniciou. Ele não prova que o acesso ao modelo, os créditos de inferência ou a memória do Supabase estejam funcionando. Serviços do Hugging Face podem exigir créditos mesmo para modelos open source.

## Render — inferência anônima de texto (LEGADO; não é mais a configuração padrão)

A inicialização leve usa por padrão `HERMES_INFERENCE_MODE=anonymous`, com `HERMES_PUBLIC_ANONYMOUS_ENABLED=1`, enviando **somente o texto digitado no chat** a `https://vireonix.ai/v1/chat/completions` e modelo remoto `auto`. É uma API de terceiros, não relacionada ao Duck.ai ou aos Inference Providers do Hugging Face. Documentação do serviço: https://vireonix.ai/docs.

Não é necessário `HF_TOKEN` no modo anônimo. Mesmo que o token exista no Render, ele **não é enviado ao provedor público** e nenhuma chamada de inferência é feita pelo roteador ao Hugging Face. Para restaurar uma rota autenticada opcional no futuro, use `HERMES_INFERENCE_MODE=auto`; nesse modo, uma resposta HTTP 402 pode encaminhar **somente prompts públicos** para o serviço anônimo (`HERMES_FALLBACK_ON_HF_402=1`). As chamadas falhas não são tratadas como respostas válidas.

**Aviso de privacidade e disponibilidade:** a Vireonix declara acesso sem chave e limites por IP, mas não garante SLA ou continuidade. As mensagens enviadas podem ser processadas e armazenadas de acordo com a política do terceiro. Nunca envie senhas, dados pessoais, informações de trabalho restritas, histórico de memória criptografada ou arquivos confidenciais. O modo leve não faz leitura automática da memória do Supabase. Não há garantia de chat gratuito ilimitado ou estável em produção. `/health` testa apenas o servidor web; a resposta efetiva da API requer teste real depois do deploy.

## Configuração atual do Render — GroqCloud Free

A nova configuração utiliza a API oficial da GroqCloud no **plano Free** e o modelo **qwen/qwen3.8-27b**.
Os limites atualmente documentados para esse modelo são **30 requisições por minuto e 1.000 por dia**, além de limites de tokens. É gratuito dentro da franquia, não ilimitado.

**Para ativar no Render:**
1. Crie uma chave gratuita em https://console.groq.com/keys e mantenha a conta no plano Free, sem ativar Developer/Billing.
2. Adicione a chave como variável secreta GROQ_API_KEY em Render → Environment; não publique a chave no GitHub ou neste chat.
3. Garanta HERMES_INFERENCE_MODE=groq, HERMES_PUBLIC_ANONYMOUS_ENABLED=0 e HERMES_GLOBAL_KEYLESS_ALLOW=0 (padrões da inicialização leve).
4. Faça novo deploy e teste uma mensagem simples.

Endpoint: https://api.groq.com/openai/v1/chat/completions . Modelo padrão: qwen/qwen3.8-27b . Modelo alternativo para configurar manualmente: openai/gpt-oss-20b via HERMES_GROQ_MODEL.
O modo Groq não faz chamadas ao Hugging Face nem à Vireonix. Não usa o HF_TOKEN, não altera plano de cobrança, e devolve erro 429 ao exceder a franquia gratuita.
O texto da mensagem é processado pela Groq. O modo leve não lê memória criptografada do Supabase nem envia chaves da plataforma. Evite incluir dados confidenciais.

Fontes oficiais: https://console.groq.com/docs/openai e https://console.groq.com/docs/rate-limits .
