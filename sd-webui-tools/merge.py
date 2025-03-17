import os
from PIL import Image

# Configuration
rgb_input_dir = "facesGen_rgb"
alpha_input_dir = "facesGen_alpha"
output_dir = "facesOut"

def merge_images(rgb_img, alpha_img):
    # Convert alpha image to single channel
    alpha = alpha_img.convert("L")
    
    # Create RGBA image
    rgba = Image.new("RGBA", rgb_img.size)
    rgba.paste(rgb_img, (0, 0))
    
    # Apply alpha channel
    rgba.putalpha(alpha)
    return rgba

os.makedirs(output_dir, exist_ok=True)

# Get matching pairs
rgb_files = {f.replace("_rgb", ""): f for f in os.listdir(rgb_input_dir) if f.endswith("_rgb.png")}

for base_name, rgb_filename in rgb_files.items():
    alpha_filename = f"{os.path.splitext(base_name)[0]}_alpha.png"
    alpha_path = os.path.join(alpha_input_dir, alpha_filename)
    
    if not os.path.exists(alpha_path):
        print(f"Missing alpha file for {base_name}")
        continue
        
    try:
        # Load RGB image
        rgb_path = os.path.join(rgb_input_dir, rgb_filename)
        with Image.open(rgb_path) as rgb_img:
            
            # Load Alpha mask
            with Image.open(alpha_path) as alpha_img:
                
                # Verify dimensions match
                if rgb_img.size != alpha_img.size:
                    print(f"Size mismatch: {base_name}")
                    continue
                
                # Merge images
                merged = merge_images(rgb_img, alpha_img)
                
                # Save result
                output_path = os.path.join(output_dir, f"{base_name}")
                merged.save(output_path, "PNG")
                print(f"Merged: {base_name}")
                
    except Exception as e:
        print(f"Error processing {base_name}: {str(e)}")
