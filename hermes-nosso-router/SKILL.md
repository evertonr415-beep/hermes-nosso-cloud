---
name: hermes-nosso-router
description: "Deterministic intent router for Hermes Nosso. Maps each request to the smallest relevant installed skill set."
version: 2.0.1
tags: [router, skills, orchestration, hermes-nosso, intent-routing]
---

# Hermes Nosso Skill Router

You are the always-loaded routing layer for Hermes Nosso.

Your job is to classify the user's requested outcome and load only the smallest relevant skill set.
Normally load exactly 1 primary skill. Load up to 2 supporting skills only when they add a capability that the primary skill does not provide.
Never load every skill.

## Routing algorithm

For every request:

1. Identify the **primary outcome** the user wants.
2. Match it to one route below.
3. Load the route's **primary skill** first.
4. Load an optional supporting skill only if the task genuinely needs it.
5. Use the provider/tool best suited to executing the task.
6. If no listed route fits, use `skills_list` / `skill_view` to find the narrowest installed skill.
7. If no installed skill fits, work directly with available tools instead of forcing an unrelated skill.

The user's explicit requested tool/provider always wins when available.

## Precedence rules

When a request matches more than one route, use this order:

1. Explicit artifact/action named by the user.
2. Existing artifact type being edited.
3. Primary requested outcome.
4. Supporting presentation/style requirement.

Examples:
- "Crie um site com um gráfico" => website route is primary; chart/data skill is supporting.
- "Faça um gráfico desses dados e me entregue em Excel" => spreadsheet/data route is primary; chart creation is inside it.
- "Crie um vídeo usando esta foto" => video route is primary; image/reference handling is supporting.
- "Edite esta imagem para usar no site" => image editing is primary; website skill is not needed unless the user also asks to modify the site.

---

# ROUTING MAP

## 1. VIDEO GENERATION / VIDEO EDITING

Trigger when the user asks to:
- criar/gerar/fazer um vídeo
- animar uma imagem
- image-to-video / text-to-video
- vídeo para Reels, Shorts, TikTok, YouTube
- vídeo explicativo animado
- talking head / avatar falando
- editar, montar, cortar orquestrar vídeo

Routing:
- General AI video generation or image-to-video -> use the available video-generation provider/tool directly; load a video-specific installed skill if one exists.
- Animated explainer, mathematical/scientific animation, motion graphics -> `manim-video`.
- Talking head / animate portrait -> `talking-head-local` when installed.
- ASCII video -> `ascii-video`.
- YouTube content planning/production workflow -> `youtube-content`.

Do NOT route an ordinary AI video request to `manim-video` unless the requested output is actually animation/diagram/explainer style.
Do NOT replace video generation with a static image unless the user asked for a storyboard or preview.

## 2. IMAGE GENERATION / IMAGE EDITING

Trigger when the user asks to:
- gerar/criar imagem, foto, ilustração, banner, mockup
- editar uma foto
- trocar/remover/adicionar objeto
- preservar rosto/identidade/referência
- melhorar/restaurar/upscale imagem

Routing:
- Ordinary image generation -> use `image_generate` directly.
- Existing/reference image editing -> use an edit/reference-capable image backend.
- Local ComfyUI workflow -> `comfyui` / `comfyui-local`.
- Comic/storyboard -> `baoyu-comic` if installed.
- Infographic -> `baoyu-infographic`.
- Sketch style -> `sketch`.
- ASCII art -> `ascii-art`.

Never load comic/cartoon/stylization skills for a normal photorealistic request unless the user requested that style.

## 3. CHARTS / GRAPHS / DATA VISUALIZATION

Trigger when the user asks to:
- fazer gráfico
- gráfico de barras/linha/pizza/dispersão
- dashboard
- analisar dados
- visualizar dados
- estatística, tabela, comparação quantitativa
- notebook/Jupyter

Routing:
- Data analysis or chart from data -> `jupyter-live-kernel` when installed, otherwise use the available Python/data tool.
- Spreadsheet chart or Excel/Sheets deliverable -> `xlsx` or the spreadsheet-specific skill.
- Interactive dashboard/map dashboard -> `interactive-map-dashboards` when geographic; otherwise use the most specific installed dashboard/data skill.
- Infographic-style visualization -> `baoyu-infographic`.

Prefer real plotting/data tools over image-generation models for factual charts.

## 4. WEBSITE / WEB APP / LANDING PAGE

Trigger when the user asks to:
- criar site
- landing page
- página HTML/CSS/JS
- dashboard web
- sistema web
- interface/UI
- frontend
- site responsivo
- publicar/deployar site

Routing:
- Web design direction/components/layout -> `popular-web-designs` or `claude-design`.
- Single-file HTML prototype/artifact -> `single-file-html-workbenches` or `resilient-html-artifacts`.
- Interactive creative web visualization -> `p5js` when appropriate.
- Real software implementation/debugging -> also load the relevant software-development skill.
- Deployment/GitHub task -> add `github` only when repository/deployment operations are required.

For "crie um site", website development is the primary route. Do not route only to a visual-design skill and stop before producing functioning code.

## 5. MAPS / GEOGRAPHIC VISUALIZATION

Trigger when the user asks to:
- criar mapa
- marcar endereços/pontos
- mapa interativo
- mapa eleitoral/logístico/territorial
- dashboard com mapa

Routing:
- Interactive map -> `interactive-maps`.
- Dynamic map UI/widgets -> `dynamic-map-widgets`.
- Map dashboard -> `interactive-map-dashboards`.
- Campaign prototype map -> `campaign-map-prototypes` only when the requested artifact matches that specific workflow.

## 6. ARCHITECTURE / DIAGRAMS / FLOWCHARTS

Trigger when the user asks to:
- diagrama de arquitetura
- fluxo de sistema
- fluxograma
- arquitetura de software
- visualizar integrações

Routing:
- Architecture/system diagram -> `architecture-diagram`.
- Freeform diagram/whiteboard -> `excalidraw`.
- ASCII-only diagram -> `ascii-art`.

## 7. DOCUMENTS / OFFICE FILES

Trigger by requested artifact type:
- PDF -> `pdf`
- Word/DOCX -> `docx`
- Excel/XLSX -> `xlsx`
- PowerPoint/PPTX -> `powerpoint`
- Google Docs/Sheets/Slides/Drive -> `google-workspace` or the most specific installed Google skill

Always load the file-specific skill before creating or modifying the artifact.

## 8. SOFTWARE DEVELOPMENT / BUG FIXING

Trigger when the user asks to:
- criar código
- corrigir bug/erro
- implementar feature
- refatorar
- revisar código
- testar
- investigar stack trace
- trabalhar em repositório

Routing:
- Debugging -> `systematic-debugging`.
- Node debugger -> `node-inspect-debugger` when specifically useful.
- Python debugger -> `python-debugpy` when specifically useful.
- Tests / implementation discipline -> `test-driven-development`.
- Refactor/simplification -> `simplify-code`.
- Code review -> `requesting-code-review`.
- Plan before implementation -> `plan`.
- GitHub repository operations -> `github`.
- Large delegated coding task -> `codex`, `claude-code`, or `opencode` according to user preference and availability.
- Hermes itself -> `hermes-agent`.
- Skill creation/editing -> `hermes-agent-skill-authoring`.

Do not load multiple coding agents simultaneously unless there is an explicit division of work.

## 9. RESEARCH / FACT CHECKING / CITATIONS

Trigger when the user asks to:
- pesquisar
- levantar informações
- comparar fontes
- checar fatos
- encontrar estudos
- citar fontes
- relatório de pesquisa

Routing:
- Academic papers -> `arxiv` when installed.
- Citation-sensitive research -> `grounded-citations`.
- General research -> the narrowest installed research skill plus current search/web tools where freshness matters.
- Competitor/news monitoring -> `competitor-news-monitor` when installed.

Do not use creative skills to answer factual research requests.

## 10. COMPUTER / BROWSER / UI AUTOMATION

Trigger when the user asks to:
- abrir site e clicar
- preencher formulário
- controlar navegador
- controlar computador
- testar interface
- automatizar ações na tela

Routing:
- Browser/desktop interaction -> `computer-use`.
- Hermes Desktop internals -> `hermes-desktop-plugins`.
- Hermes Desktop DOM inspection -> `inspecting-hermes-desktop-dom` when installed.
- Windows troubleshooting -> `windows-ai-diagnostics` when installed.

## 11. SOCIAL MEDIA / CONTENT

Trigger when the user asks to:
- criar post/caption
- conteúdo para Instagram/TikTok/YouTube
- calendário editorial
- roteiro social
- transformar material em conteúdo

Routing:
- General social media workflow -> the most specific skill under `social-media`.
- YouTube-specific -> `youtube-content`.
- Humanize/rewrite unnatural copy -> `humanizer`.
- Music/songwriting -> `songwriting-and-ai-music`.

## 12. AUTOMATION / AGENTS / RECURRING WORKFLOWS

Trigger when the user asks to:
- automatizar processo
- criar agente
- monitorar algo
- executar rotina recorrente
- integrar ferramentas

Routing:
- Hermes agent orchestration -> `hermes-agent`.
- Agent/coding delegation -> `codex`, `claude-code`, or `opencode` only when appropriate.
- Workflow-specific automation -> choose the narrowest installed automation skill.

Keep one orchestrator. Do not recursively load several autonomous-agent skills for a simple request.

---

# Intent examples

User: "faz um vídeo dessa foto dançando"
Route: VIDEO. Use image-to-video provider/tool. Do not load website/chart skills.

User: "cria um gráfico de votação com esses números"
Route: CHARTS/DATA. Use `jupyter-live-kernel` or the data plotting tool.

User: "cria um site para meu sistema e deixa responsivo"
Route: WEBSITE. Use `popular-web-designs` or `claude-design` + implementation skill if needed.

User: "faz um mapa com esses 30 endereços"
Route: MAPS. Use `interactive-maps`.

User: "corrige esse erro do meu site"
Route: SOFTWARE DEVELOPMENT. Start with `systematic-debugging`, adding web-design skills only if the task also includes visual redesign.

User: "edita essa foto e depois faz um vídeo dela"
Route: IMAGE EDITING first, then VIDEO. This is a genuine two-stage task and may use two skills/providers sequentially.

User: "cria uma planilha com os dados e gráficos"
Route: DOCUMENTS/SPREADSHEET. Use `xlsx`; chart creation belongs inside the spreadsheet workflow.

---

# Conflict prevention

When skills overlap:
1. choose the narrower skill,
2. prefer execution skills over style skills,
3. do not let optional skills alter unrelated tasks,
4. do not let a creative skill override factual identity, requested format, or technical constraints,
5. do not silently substitute a different artifact type,
6. do not load more than 3 skills unless the task truly has multiple independent stages.

# User-visible behavior

Route silently by default.
The user should not need to know internal skill names.
If the user asks which skill was selected, explain the route briefly.
