import os
from PIL import Image

# Configuration
input_dir = "faces"

rgb_output_dir = "facesIn_rgb"
alpha_output_dir = "facesIn_alpha"

def process_image(img, base_filename):
    # Split into RGB and Alpha
    rgb_img = img.convert("RGB")
    
    # Create alpha mask (white = opaque, black = transparent)
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        alpha = img.split()[-1]  # Get alpha channel
        alpha_mask = alpha.convert("L")
    else:
        # No alpha channel - create fully opaque mask
        alpha_mask = Image.new("L", img.size, 255)
    
    # Convert alpha mask to RGB (white = 255, black = 0)
    alpha_rgb = alpha_mask.convert("RGB")
    
    return rgb_img, alpha_rgb

os.makedirs(rgb_output_dir, exist_ok=True)
os.makedirs(alpha_output_dir, exist_ok=True)

for filename in os.listdir(input_dir):
    if filename.lower().endswith(".png"):
        input_path = os.path.join(input_dir, filename)
        base_name = os.path.splitext(filename)[0]
        
        try:
            with Image.open(input_path) as img:
                rgb_img, alpha_img = process_image(img, base_name)
                
                # Save RGB version
                rgb_path = os.path.join(rgb_output_dir, f"{base_name}_rgb.png")
                rgb_img.save(rgb_path, "PNG")
                
                # Save Alpha mask version
                alpha_path = os.path.join(alpha_output_dir, f"{base_name}_alpha.png")
                alpha_img.save(alpha_path, "PNG")
                
                print(f"Processed: {filename}")
                
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")