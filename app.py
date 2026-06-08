import torch
from diffusers import AutoPipelineForText2Image
import gradio as gr
import requests
import time
import os
import gc

# --- 1. CONFIGURATION ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

MODELS = {
    "Illustrious (Anime/NSFW)": "John6666/wai-nsfw-illustrious-v80-sdxl",
    "Juggernaut XL v9 (Photorealistic)": "RunDiffusion/Juggernaut-XL-v9",
    "RealVisXL V4.0 (Photorealistic)": "SG161222/RealVisXL_V4.0",
    "Lustly AI Flux (Uncensored)": "lustlyai/Flux_Lustly.ai_Uncensored_nsfw_v1",
    "Heartsync Flux (Uncensored)": "Heartsync/Flux-NSFW-uncensored",
    "FLUX Uncensored Merged": "shauray/FLUX-UNCENSORED-merged",
    "UnfilteredAI NSFW Gen V2": "UnfilteredAI/NSFW-gen-v2",
    "FLUX.1 Schnell (Fast/Permissive)": "black-forest-labs/FLUX.1-schnell",
    "FHDR Uncensored": "kpsss34/FHDR_Uncensored",
    "Z-Image Turbo NSFW": "thutes-gbr25/NSFW-MASTER-Z-IMAGE-TURBO",
    "Qwen Image NSFW": "starsfriday/Qwen-Image-NSFW"
}

# --- 2. ENGINE SETUP ---
current_model_name = "Illustrious (Anime/NSFW)"
pipe = None

def load_pipeline(model_id):
    global pipe
    if pipe is not None:
        del pipe
        gc.collect()
        torch.cuda.empty_cache()
    
    print(f"Loading {model_id} to GPU...")
    
    # AutoPipeline dynamically detects SDXL, SD 1.5, or FLUX
    pipe = AutoPipelineForText2Image.from_pretrained(
        model_id,
        torch_dtype=torch.float16,
        safety_checker=None, 
        requires_safety_checker=False
    )
    
    # Crucial for FLUX models on a T4 GPU to prevent memory crashes
    pipe.enable_model_cpu_offload()

# Initial startup load
load_pipeline(MODELS[current_model_name])

def generate_image(model_choice, prompt, negative_prompt, steps, guidance):
    global current_model_name, pipe
    
    if model_choice != current_model_name:
        print(f"Switching model from {current_model_name} to {model_choice}...")
        load_pipeline(MODELS[model_choice])
        current_model_name = model_choice
        
    print("Generating artwork...")
    
    # Detect if current model is FLUX
    is_flux = "flux" in MODELS[model_choice].lower()
    
    # Build arguments dynamically (FLUX crashes if passed a negative_prompt)
    kwargs = {
        "prompt": prompt,
        "num_inference_steps": int(steps),
        "guidance_scale": float(guidance)
    }
    
    if not is_flux and negative_prompt.strip():
        kwargs["negative_prompt"] = negative_prompt
        
    image = pipe(**kwargs).images[0]
    return image

# --- 3. INTERFACE SETUP ---
with gr.Blocks(title="Sila's Private Studio") as demo:
    gr.Markdown("# 🎨 Private Uncensored Studio")
    
    with gr.Row():
        with gr.Column():
            model_dropdown = gr.Dropdown(
                choices=list(MODELS.keys()), 
                value=current_model_name, 
                label="Select Engine"
            )
            prompt = gr.Textbox(label="Prompt", lines=4)
            negative = gr.Textbox(
                label="Negative Prompt (Ignored by FLUX models)", 
                value="blurry, low quality, censored, deformed", 
                lines=2
            )
            # Adjusted minimum steps down to 1 for Schnell/Turbo models
            steps = gr.Slider(minimum=1, maximum=50, value=30, step=1, label="Steps")
            guidance = gr.Slider(minimum=1.0, maximum=15.0, value=7.5, step=0.5, label="Guidance Scale")
            
            gr.Markdown(
                "**Parameter Cheat Sheet:**\n"
                "* **SDXL/SD1.5:** Steps ~30, Guidance ~7.5\n"
                "* **FLUX/Turbo:** Steps ~4 to 8, Guidance ~1.0 to 3.5\n"
                "* **Schnell:** Steps strictly 4"
            )
            
            btn = gr.Button("Generate", variant="primary")
            
        with gr.Column():
            output_image = gr.Image(label="Generated Art")
            
    btn.click(
        fn=generate_image, 
        inputs=[model_dropdown, prompt, negative, steps, guidance], 
        outputs=output_image
    )

# --- 4. TELEGRAM DELIVERY SYSTEM ---
print("Waking up Sila Studio...")

demo.launch(share=True, prevent_thread_lock=True)
public_url = demo.share_url

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
else:
    print("Skipping Telegram alert: BOT_TOKEN or CHAT_ID environment variables are missing.")

while True:
    time.sleep(60)
