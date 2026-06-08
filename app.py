import torch
from diffusers import StableDiffusionXLPipeline
import gradio as gr
import requests
import time
import os

# --- 1. CONFIGURATION ---
# Fetching Telegram Bot details from environment secrets
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
MODEL_ID = "John6666/wai-nsfw-illustrious-v80-sdxl"

# --- 2. ENGINE SETUP ---
print("Loading Uncensored Engine to GPU...")
pipe = StableDiffusionXLPipeline.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float16,
    safety_checker=None, # The Uncensored Override
    requires_safety_checker=False
)
pipe = pipe.to("cuda")
pipe.enable_attention_slicing() # Prevents memory crashes on free T4 GPUs

def generate_image(prompt, negative_prompt, steps, guidance):
    print("Generating artwork...")
    image = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt,
        num_inference_steps=int(steps),
        guidance_scale=float(guidance)
    ).images[0]
    return image

# --- 3. INTERFACE SETUP ---
with gr.Blocks(title="Sila's Private Studio") as demo:
    gr.Markdown("# 🎨 Private Uncensored Studio")
    
    with gr.Row():
        with gr.Column():
            prompt = gr.Textbox(label="Prompt", lines=4)
            negative = gr.Textbox(label="Negative Prompt", value="blurry, low quality, censored, deformed", lines=2)
            steps = gr.Slider(minimum=10, maximum=50, value=30, step=1, label="Steps")
            guidance = gr.Slider(minimum=1.0, maximum=15.0, value=7.5, step=0.5, label="Guidance Scale")
            btn = gr.Button("Generate", variant="primary")
            
        with gr.Column():
            output_image = gr.Image(label="Generated Art")
            
    btn.click(fn=generate_image, inputs=[prompt, negative, steps, guidance], outputs=output_image)

# --- 4. TELEGRAM DELIVERY SYSTEM ---
print("Waking up Sila Studio...")

# Launch in the background so we can grab the URL
demo.launch(share=True, prevent_thread_lock=True)
public_url = demo.share_url

# Fire off Telegram message if secrets are available
if BOT_TOKEN and CHAT_ID:
    message = (
        "🎨 **Sila Image Studio is Awake!**\n\n"
        "Your private server is spun up and ready for today's session.\n\n"
        f"👉 Click here to enter: {public_url}\n\n"
        "(Note: This link will expire when the server goes to sleep.)"
    )
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

while True:
    time.sleep(60)
else:
    print("Skipping Telegram alert: BOT_TOKEN or CHAT_ID environment variables are missing.")
