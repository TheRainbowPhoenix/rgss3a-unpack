# RGSS Archive Tool

Python tool for handling RPG Maker RGSSAD/RGSS3A archives. No dependencies.

## Quick Start

```bash
# Unpack archive to folder:
python dec.py unpack Game.rgss3a OUT-DIR
```

## Basic Usage

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

## Features:
- Supports versions 1-3 (RGSSAD/RGSS2A/RGSS3A)
- Regex filtering for extraction
- Windows/Mac/Linux compatible
- No compile time / no toolchain except Python3
- Just works.