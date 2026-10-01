---
name: hermes-fullstack-builder
description: "Cria e evolui sites, sistemas e aplicações full-stack de ponta a ponta: arquitetura, código, banco, testes, Git e deploy quando houver credenciais disponíveis."
version: 1.0.0
platforms: [linux]
metadata:
  hermes:
    tags: [fullstack, website, webapp, system, react, nextjs, node, python, database, deploy, github, railway, vercel, supabase]
    category: software-development
    requires_toolsets: [terminal]
---

# Hermes Fullstack Builder

## Quando usar

Use esta skill quando o usuário pedir para criar, implementar, terminar, migrar ou publicar um site, sistema, painel, API, SaaS, landing page funcional, aplicativo web ou projeto full-stack.

Use também quando o pedido for curto, por exemplo: "crie um site", "faça um sistema", "monte um painel", "quero um app web". O objetivo padrão é entregar implementação funcional, não apenas plano, mockup ou exemplo de código.

## Objetivo operacional

Levar o pedido do usuário até o artefato executável:

1. entender requisitos e inferir defaults seguros quando detalhes não forem essenciais;
2. escolher uma arquitetura simples e adequada;
3. criar/editar arquivos reais no workspace;
4. instalar dependências necessárias;
5. implementar frontend, backend e banco conforme o caso;
6. executar lint, typecheck, testes e build;
7. abrir a aplicação localmente ou executar smoke test HTTP;
8. corrigir erros encontrados e repetir a validação;
9. persistir em Git quando houver repositório/autenticação disponível;
10. publicar em Vercel, Railway, Supabase ou outro provider somente quando a credencial/ferramenta correspondente estiver realmente disponível;
11. entregar resumo curto com caminho/repositório/link e o que foi validado.

## Regras de execução

- Execute em vez de apenas explicar quando as ferramentas permitirem.
- Não pare após gerar snippets: escreva os arquivos do projeto.
- Não afirme que algo foi publicado sem verificar status/URL.
- Não invente credenciais, tokens, nomes de projeto ou resultado de deploy.
- Antes de sobrescrever projeto existente, inspecione estrutura, package manager, scripts, framework e estado do Git.
- Preserve funcionalidades existentes. Prefira mudanças pequenas e verificáveis a reescritas amplas.
- Para ações irreversíveis ou que possam gerar cobrança, peça confirmação antes da ação final quando exigido pelo provider.
- Nunca grave segredos em código, commit, log ou arquivo público. Use variáveis de ambiente.
- Se um provider não estiver autenticado, deixe o projeto 100% deploy-ready, informe apenas a autenticação que falta e não fabrique conclusão.

## Escolha de stack

### Site estático / landing page
Preferência: HTML/CSS/JS ou Vite/React quando houver interatividade relevante.

### Dashboard / sistema web
Preferência: React + TypeScript. Use Next.js quando SSR, rotas de servidor ou aplicação integrada justificarem.

### API
Escolha a stack já presente no projeto. Em projeto novo, use Node/TypeScript ou Python/FastAPI conforme a natureza da tarefa.

### Banco e autenticação
Quando Supabase estiver disponível, prefira Postgres + Supabase para projetos que precisam de banco/auth/storage rapidamente. Caso contrário, use banco compatível com a infraestrutura disponível e mantenha migrations versionadas.

Não adicione banco, framework ou serviço externo sem necessidade.

## Fluxo para projeto novo

1. Criar pasta de trabalho em diretório persistente quando disponível (`/opt/data/projects/<slug>` no Hermes Cloud; caso contrário workspace atual).
2. Inicializar projeto com nome simples e estável.
3. Criar README com comandos de desenvolvimento, build e deploy.
4. Criar `.gitignore` e `.env.example` sem segredos.
5. Implementar primeiro o caminho crítico do usuário.
6. Executar o projeto e validar a tela/API principal.
7. Adicionar testes mínimos para lógica relevante.
8. Rodar build de produção.
9. Inicializar Git se apropriado.
10. Publicar apenas quando provider autenticado estiver disponível.

## Fluxo para projeto existente

1. `pwd`, `ls`, `git status`, detectar package manager e framework.
2. Ler README, package scripts e arquivos de configuração relevantes.
3. Rodar teste/build existente antes da mudança quando viável para obter baseline.
4. Implementar a menor alteração suficiente.
5. Rodar testes direcionados e depois build/lint relevante.
6. Revisar `git diff` para evitar regressões e segredos.
7. Só então commit/deploy.

## Verificação obrigatória

Um projeto só deve ser chamado de "pronto" quando, conforme aplicável:

- dependências instalaram sem erro;
- lint/typecheck passou ou problemas remanescentes foram declarados;
- testes relevantes passaram;
- build de produção passou;
- servidor iniciou;
- rota/tela principal respondeu;
- banco/migration foi verificado quando usado;
- deploy retornou estado de sucesso e URL, se solicitado e disponível.

Se uma etapa falhar, leia o erro real, corrija e repita. Não esconda falha.

## GitHub

Quando autenticado:

- reutilize repositório fornecido pelo usuário quando houver;
- para projeto novo, crie repositório somente se houver ferramenta/credencial que permita a ação;
- faça commits pequenos com mensagens descritivas;
- não force-push em branch compartilhada;
- verifique `git status` e `git diff --check` antes do commit.

Sem autenticação GitHub, mantenha repo local pronto e diga exatamente que a publicação no GitHub depende de conexão/autorização.

## Vercel

Use para frontend/Next.js quando a CLI/API estiver autenticada. Antes do deploy, rode build local. Após deploy, valide a URL retornada.

## Railway

Use para serviços web, APIs e apps que precisem de runtime persistente. Respeite `PORT` fornecida pelo ambiente e faça bind em `0.0.0.0`. Após deploy, confirme health/status e logs iniciais.

## Supabase

Quando conectado, pode criar/alterar schema por migrations, configurar tabelas, RLS e funções. Nunca desative proteção de dados de forma ampla apenas para fazer o app funcionar. Para dados privados, RLS deve ser deliberada.

## Recuperação automática

Se build/deploy falhar:

1. capturar mensagem de erro e comando que falhou;
2. classificar: dependência, sintaxe/tipo, variável ausente, banco, rede/provider, buildpack/runtime;
3. corrigir causa raiz;
4. executar novamente a menor validação relevante;
5. repetir até sucesso ou até identificar dependência externa que realmente exija ação do usuário.

## Critério de conclusão

Resposta final curta e concreta:

- o que foi criado/alterado;
- onde está;
- testes/build executados;
- URL publicada, se houver e validada;
- único bloqueio externo restante, se existir.

Não terminar com apenas código colado quando arquivos reais poderiam ter sido criados.