"""Hugging Face ZeroGPU worker for Hermes Image Studio.

Deploy this folder as a separate Gradio Space. The model runs only inside a
GPU-granted function; the main Hermes Render service does not need a GPU.
"""
import os
import threading

import gradio as gr
import spaces
import torch
from diffusers import FluxPipeline

MODEL_ID = "black-forest-labs/FLUX.1-schnell"
_pipeline = None
_lock = threading.Lock()


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        with _lock:
            if _pipeline is None:
                pipe = FluxPipeline.from_pretrained(
                    MODEL_ID,
                    torch_dtype=torch.bfloat16,
                )
                pipe.enable_model_cpu_offload()
                _pipeline = pipe
    return _pipeline


@spaces.GPU(duration=60)
def generate(prompt: str, aspect: str = "square"):
    prompt = (prompt or "").strip()
    if not 3 <= len(prompt) <= 4000:
        raise gr.Error("A descrição precisa ter entre 3 e 4.000 caracteres.")
    dimensions = {
        "square": (768, 768),
        "portrait": (768, 1024),
        "landscape": (1024, 768),
    }
    if aspect not in dimensions:
        raise gr.Error("Formato não suportado.")
    width, height = dimensions[aspect]
    pipe = get_pipeline()
    result = pipe(
        prompt=prompt,
        width=width,
        height=height,
        num_inference_steps=4,
        guidance_scale=0.0,
        max_sequence_length=256,
    )
    return result.images[0]


demo = gr.Interface(
    fn=generate,
    inputs=[
        gr.Textbox(label="Descrição da imagem", lines=5, max_lines=12),
        gr.Dropdown(
            choices=["square", "portrait", "landscape"],
            value="square",
            label="Formato",
        ),
    ],
    outputs=gr.Image(type="pil", label="Imagem gerada"),
    title="Hermes Zero-Cost Image Worker",
    description=(
        "FLUX.1 schnell em Hugging Face ZeroGPU. A disponibilidade e a cota "
        "gratuita dependem da conta e das regras atuais do Hugging Face."
    ),
    api_name="generate",
)

if __name__ == "__main__":
    demo.queue(max_size=2).launch(server_name="0.0.0.0", server_port=int(os.getenv("PORT", "7860")))
