---
title: Hermes Zero-Cost Image Worker
emoji: 🎨
colorFrom: purple
colorTo: blue
sdk: gradio
app_file: app.py
pinned: false
---

# Hermes Zero-Cost Image Worker

GPU worker separado para o Hermes Image Studio, usando **FLUX.1 schnell** com licença Apache 2.0. Este repositório é destinado a um Hugging Face Space separado, não ao Render principal.

## Implantação

1. Crie um Space Gradio novo no Hugging Face e selecione ZeroGPU, se disponível para sua conta.
2. Envie os arquivos desta pasta (`app.py`, `requirements.txt` e `README.md`) para a raiz do Space.
3. Aguarde o build e teste o botão de geração na própria página do Space.
4. Copie a URL direta terminada em `.hf.space`, como `https://<seu-usuario>-<nome-do-space>.hf.space`.
5. No Render do Hermes, adicione `HERMES_IMAGE_STUDIO_SPACE_URL` com essa URL. Para um Space público, não é necessário token. Para um Space privado, configure `HERMES_IMAGE_STUDIO_SPACE_TOKEN` como segredo se a política do Space permitir esse tipo de chamada.
6. Faça deploy do Hermes após as alterações do Image Studio chegarem à branch de produção.

## Limites e custo

- ZeroGPU oferece capacidade GPU sob demanda, com cotas e disponibilidade sujeitas às políticas do Hugging Face. Não promete geração ilimitada nem serviço 24/7.
- O modelo é carregado sob demanda; a primeira geração pode demorar ou falhar por memória, tempo máximo ou cota.
- Nenhum provedor pago é chamado automaticamente pelo Hermes.
- FLUX.1 schnell é um modelo aberto, mas o uso do hardware continua sujeito à infraestrutura e aos termos do provedor.

## Segurança

Mantenha o Space público somente se aceitar que terceiros possam enviar solicitações. Para uso pessoal, prefira acesso restrito se compatível com ZeroGPU e com a autenticação do endpoint. Nunca coloque tokens em arquivos do repositório. O Hermes só aceita URLs HTTPS diretas em `*.hf.space` e rejeita resultados de imagem vindos de outros hosts.
