# Llama local como provedor opcional do Hermescloud

Este procedimento é uma preparação para teste controlado. **Não faça merge nem deploy só por seguir este documento.** Groq deve continuar como padrão.

## Pré-requisitos já verificados

- Ollama executa `llama3.2:3b` no computador do proprietário.
- O bridge local responde em `127.0.0.1:8765`.
- A rota OpenAI-compatible `/v1/chat/completions` respondeu localmente e pelo hostname HTTPS.
- O hostname usado nos testes é `https://llama.sistemavotoforte.com.br/v1/chat/completions`.

O computador, Ollama, bridge e túnel precisam permanecer ligados. Não exponha a porta Ollama `11434` diretamente à internet.

## Segredo

O nome de variável usado pelo bridge local e pelo roteador deve ser idêntico: `HERMES_LLAMA_BRIDGE_KEY`.

O valor precisa ser a mesma chave aleatória longa já configurada no computador do proprietário. Cadastre-a como **secret** no Render; não a coloque no GitHub, em JSON de configuração, no frontend, em logs ou em mensagens de chat. Nunca cole o valor da chave em issues ou pull requests.

## Variáveis de ambiente no serviço Hermes do Render

Configure apenas depois de confirmar que o endpoint é protegido e que o segredo correspondente foi cadastrado. Adicione/mescle as variáveis abaixo, sem substituir o restante do ambiente:

- `HERMES_GLOBAL_ROUTER_ENABLED=1`
- `HERMES_GLOBAL_ALLOWED_PROVIDERS=ollama-local`
- `HERMES_GLOBAL_PROVIDERS_JSON=[{"id":"ollama-local","url":"https://llama.sistemavotoforte.com.br/v1/chat/completions","model":"llama3.2:3b","api_key_env":"HERMES_LLAMA_BRIDGE_KEY","priority":-30,"max_tokens":512,"timeout":20}]`
- `HERMES_LLAMA_BRIDGE_KEY`: o mesmo valor secreto já guardado no computador.

Atenção: `HERMES_GLOBAL_ALLOWED_PROVIDERS` é uma lista de provedores personalizados autorizados. Se o ambiente já contiver provedores personalizados necessários, preserve-os e acrescente `ollama-local), em vez de substituir a lista inteira. Do mesmo modo, se `HERMES_GLOBAL_PROVIDERS_JSON` já tiver entradas válidas, preserve-as e acrescente a entrada local.

## Sequência de validação antes de ativar

1. Teste o endpoint HTTPS com a autenticação e uma mensagem não sensível.
2. Confirme no roteador que `configured()` lista `ollama-local` sem imprimir segredo.
3. Faça uma solicitação de teste explicitamente com `provider_id=ollama-local` em ambiente de teste, não com tráfego real.
4. Verifique que falha do Llama retorna erro seguro e não troca silenciosamente para outro provedor quando o usuário escolheu Llama.
5. Teste a interface e os testes de regressão.
6. Só depois de revisão humana, aplique a configuração no Render e faça deploy manual controlado. Não mude `HERMES_INFERENCE_MODE=groq`; Groq continua sendo o padrão.

## Segurança e limitações

- Use HTTPS e bearer authentication; considere Cloudflare Access ou outra política de acesso à frente do túnel, se compatível com chamadas máquina-a-máquina.
- A chave é uma credencial de alto impacto: rotacione-a se for exposta.
- O bridge atual não aceita streaming; mensagens devem usar `stream=false`.
- O modelo é pequeno e pode não obedecer a instruções exatas.
- O Llama só estará disponível enquanto o computador e o túnel estiverem online.
- Os testes automatizados de CI usam respostas simuladas. Eles não comprovam por si só a conectividade real entre Render e o computador.
