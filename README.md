# 🐀 MapMole

**Raster change detection made easy** — upload two GeoTIFF satellite images and instantly see what changed.

<div align="center">
  <img src="./readme/sample.jpg" alt="MapMole sample output" />
</div>

## Overview

MapMole compares two raster images (GeoTIFF) and produces a binary change map highlighting areas of difference. It ships with both a **Streamlit web UI** and a **command-line interface**, so you can use whichever fits your workflow.

### Use Cases

| Domain | Example |
|--------|---------|
| **HADR** | Assess damage after natural disasters by comparing pre- and post-event satellite imagery |
| **IMINT** | Monitor activity patterns, infrastructure, and developments over time |
| **Cartography** | Detect deforestation, urban expansion, or shifting coastlines for mapsheet refreshes |

<div align="center">
  <img src="./readme/theory.png" alt="Change detection theory" />
</div>

## How It Works

1. **Read** — extracts the first band of each GeoTIFF (single-band grayscale assumed).
2. **Align** — if dimensions differ, the second image is resampled to match the first using bilinear interpolation via [Rasterio](https://rasterio.readthedocs.io/).
3. **Diff** — computes the absolute pixel-wise difference.
4. **Enhance** — normalises to 0–255, applies a log stretch (`log(1 + x)`), then thresholds with a configurable sensitivity factor to produce a binary mask.

> **Tip:** Use images in the same projection system for best results. Colour-correcting the imagery beforehand also helps. Results may vary with cloud cover or georectification errors.

## Quick Start

### Prerequisites

- Python 3.9+

### Install

```bash
pip install -r requirements.txt
```

### Web UI (recommended)

```bash
streamlit run app.py
```

This opens an interactive dashboard where you can:
- Upload two `.tif` images
- Adjust the change-detection threshold with a slider
- Choose a colour map
- View side-by-side results with statistics
- Download the output change map

### CLI

```bash
# Interactive prompts
python mapmole.py

# Or pass arguments directly
python mapmole.py --image1 before.tif --image2 after.tif --output changes.tif --threshold 0.7
```

## Project Structure

```
mapmole/
├── app.py              # Streamlit web UI
├── core.py             # Shared change-detection engine
├── mapmole.py          # Command-line interface
├── requirements.txt    # Python dependencies
├── .gitignore
├── LICENSE             # MIT
└── readme/             # Images for this README
```

---

## CLI Reference

The CLI supports both **interactive mode** (guided prompts) and **argument mode** for scripting and automation.

### Interactive Mode

```bash
python mapmole.py
```

You'll be prompted to enter:
1. Path to the first `.tif` image
2. Path to the second `.tif` image
3. Path for the output `.tif` file

A matplotlib window will display the before, after, and change map side by side.

### Argument Mode

```bash
python mapmole.py --image1 <path> --image2 <path> --output <path> [--threshold <float>]
```

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--image1` | Yes* | — | Path to the first (before) `.tif` image |
| `--image2` | Yes* | — | Path to the second (after) `.tif` image |
| `--output` | Yes* | — | Path for the output change map `.tif` |
| `--threshold` | No | `0.75` | Sensitivity factor (0.0–1.0). Lower = more changes detected |

*If omitted, the CLI falls back to interactive prompts.

### Examples

```bash
# Full argument mode — no prompts
python mapmole.py --image1 before.tif --image2 after.tif --output changes.tif

# High sensitivity (detect subtle changes)
python mapmole.py --image1 before.tif --image2 after.tif --output changes.tif --threshold 0.5

# Low sensitivity (only major changes)
python mapmole.py --image1 before.tif --image2 after.tif --output changes.tif --threshold 0.9

# Mixed — supply images via args, get prompted for output path
python mapmole.py --image1 before.tif --image2 after.tif
```

## License

[MIT](LICENSE) — made by [kevanwee](https://github.com/kevanwee).

