# Hermes Nosso — pacote de transferência

Branch de handoff: `handoff-2026-09-30`

Esta branch existe para migrar o projeto para outra plataforma e continuar o desenvolvimento sem depender do histórico da conversa.

## Componentes

### 1. hermes-cloud
- Dockerfile: `Dockerfile`
- Base: `nousresearch/hermes-agent:latest`
- Dashboard: porta 9119
- API OpenAI-compatible: porta 8642
- Persistência obrigatória: `/opt/data`
- Mantém config, memória, sessões, skills, auth e estado do Hermes.

### 2. hermes-web / Hermes Simples
- Dockerfile: `Dockerfile.simple`
- App: `hermes-simple.py`
- Porta: 9119
- Interface simplificada estilo chat.
- Conversa com o backend por meio do bridge.
- O painel avançado permanece no hermes-cloud.

### 3. bridge
- Dockerfile: `Dockerfile.bridge`
- App: `bridge.py`
- Porta: 9120
- Faz a ponte autenticada entre Hermes Simples e a API do hermes-cloud.

### 4. gateway Tailscale opcional
- Dockerfile: `Dockerfile.tailscale-gateway`
- Proxy: `tailscale-gateway-proxy.py`
- Startup: `start-tailscale-gateway.sh`
- Porta interna: 8642
- Volume persistente: `/var/lib/tailscale`
- Serve para alcançar um Hermes local/ComfyUI/terminal em uma Tailnet sem expor o computador à internet.

## Arquivos importantes

- `railway-entrypoint.sh`: inicialização e configuração persistente do Hermes Cloud.
- `patch-hermes-web-runtime.py`: compatibilidade/recovery do dashboard avançado.
- `custom-skills.tar.gz.b64`: skills adicionais empacotadas.
- `smoke-tests.sh`, `runtime-smoke-run.sh`, `cron-validation-run.sh`: validações.
- `bucket-backup.py` e `bucket-backup-run.sh`: backup.
- `hermes-simple.py`: frontend/backend leve do chat simples.
- `bridge.py`: bridge OpenAI-compatible/MCP.
- `Dockerfile.webpreview`, `hermes-desktop-theme.css`, `hermes-desktop-brand.js`, `hermes-preview-nginx.conf`, `start-web-preview.sh`: experimentos de visual Desktop existentes na branch `desktop-web-preview`.

## Estado de referência no momento do handoff

- Backend principal: branch `main`, referência `b642c0ff4a60e52d7df149b8e8ba7b08bc8ca86e`.
- Bridge validado: commit `d0f2e88735d9d507ab1e46c8fc7ae19ef038a5c2`.
- Hermes Simples que estava sendo testado/deployado: branch `desktop-web-preview`.
- A interface simples utiliza Basic Auth e bridge autenticado.
- O volume `/opt/data` é crítico e nunca deve ser apagado durante migração.

## Modelos/providers

A configuração foi preparada para:
- OpenAI/GPT como principal/fallback conforme `railway-entrypoint.sh`.
- Matrix como provider custom OpenAI-compatible.
- Hermes Local como provider opcional por gateway privado.

Não presuma que um alias fornecido por um gateway corresponde ao modelo comercial indicado pelo nome. Valide o campo `model` retornado pela API.

## Imagem

O Hermes upstream possui a ferramenta `image_generate`. O provider/modelo é lido da configuração `image_gen` do Hermes.

A skill opcional `baoyu-comic` do upstream possui regra de usar alternativas estilizadas para certas figuras públicas. Se o objetivo for fotografia/realismo, evite deixar skills de comic/ilustração escolherem o fluxo automaticamente. Prefira uma regra explícita de roteamento para `image_generate` e um modelo fotográfico adequado.

## Segurança

NÃO coloque no Git:
- API keys
- senhas
- tokens
- cookies
- auth.json
- conteúdo de `/opt/data/.env`
- estado da Tailnet

As chaves que já foram compartilhadas em chats devem ser rotacionadas antes de entregar este projeto a terceiros.

Use `.env.example` apenas como lista de variáveis.

## Migração

1. Clone este repositório/branch.
2. Copie `.env.example` para `.env`.
3. Preencha secrets no gerenciador da plataforma, não no Git.
4. Crie um volume persistente em `/opt/data` para o hermes-cloud.
5. Suba primeiro `hermes-cloud`.
6. Valide `/health`, dashboard e API 8642.
7. Suba o bridge.
8. Valide `/v1/models` e uma chamada curta de chat.
9. Suba `hermes-web`.
10. Só depois habilite Tailscale/Hermes Local.

## Regra de desenvolvimento

Mantenha o frontend simples desacoplado do dashboard avançado. O usuário final deve usar o Hermes Simples; recursos técnicos podem permanecer no painel avançado.

## O que a próxima plataforma deve fazer primeiro

- revisar `hermes-simple.py`;
- transformar frontend inline em componentes/arquivos separados se desejar;
- adicionar streaming SSE/WebSocket;
- salvar conversas no backend em vez de apenas localStorage;
- implementar upload de arquivos/imagens;
- corrigir o roteamento de geração de imagem para não cair em skills estilizadas sem intenção;
- manter secrets fora do código;
- preservar compatibilidade com a API OpenAI-compatible do Hermes.
