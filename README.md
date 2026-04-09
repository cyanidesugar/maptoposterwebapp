# Map Studio

Generate beautiful, print-ready map posters for any city in the world. Export as PNG, SVG, PDF, or STL for 3D printing.

## Download

Grab the latest release from the [Releases page](https://github.com/cyanidesugar/maptoposterwebapp/releases/latest). Extract the zip and run `MapToPoster.exe` — no installation required.

> The `themes/` folder must stay next to the EXE.

---

## Features

- Any city in the world via OpenStreetMap
- 36 built-in themes (description shown in the dropdown when selecting)
- Export to PNG, SVG, PDF, or STL
- STL output generates a watertight relief mesh suitable for FDM printing
- Adjustable map radius, resolution, and DPI
- Custom fonts, label sizes, and text overrides
- Preset system to save and recall your favourite settings
- Favourite themes pinned to the top of the dropdown

---

## Themes

| Theme | Description |
|---|---|
| autumn | Burnt oranges, deep reds, golden yellows |
| blueprint | Classic architectural blueprint aesthetic |
| bubblegum_bright | Fun and playful with vibrant candy colors |
| candy_shop | Soft pink background with mint and peach accents |
| citrus_pop | Bright and cheerful with vibrant citrus colors |
| cloudy_day | Serene and misty — soft blue-grey with warm accents |
| contrast_zones | Strong contrast showing urban density |
| copper_patina | Oxidized copper — teal-green patina with copper accents |
| cream_mauve | Sophisticated warm cream with dusty mauve |
| dragons_lair | Volcanic — dark stone with flowing lava and ember accents |
| dusty_peach | Warm and gentle — muted peach with soft grey-greens |
| elven_forest | Ancient woodland — deep greens with silver and ethereal blue |
| emerald | Lush dark green with mint accents |
| enchanted_night | Midnight blue with glowing magical accents |
| fantasy_realm | Parchment background with mystical purple and gold |
| forest | Deep greens and sage — organic botanical aesthetic |
| gradient_roads | Dark centre fading to light edges |
| hangzhou_ink | Traditional Chinese ink wash — elegant grey with subtle blue |
| japanese_ink | Minimalist ink wash with subtle red accent |
| lavender_dream | Soft lavender with rose and periwinkle |
| midnight_blue | Deep navy with gold/copper roads — luxury atlas aesthetic |
| mint_fresh | Cool and clean — soft mint with fresh coral and sky blue |
| misty_lavender | Dreamy greyed lavender with warm undertones |
| monochrome_blue | Single blue family with varying saturation |
| mystical_realm | Enchanted fantasy with purples and ethereal golds |
| neon_cyberpunk | Dark background with electric pink/cyan |
| night_drive | Dark background with brakelight accents |
| noir | Pure black with white/gray roads — modern gallery aesthetic |
| ocean | Blues and teals — perfect for coastal cities |
| pastel_dream | Soft dusty blues and mauves — dreamy artistic aesthetic |
| peach_sorbet | Warm cream with coral and apricot tones |
| sage_garden | Earthy calm — muted sage with terracotta touches |
| soft_sakura | Gentle cherry blossom — muted pinks and creams |
| sunset | Warm oranges and pinks — golden hour aesthetic |
| terracotta | Mediterranean warmth — burnt orange and clay on cream |
| warm_beige | Earthy warm neutrals with sepia tones — vintage map feel |

---

## STL / 3D Printing

Select **STL** as the output format to generate a relief map mesh. Settings available in the GUI:

- **Physical size** (mm) — width and height of the printed object
- **Base thickness** — solid base below the relief
- **Max relief height** — how tall the tallest roads rise above the base
- **Resolution** — grid density (higher = more detail, larger file)
- **Smoothing** — Gaussian blur applied to the heightmap
- **Invert** — raises water/parks instead of roads

Output is always a watertight solid ready to slice directly.

---

## Adding Custom Themes

Create a JSON file in the `themes/` folder next to the EXE:

```json
{
  "name": "My Theme",
  "description": "One-line description shown in the GUI",
  "bg": "#1a1a2e",
  "text": "#e0e0e0",
  "gradient_color": "#1a1a2e",
  "water": "#16213e",
  "parks": "#0f3460",
  "road_motorway": "#e94560",
  "road_primary": "#c84b31",
  "road_secondary": "#a23b2a",
  "road_tertiary": "#7a2c1e",
  "road_residential": "#4a1a0e",
  "road_default": "#3a1208"
}
```

The theme will appear in the dropdown automatically on next launch.

---

## Running from source

```bash
# Clone and set up
git clone https://github.com/cyanidesugar/maptoposterwebapp.git
cd maptoposterwebapp

# Install dependencies
pip install -r requirements.txt

# Run the GUI
python maptoposter_gui.py

# Build the EXE (must use the venv Python)
.venv/Scripts/python.exe build_exe.py
```
