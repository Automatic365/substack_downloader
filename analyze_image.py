from PIL import Image
from collections import Counter
import math

def get_dominant_colors(image_path, num_colors=5):
    img = Image.open(image_path)
    img = img.convert("RGB")
    img = img.resize((150, 150))  # Resize for speed
    
    pixels = list(img.getdata())
    
    # Simple frequency count (a real K-means would be better but this is standard lib + pillow only)
    # To reduce noise, we can quantize colors (round to nearest 10)
    quantized_pixels = [tuple(round(c/20)*20 for c in p) for p in pixels]
    
    counts = Counter(quantized_pixels)
    common = counts.most_common(num_colors)
    
    return [c[0] for c in common]

def get_brightness(image_path):
    img = Image.open(image_path).convert('L')
    stat = img.resize((1,1)).getpixel((0,0))
    return stat

def analyze(path):
    print(f"Analyzing {path}...")
    try:
        colors = get_dominant_colors(path)
        brightness = get_brightness(path)
        
        print(f"Brightness (0-255): {brightness}")
        if brightness < 100:
            print("Mode: Dark")
        else:
            print("Mode: Light")
            
        print("Dominant Colors (RGB):")
        for c in colors:
            print(f"  - {c} (Hex: #{c[0]:02x}{c[1]:02x}{c[2]:02x})")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze("exec.png")
