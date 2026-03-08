"""
MapMole CLI — command-line interface for raster change detection.

Usage:
    python mapmole.py
"""

import argparse
import sys

import matplotlib.pyplot as plt

from core import run_change_detection, save_raster


def _prompt_path(label):
    """Prompt for a .tif file path with basic validation."""
    while True:
        path = input(f"Enter path to the {label} .tif image: ").strip()
        if path.lower().endswith(".tif"):
            return path
        print("Invalid file format. Please enter a .tif file.")


def main():
    parser = argparse.ArgumentParser(
        description="MapMole — detect changes between two GeoTIFF raster images.",
    )
    parser.add_argument("--image1", help="Path to the first .tif image")
    parser.add_argument("--image2", help="Path to the second .tif image")
    parser.add_argument("--output", help="Path for the output .tif file")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.75,
        help="Threshold factor for change sensitivity (0.0–1.0, default 0.75)",
    )
    args = parser.parse_args()

    image1_path = args.image1 or _prompt_path("first")
    image2_path = args.image2 or _prompt_path("second")
    output_path = args.output or _prompt_path("output")

    print("Running change detection …")
    try:
        image1, image2, change_map, profile = run_change_detection(
            image1_path, image2_path, args.threshold
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    save_raster(output_path, change_map, profile)
    print(f"Change map saved to {output_path}")

    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    for ax, img, title in zip(
        axes, [image1, image2, change_map], ["Image 1", "Image 2", "Change Map"]
    ):
        ax.imshow(img, cmap="gray")
        ax.set_title(title)
        ax.axis("off")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
