#!/usr/bin/env python3
"""
MapToPoster Web App using Streamlit
Run with: streamlit run streamlit_app.py
Deploy to: Streamlit Cloud (free)
"""

import streamlit as st
import sys
import os
from pathlib import Path
import base64
from io import StringIO

# Page config
st.set_page_config(
    page_title="MapToPoster Generator",
    page_icon="🗺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stApp {
        background-color: #1e1e1e;
    }
    .main {
        color: #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("🗺 MapToPoster Generator")
st.markdown("Create beautiful, minimalist map posters")

# Sidebar
with st.sidebar:
    st.header("Configuration")
    
    # Location
    location_mode = st.radio("Location Input", ["City & Country", "Coordinates"])
    
    if location_mode == "City & Country":
        city = st.text_input("City", placeholder="Paris")
        country = st.text_input("Country", placeholder="France")
        
        # Custom display names
        with st.expander("Custom Display Names (Optional)"):
            st.caption("Override the text shown on the poster")
            display_city = st.text_input("Custom City Name", placeholder="Leave blank to use actual name")
            display_country = st.text_input("Custom Country Name", placeholder="Leave blank to use actual name")
    else:
        latitude = st.number_input("Latitude", -90.0, 90.0, 48.8566, format="%.4f")
        longitude = st.number_input("Longitude", -180.0, 180.0, 2.3522, format="%.4f")
        city = "Custom"
        country = "Location"
    
    # Design
    st.subheader("Map Design")
    theme = st.selectbox("Theme", [
        "feature_based", "gradient_roads", "contrast_zones", "noir",
        "midnight_blue", "blueprint", "neon_cyberpunk", "warm_beige",
        "pastel_dream", "japanese_ink", "forest", "ocean",
        "terracotta", "sunset", "autumn", "copper_patina", "monochrome_blue"
    ])
    
    # Font selection
    font_family = st.text_input("Font Family", placeholder="Arial, Roboto, Helvetica... (leave blank for default)")
    
    distance = st.slider("Radius (m)", 1000, 50000, 15000, 1000)
    network_type = st.selectbox("Network Type", ["drive", "all", "walk", "bike"])
    
    # Output
    st.subheader("Output")
    
    # Size presets
    size_preset = st.selectbox("Size Preset", [
        "Custom",
        "Poster (12x16)",
        "A4 Print (8.3x11.7)",
        "4K Wallpaper (12.8x7.2)",
        "HD Wallpaper (6.4x3.6)",
        "Mobile Portrait (3.6x6.4)",
        "Instagram Square (3.6x3.6)"
    ])
    
    if size_preset == "Custom":
        width = st.number_input("Width (inches)", 1.0, 20.0, 12.0, 0.1)
        height = st.number_input("Height (inches)", 1.0, 20.0, 16.0, 0.1)
    else:
        size_map = {
            "Poster (12x16)": (12, 16),
            "A4 Print (8.3x11.7)": (8.3, 11.7),
            "4K Wallpaper (12.8x7.2)": (12.8, 7.2),
            "HD Wallpaper (6.4x3.6)": (6.4, 3.6),
            "Mobile Portrait (3.6x6.4)": (3.6, 6.4),
            "Instagram Square (3.6x3.6)": (3.6, 3.6)
        }
        width, height = size_map[size_preset]
    
    dpi = st.slider("DPI (Quality)", 72, 600, 300, 50)
    st.caption("72: Screen | 150: Draft | 300: Print | 600: High-res")
    
    # Features
    show_roads = st.checkbox("Roads", value=True)
    show_water = st.checkbox("Water", value=True)
    show_parks = st.checkbox("Parks", value=True)

# Main
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
        # Create a progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        log_container = st.expander("📋 Generation Log", expanded=True)
        log_text = log_container.empty()
        
        with st.spinner("Generating... (30-60 seconds)"):
            try:
                # Build args
                args = [
                    "-t", theme,
                    "-d", str(distance),
                    "-W", str(width),
                    "-H", str(height),
                    "--dpi", str(dpi),
                    "--network-type", network_type
                ]
                
                # Add font if specified
                if font_family:
                    args.extend(["--font-family", font_family])
                
                if location_mode == "City & Country":
                    args.extend(["-c", city, "-C", country])
                    # Add custom display names if provided
                    if display_city:
                        args.extend(["-dc", display_city])
                    if display_country:
                        args.extend(["-dC", display_country])
                else:
                    args.extend(["--latitude", str(latitude), "--longitude", str(longitude)])
                    args.extend(["-c", city, "-C", country])
                
                if not show_roads:
                    args.append("--no-roads")
                if not show_water:
                    args.append("--no-water")
                if not show_parks:
                    args.append("--no-parks")
                
                # Execute
                original_argv = sys.argv[:]
                original_stdout = sys.stdout
                original_stderr = sys.stderr
                
                output_buffer = StringIO()
                
                # Track progress based on output
                class ProgressWriter:
                    def __init__(self):
                        self.buffer = ""
                        self.progress = 0
                        self.log_lines = []
                    
                    def write(self, text):
                        if text:
                            self.buffer += text
                            
                            # Add to log display (filter out progress bars)
                            import re
                            # Remove ANSI codes
                            clean_text = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', text)
                            clean_text = clean_text.replace('\r', '\n')
                            
                            # Filter progress bars
                            for line in clean_text.split('\n'):
                                if line.strip():
                                    # Skip lines with lots of # characters (progress bars)
                                    if line.count('#') < 10 and line.count('█') < 10:
                                        self.log_lines.append(line)
                                        # Update log display
                                        log_text.code('\n'.join(self.log_lines[-50:]))  # Show last 50 lines
                            
                            # Update progress based on key milestones
                            if "Looking up coordinates" in text:
                                self.progress = 10
                                status_text.text("📍 Looking up location...")
                                progress_bar.progress(self.progress)
                            elif "Downloading street network" in text or "street network" in text:
                                self.progress = 30
                                status_text.text("🛣️ Downloading street network...")
                                progress_bar.progress(self.progress)
                            elif "Downloading water" in text or "water features" in text:
                                self.progress = 50
                                status_text.text("💧 Downloading water features...")
                                progress_bar.progress(self.progress)
                            elif "Downloading parks" in text or "green spaces" in text:
                                self.progress = 70
                                status_text.text("🌳 Downloading parks...")
                                progress_bar.progress(self.progress)
                            elif "Rendering map" in text or "Creating poster" in text or "Applying" in text:
                                self.progress = 85
                                status_text.text("🎨 Rendering map...")
                                progress_bar.progress(self.progress)
                            elif "Poster saved" in text or "Done!" in text:
                                self.progress = 100
                                status_text.text("✅ Complete!")
                                progress_bar.progress(self.progress)
                    
                    def flush(self):
                        pass
                    
                    def isatty(self):
                        return False
                
                progress_writer = ProgressWriter()
                
                try:
                    sys.argv = ['create_map_poster.py'] + args
                    sys.stdout = progress_writer
                    sys.stderr = progress_writer
                    
                    with open('create_map_poster.py', 'r', encoding='utf-8') as f:
                        script_code = f.read()
                    
                    exec(script_code, {'__name__': '__main__', '__file__': 'create_map_poster.py', '__builtins__': __builtins__})
                    
                    # Find generated poster
                    posters_dir = Path("posters")
                    if posters_dir.exists():
                        posters = sorted(posters_dir.glob("*.png"), key=lambda x: x.stat().st_mtime, reverse=True)
                        if posters:
                            poster_path = posters[0]
                            
                            progress_bar.progress(100)
                            status_text.text("✅ Poster generated successfully!")
                            
                            st.success("Poster generated!")
                            st.image(str(poster_path), use_container_width=True)
                            
                            with open(poster_path, "rb") as file:
                                st.download_button(
                                    "📥 Download Poster",
                                    data=file,
                                    file_name=poster_path.name,
                                    mime="image/png",
                                    use_container_width=True
                                )
                        else:
                            st.error("No poster generated")
                
                finally:
                    sys.argv = original_argv
                    sys.stdout = original_stdout
                    sys.stderr = original_stderr
                
            except Exception as e:
                st.error(f"Error: {str(e)}")

st.markdown("---")
st.markdown("Map data © OpenStreetMap contributors")
