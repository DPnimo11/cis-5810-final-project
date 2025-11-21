import os
import subprocess
import sys
import json
import base64
import requests
from rembg import remove

# --- CONFIGURATION ---
TRIPOSR_PATH = os.path.abspath("TRIPOSR_FILE_PATH") 
BLENDER_EXEC = "BLENDER_FILE_PATH" 

# !!! PASTE YOUR FREE KEY HERE !!!
API_KEY = "YOUR_API_KEY"

def clean_background(input_path, output_path):
    """Removes background using rembg."""
    print(f"   [>] Cleanup: Removing background for {os.path.basename(input_path)}...")
    try:
        with open(input_path, 'rb') as i:
            input_data = i.read()
            output_data = remove(input_data)
        
        abs_out = os.path.abspath(output_path)
        with open(abs_out, 'wb') as o:
            o.write(output_data)
        return abs_out
    except Exception as e:
        print(f"   [!] BG Removal Failed: {e}")
        return os.path.abspath(input_path)

def get_physics_gemini_rest(image_path):
    print(f"   [>] Gemini API: Analyzing {os.path.basename(image_path)}...")
    
    with open(image_path, "rb") as f:
        b64_data = base64.b64encode(f.read()).decode('utf-8')
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    
    # UPDATED PROMPT
    prompt_text = """
    Look at this object. Estimate its physics properties and visual orientation.
    Return ONLY a raw JSON object (no markdown) with these keys:
    "mass": number (kg),
    "bounciness": number (0.0 to 0.95),
    "friction": number (0.0 to 1.0),
    "facing": string (one of: "left", "right", "front").
    
    Note: If the object is facing the left side of the image, return "left". 
    If it faces the right side, return "right".
    """
    
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt_text},
                {"inline_data": {"mime_type": "image/png", "data": b64_data}}
            ]
        }]
    }

    try:
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        if response.status_code != 200:
            print(f"       [!] API Error {response.status_code}")
            return {"mass": 1.0, "bounciness": 0.5, "friction": 0.5, "facing": "front"}

        result = response.json()
        text_content = result['candidates'][0]['content']['parts'][0]['text']
        clean_json = text_content.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_json)
        
        print(f"       [i] Result: Mass={data.get('mass')}kg, Facing={data.get('facing')}")
        return data

    except Exception as e:
        print(f"       [!] Error parsing Gemini response: {e}")
        return {"mass": 1.0, "bounciness": 0.5, "friction": 0.5, "facing": "front"}

def generate_3d_model(image_path, dir):
    """Calls TripoSR locally."""
    print(f"   [>] TripoSR: Generating 3D mesh...")
    output_dir = os.path.join(os.getcwd(), dir)
    os.makedirs(output_dir, exist_ok=True)

    try:
        subprocess.run([
            "python", "run.py",
            image_path,
            "--output-dir", output_dir,
        ], cwd=TRIPOSR_PATH, check=True)
    except Exception:
        print("   [!] TripoSR Failed.")
        sys.exit(1)

    base_name = os.path.splitext(os.path.basename(image_path))[0]
    expected_mesh = os.path.join(output_dir, "0", "mesh.obj")
    return expected_mesh

def main():
    # ... Setup code ...
    raw_img_A = os.path.abspath("captured.jpeg")
    raw_img_B = os.path.abspath("horse.png")

    # --- PROCESS OBJECT A ---
    print("\n--- Object A ---")
    phys_A = get_physics_gemini_rest(raw_img_A)
    clean_A = clean_background(raw_img_A, "clean_A.png")
    model_A = generate_3d_model(clean_A, "A")
    #model_A = os.path.join(os.getcwd(), "A/0/mesh.obj")

    # --- PROCESS OBJECT B ---
    print("\n--- Object B ---")
    phys_B = get_physics_gemini_rest(raw_img_B)
    clean_B = clean_background(raw_img_B, "clean_B.png")
    model_B = generate_3d_model(clean_B, "B")
    #model_B = os.path.join(os.getcwd(), "B/0/mesh.obj")
    
    # --- SIMULATE ---
    print("\n[>] Blender: Starting Simulation...")
    
    # PASS NEW ARGUMENTS (Facing Direction)
    args = [
        model_A, str(phys_A.get('mass', 1)), str(phys_A.get('bounciness', 0.5)), str(phys_A.get('friction', 0.5)), str(phys_A.get('facing', 'front')),
        model_B, str(phys_B.get('mass', 1)), str(phys_B.get('bounciness', 0.5)), str(phys_B.get('friction', 0.5)), str(phys_B.get('facing', 'front'))
    ]

    subprocess.run([
        BLENDER_EXEC,
        "--background", 
        "--python", "final_blender.py", 
        "--", 
        *args
    ])
    
    print("\n[Done] Check output_collision.mp4!")

if __name__ == "__main__":
    main()