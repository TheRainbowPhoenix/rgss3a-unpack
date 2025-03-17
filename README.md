# RPG Maker VX Ace Tools

## RGSS Archive Tool

Python tool for handling RPG Maker RGSSAD/RGSS3A archives. No dependencies.

### Quick Start

```bash
# Unpack archive to folder:
python dec.py unpack Game.rgss3a OUT-DIR
```

### Basic Usage

1. **List contents**  
`python dec.py list ARCHIVE`

2. **Unpack files**  
`python dec.py unpack ARCHIVE OUTPUT_DIR [REGEX_FILTER]`  
Example (only extract PNGs):  
`python dec.py unpack Game.rgss3a out .*\.png`

3. **Create archive**  
`python dec.py pack INPUT_DIR OUTPUT_ARCHIVE [VERSION]`  
Versions: 1 (RGSSAD), 2 (RGSS2A), 3 (RGSS3A)  
Default: Auto-detect from extension

### Features:
- Supports versions 1-3 (RGSSAD/RGSS2A/RGSS3A)
- Regex filtering for extraction
- Windows/Mac/Linux compatible
- No compile time / no toolchain except Python3
- Just works.

## StableDiffusion-WebUI splitters

Two scripts are available, that will make it easy to upscale png images. Copy both scripts on the folder where you have the images you want to upscale (for example, the folder `C:\Workspace\VxToMv\OUT\Graphics\` will be used)

Run the splitter :
`python split.py`

Go into Stable Diffusion WebUI, and ensure you have a good upscaller like `R-ESRGAN 4x+ Anime6B`, then choose "Extra" > "Batch from Directory" and enable "Upscale" at 1.5 :

![image](https://github.com/user-attachments/assets/a5710cd9-a3d6-4d20-a0eb-f4f0ded2f9a9)

Do that for both `facesIn_alpha` / `facesGen_alpha` and `facesIn_rgb` / `facesGen_rgb`

Finally, run the merger :
`python merge.py`

All the upscalled images are in `facesOut` folder
