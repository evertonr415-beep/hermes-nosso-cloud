# Hermes Nosso — Executor Map

This file defines execution backends for each routed intent. It is operational guidance for the always-loaded `hermes-nosso-router`.

## General rule

Choose the first executor that is actually available in the current runtime. Never claim an integration exists if its tool/credential is unavailable. Never silently replace the requested artifact with another artifact type.

## Video

### General AI video / image-to-video
Primary executor:
- dedicated video-generation provider/tool, if registered in the runtime.

Allowed fallbacks:
- if the user asked for an explainer/technical animation, use `manim-video`;
- if the user asked for creative-code animation, use `p5js`;
- otherwise report that the video provider is not connected. Do not return a static image as if it were a video.

### Manim
Executor:
- terminal/python
- Manim CE
- ffmpeg

Skill:
- `manim-video`

## Image

Primary executor:
- `image_generate` / image-generation provider exposed by the runtime.

Editing:
- use an edit/reference-capable image backend when an input image is supplied.

Specialized:
- masking/segmentation -> `segment-anything-model`
- ComfyUI -> `comfyui`

Do not use generic code or HTML as a substitute for requested image generation.

## Charts / data

Primary executor:
- Python/Jupyter via `jupyter-live-kernel`.

For spreadsheet artifacts:
- `xlsx` skill owns workbook creation/editing and embedded charts.

For geographic datasets:
- `maps` may be combined with Jupyter for preprocessing.

## Websites / web apps

Primary execution stack:
1. `popular-web-designs` / `claude-design` for visual direction when needed.
2. terminal + file-writing/code tools for implementation.
3. browser/computer-use or browser-vision for verification when available.
4. GitHub skills/tools for repository persistence when requested.
5. deployment provider only if a real connected deployment tool/credential exists.

Never claim Vercel, Railway, Netlify, Supabase, or another provider was used unless that provider is actually available and the deployment action succeeded.

## GitHub

Use the narrowest GitHub skill:
- repository/file operations -> `github-repo-management`
- inspect codebase -> `codebase-inspection`
- PR -> `github-pr-workflow`
- review -> `github-code-review`
- issues -> `github-issues`
- auth -> `github-auth`

Executor:
- registered GitHub integration/tool when available;
- otherwise command-line git/GitHub only if authenticated in the runtime.

## Documents

- PDF -> `pdf` or `nano-pdf`
- DOCX -> `docx`
- XLSX -> `xlsx`
- PPTX -> `powerpoint`
- OCR/scans -> `ocr-and-documents`
- structured extraction -> `document-extraction`

Executor:
- skill-prescribed local tools first.
- Preserve the requested file format.

## Research

Primary executor:
- web/search tool for current information.
- `arxiv` for academic paper search.
- `research-paper-writing` for paper composition.

Freshness-sensitive claims must use current search rather than model memory alone.

## Computer / browser

Primary executor:
- `computer-use`

Use only for tasks requiring interaction with graphical/browser interfaces.

## Audio / music

- composition/lyrics/music planning -> `songwriting-and-ai-music`
- actual AudioCraft generation -> `audiocraft-audio-generation` when its dependencies are available
- audio visualization -> `songsee`

If the generation backend is missing, do not claim audio was generated.

## Maps

Primary:
- `maps`

Supporting:
- Jupyter for geocoding/data cleanup where available
- web implementation stack when an interactive web map is requested

## ML / inference

- Hugging Face -> `huggingface-hub`
- llama.cpp -> `llama-cpp`
- vLLM -> `serving-llms-vllm`
- evaluation -> `evaluating-llms-harness`
- W&B -> `weights-and-biases`

Only use providers/services for which runtime credentials are actually present.

## Provider connection state

The current Hermes Cloud runtime is known to have:
- OpenAI-compatible model access
- Matrix provider configuration
- Hermes bridge/local model configuration

External creative/deployment providers such as dedicated AI-video services must be treated as optional until their provider/tool and credential are available in the runtime.

## Failure policy

When the chosen executor is unavailable:
1. try the narrowest valid fallback for the same artifact type;
2. never fabricate completion;
3. never silently return a different artifact type;
4. explain the missing executor succinctly and preserve the user's requested plan for when it becomes available.
