import torch
from diffusers import StableDiffusionXLPipeline
import gradio as gr
import requests
import time
import os
import gc

# --- 1. CONFIGURATION ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Define your model library here
MODELS = {
    "Illustrious (Anime/NSFW)": "John6666/wai-nsfw-illustrious-v80-sdxl",
    "Juggernaut XL v9 (Photorealistic)": "RunDiffusion/Juggernaut-XL-v9",
    "RealVisXL V4.0 (Photorealistic)": "SG161222/RealVisXL_V4.0"
}

# --- 2. ENGINE SETUP ---
current_model_name = "Illustrious (Anime/NSFW)"
pipe = None

def load_pipeline(model_id):
    global pipe
    # Clear VRAM before loading a new model to prevent Out-Of-Memory crashes
    if pipe is not None:
        del pipe
        gc.collect()
        torch.cuda.empty_cache()
    
    print(f"Loading {model_id} to GPU...")
    pipe = StableDiffusionXLPipeline.from_pretrained(
        model_id,
        torch_dtype=torch.float16,
        safety_checker=None, 
        requires_safety_checker=False
    )
    pipe = pipe.to("cuda")
    pipe.enable_attention_slicing()

# Initial startup load
load_pipeline(MODELS[current_model_name])

def generate_image(model_choice, prompt, negative_prompt, steps, guidance):
    global current_model_name, pipe
    
    # Check if the user selected a different model from the dropdown
    if model_choice != current_model_name:
        print(f"Switching model from {current_model_name} to {model_choice}...")
        load_pipeline(MODELS[model_choice])
        current_model_name = model_choice
        
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
            model_dropdown = gr.Dropdown(
                choices=list(MODELS.keys()), 
                value=current_model_name, 
                label="Select Engine"
            )
            prompt = gr.Textbox(label="Prompt", lines=4)
            negative = gr.Textbox(label="Negative Prompt", value="blurry, low quality, censored, deformed", lines=2)
            steps = gr.Slider(minimum=10, maximum=50, value=30, step=1, label="Steps")
            guidance = gr.Slider(minimum=1.0, maximum=15.0, value=7.5, step=0.5, label="Guidance Scale")
            btn = gr.Button("Generate", variant="primary")
            
        with gr.Column():
            output_image = gr.Image(label="Generated Art")
            
    # Added model_dropdown to the inputs array
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
