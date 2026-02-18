#!/usr/bin/env python3
"""
MapToPoster Web App using Streamlit
Run with: streamlit run streamlit_app.py
"""

import streamlit as st
import subprocess
import sys
import re
from pathlib import Path

# Import theme list from the main module
from create_map_poster import get_available_themes

# Page config
st.set_page_config(
    page_title="MapToPoster Generator",
    page_icon="\U0001f5fa",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #1e1e1e; }
    .main { color: #e0e0e0; }
</style>
""", unsafe_allow_html=True)

st.title("\U0001f5fa MapToPoster Generator")
st.markdown("Create beautiful, minimalist map posters")

# Load themes dynamically
available_themes = get_available_themes()

# Sidebar
with st.sidebar:
    st.header("Configuration")

    location_mode = st.radio("Location Input", ["City & Country", "Coordinates"])

    if location_mode == "City & Country":
        city = st.text_input("City", placeholder="Paris")
        country = st.text_input("Country", placeholder="France")

        with st.expander("Custom Display Names (Optional)"):
            st.caption("Override the text shown on the poster")
            display_city = st.text_input("Custom City Name", placeholder="Leave blank to use actual name")
            display_country = st.text_input("Custom Country Name", placeholder="Leave blank to use actual name")
    else:
        latitude = st.number_input("Latitude", -90.0, 90.0, 48.8566, format="%.4f")
        longitude = st.number_input("Longitude", -180.0, 180.0, 2.3522, format="%.4f")
        city = "Custom"
        country = "Location"

    st.subheader("Map Design")
    theme = st.selectbox("Theme", available_themes)
    font_family = st.text_input("Font Family", placeholder="Arial, Roboto, Helvetica... (leave blank for default)")
    distance = st.slider("Radius (m)", 1000, 50000, 15000, 1000)
    network_type = st.selectbox("Network Type", ["drive", "all", "walk", "bike"])

    st.subheader("Output")

    size_presets = {
        "Custom": None,
        "Poster (12x16)": (12, 16),
        "A4 Print (8.3x11.7)": (8.3, 11.7),
        "4K Wallpaper (12.8x7.2)": (12.8, 7.2),
        "HD Wallpaper (6.4x3.6)": (6.4, 3.6),
        "Mobile Portrait (3.6x6.4)": (3.6, 6.4),
        "Instagram Square (3.6x3.6)": (3.6, 3.6),
    }
    size_preset = st.selectbox("Size Preset", list(size_presets.keys()))

    if size_preset == "Custom":
        width = st.number_input("Width (inches)", 1.0, 20.0, 12.0, 0.1)
        height = st.number_input("Height (inches)", 1.0, 20.0, 16.0, 0.1)
    else:
        width, height = size_presets[size_preset]

    dpi = st.slider("DPI (Quality)", 72, 600, 300, 50)
    st.caption("72: Screen | 150: Draft | 300: Print | 600: High-res")

    show_roads = st.checkbox("Roads", value=True)
    show_water = st.checkbox("Water", value=True)
    show_parks = st.checkbox("Parks", value=True)

# Main area
if location_mode == "City & Country":
    if not city or not country:
        st.warning("Please enter city and country")
    else:
        st.info(f"Location: {city}, {country}")
else:
    st.info(f"Coordinates: {latitude}, {longitude}")

if st.button("Generate Poster", type="primary", use_container_width=True):
    if location_mode == "City & Country" and (not city or not country):
        st.error("Please provide city and country")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        log_container = st.expander("Generation Log", expanded=True)
        log_area = log_container.empty()
        log_lines: list[str] = []

        with st.spinner("Generating... (30-60 seconds)"):
            try:
                # Build subprocess command
                cmd = [
                    sys.executable, "create_map_poster.py",
                    "-t", theme,
                    "-d", str(distance),
                    "-W", str(width),
                    "-H", str(height),
                    "--dpi", str(dpi),
                    "--network-type", network_type,
                ]

                if font_family:
                    cmd.extend(["--font-family", font_family])

                if location_mode == "City & Country":
                    cmd.extend(["-c", city, "-C", country])
                    if display_city:
                        cmd.extend(["-dc", display_city])
                    if display_country:
                        cmd.extend(["-dC", display_country])
                else:
                    cmd.extend(["--latitude", str(latitude), "--longitude", str(longitude)])
                    cmd.extend(["-c", city, "-C", country])

                if not show_roads:
                    cmd.append("--no-roads")
                if not show_water:
                    cmd.append("--no-water")
                if not show_parks:
                    cmd.append("--no-parks")

                # Run as subprocess
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )

                ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

                for line in process.stdout:
                    clean_line = ansi_escape.sub('', line).rstrip()
                    if not clean_line:
                        continue

                    # Skip progress bar lines
                    if clean_line.count('#') > 10 or clean_line.count('\u2588') > 10:
                        continue

                    log_lines.append(clean_line)
                    log_area.code('\n'.join(log_lines[-50:]))

                    # Update progress based on milestones
                    if "Looking up coordinates" in clean_line:
                        progress_bar.progress(10)
                        status_text.text("Looking up location...")
                    elif "street network" in clean_line.lower():
                        progress_bar.progress(30)
                        status_text.text("Downloading street network...")
                    elif "water" in clean_line.lower():
                        progress_bar.progress(50)
                        status_text.text("Downloading water features...")
                    elif "park" in clean_line.lower() or "green" in clean_line.lower():
                        progress_bar.progress(70)
                        status_text.text("Downloading parks...")
                    elif "rendering" in clean_line.lower() or "applying" in clean_line.lower():
                        progress_bar.progress(85)
                        status_text.text("Rendering map...")
                    elif "done" in clean_line.lower() or "saved" in clean_line.lower():
                        progress_bar.progress(100)
                        status_text.text("Complete!")

                return_code = process.wait()

                if return_code == 0:
                    posters_dir = Path("posters")
                    if posters_dir.exists():
                        posters = sorted(posters_dir.glob("*.png"), key=lambda x: x.stat().st_mtime, reverse=True)
                        if posters:
                            poster_path = posters[0]
                            progress_bar.progress(100)
                            status_text.text("Poster generated successfully!")
                            st.success("Poster generated!")
                            st.image(str(poster_path), use_container_width=True)

                            with open(poster_path, "rb") as file:
                                st.download_button(
                                    "Download Poster",
                                    data=file,
                                    file_name=poster_path.name,
                                    mime="image/png",
                                    use_container_width=True,
                                )
                        else:
                            st.error("No poster generated")
                else:
                    st.error(f"Generation failed (exit code {return_code})")

            except Exception as e:
                st.error(f"Error: {str(e)}")

st.markdown("---")
st.markdown("Map data (c) OpenStreetMap contributors")
