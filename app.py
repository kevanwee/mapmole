"""
MapMole — Streamlit web UI for raster change detection.

Run with:
    streamlit run app.py
"""

import io
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

from core import run_change_detection, save_raster

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="MapMole", page_icon="🐀", layout="wide")

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* Header bar */
    .main-header {
        background: linear-gradient(135deg, #2e7d32 0%, #1b5e20 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
        text-align: center;
    }
    .main-header h1 { margin: 0; font-size: 2.2rem; }
    .main-header p  { margin: 0.3rem 0 0 0; opacity: 0.85; font-size: 1rem; }

    /* Cards */
    .metric-card {
        background: #f5f5f5;
        border-radius: 10px;
        padding: 1rem 1.25rem;
        text-align: center;
    }
    .metric-card h3 { margin: 0 0 0.25rem 0; font-size: 0.85rem; color: #666; }
    .metric-card p  { margin: 0; font-size: 1.4rem; font-weight: 700; color: #2e7d32; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="main-header">
        <h1>🐀 MapMole</h1>
        <p>Raster Change Detection — upload two GeoTIFF images and detect what changed</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    threshold = st.slider(
        "Change threshold",
        min_value=0.0,
        max_value=1.0,
        value=0.75,
        step=0.05,
        help="Higher = fewer changes detected (stricter). Lower = more changes detected (looser).",
    )
    colormap = st.selectbox(
        "Colour map",
        ["gray", "hot", "inferno", "viridis", "cividis", "RdYlGn"],
        index=0,
    )
    st.markdown("---")
    st.markdown(
        "**How it works**\n"
        "1. Upload two `.tif` raster images\n"
        "2. Adjust the threshold slider\n"
        "3. Click **Run Change Detection**\n"
        "4. Download the resulting change map"
    )

# ── File uploads ─────────────────────────────────────────────────────────────
col_up1, col_up2 = st.columns(2)
with col_up1:
    file1 = st.file_uploader("📂 Upload Image 1 (.tif)", type=["tif", "tiff"], key="f1")
with col_up2:
    file2 = st.file_uploader("📂 Upload Image 2 (.tif)", type=["tif", "tiff"], key="f2")

# ── Run button ───────────────────────────────────────────────────────────────
run_btn = st.button("🚀 Run Change Detection", type="primary", use_container_width=True)

if run_btn:
    if file1 is None or file2 is None:
        st.error("Please upload both images before running.")
        st.stop()

    # Write uploaded files to temp paths so rasterio can open them
    tmp_dir = tempfile.mkdtemp()
    path1 = Path(tmp_dir) / "image1.tif"
    path2 = Path(tmp_dir) / "image2.tif"
    path1.write_bytes(file1.getvalue())
    path2.write_bytes(file2.getvalue())

    with st.spinner("Detecting changes …"):
        try:
            image1, image2, change_map, profile = run_change_detection(
                str(path1), str(path2), threshold
            )
        except Exception as exc:
            st.error(f"Processing failed: {exc}")
            st.stop()

    # ── Metrics row ──────────────────────────────────────────────────────
    total_pixels = change_map.size
    changed_pixels = int(np.count_nonzero(change_map))
    pct_changed = changed_pixels / total_pixels * 100 if total_pixels else 0

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(
            f'<div class="metric-card"><h3>Image Size</h3><p>{image1.shape[1]} × {image1.shape[0]}</p></div>',
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            f'<div class="metric-card"><h3>Total Pixels</h3><p>{total_pixels:,}</p></div>',
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            f'<div class="metric-card"><h3>Changed Pixels</h3><p>{changed_pixels:,}</p></div>',
            unsafe_allow_html=True,
        )
    with m4:
        st.markdown(
            f'<div class="metric-card"><h3>% Changed</h3><p>{pct_changed:.2f}%</p></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── Visualisation ────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    for ax, img, title in zip(
        axes,
        [image1, image2, change_map],
        ["Image 1 (Before)", "Image 2 (After)", "Change Map"],
    ):
        ax.imshow(img, cmap=colormap)
        ax.set_title(title, fontsize=13, fontweight="bold")
        ax.axis("off")
    plt.tight_layout()
    st.pyplot(fig)

    # ── Download button ──────────────────────────────────────────────────
    out_path = Path(tmp_dir) / "change_map.tif"
    save_raster(str(out_path), change_map, profile)
    out_bytes = out_path.read_bytes()

    st.download_button(
        label="⬇️ Download Change Map (.tif)",
        data=out_bytes,
        file_name="mapmole_change_map.tif",
        mime="image/tiff",
        use_container_width=True,
    )

# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("MapMole · MIT License · github.com/kevanwee/mapmole")
