# MapToPoster GUI

A beautiful, user-friendly graphical interface for the [MapToPoster](https://github.com/originalankur/maptoposter) project, making it easy to generate stunning minimalist city map posters without using the command line.

![MapToPoster GUI](preview.png)

## Features

### Comprehensive Settings
- **Required Settings**: City and country input with helpful examples
- **Map Settings**: Theme selection, distance/radius control, network type (roads, paths, etc.)
- **Display Settings**: Custom display names, font family support for international languages
- **Image Settings**: Resolution presets (Instagram, wallpapers, prints), custom dimensions, DPI control, multiple output formats
- **Advanced Options**: Generate all 17 themes at once, custom coordinate support

### User-Friendly Interface
- **Live Theme Descriptions**: See what each theme looks like as you select it
- **Resolution Presets**: One-click presets for common formats:
  - Instagram Post (1080×1080)
  - Mobile Wallpaper (1080×1920)
  - HD Wallpaper (1920×1080)
  - 4K Wallpaper (3840×2160)
  - A4 Print (2480×3508)
  - Custom dimensions
- **Real-time Output Log**: Watch the generation process in real-time
- **Input Validation**: Prevents common errors before generation starts
- **Progress Indicator**: Visual feedback during poster generation

### 17 Built-in Themes
- `feature_based` - Classic black & white with road hierarchy
- `gradient_roads` - Smooth gradient shading
- `contrast_zones` - High contrast urban density
- `noir` - Pure black background, white roads
- `midnight_blue` - Navy background with gold roads
- `blueprint` - Architectural blueprint aesthetic
- `neon_cyberpunk` - Dark with electric pink/cyan
- `warm_beige` - Vintage sepia tones
- `pastel_dream` - Soft muted pastels
- `japanese_ink` - Minimalist ink wash style
- `forest` - Deep greens and sage
- `ocean` - Blues and teals for coastal cities
- `terracotta` - Mediterranean warmth
- `sunset` - Warm oranges and pinks
- `autumn` - Seasonal burnt oranges and reds
- `copper_patina` - Oxidized copper aesthetic
- `monochrome_blue` - Single blue color family

## Installation

### Prerequisites
1. Python 3.11 or higher
2. The MapToPoster project files

### Setup

1. **Clone or download the MapToPoster repository:**
   ```bash
   git clone https://github.com/originalankur/maptoposter.git
   cd maptoposter
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   
   Or with uv:
   ```bash
   uv sync
   ```

3. **Download the GUI file** and place `maptoposter_gui.py` in the same directory as `create_map_poster.py`

4. **Run the GUI:**
   ```bash
   python maptoposter_gui.py
   ```
   
   Or with uv:
   ```bash
   uv run maptoposter_gui.py
   ```

## Usage

### Basic Usage
1. Launch the GUI: `python maptoposter_gui.py`
2. Enter a **City** and **Country** (required)
3. Choose a **Theme** from the dropdown
4. Adjust **Distance** for map coverage area (4,000-20,000m recommended)
5. Click **Generate Poster**
6. Find your poster in the `posters/` folder

### Advanced Usage

#### Custom Display Names
Use the "Display Settings" section to override how the city/country appear on the poster:
- **Display Name**: Override the city name shown on poster
- **Display Country**: Override the country name shown on poster

This is useful when:
- The city name is too long
- You want to use a local language name
- You're mapping a district but want the main city name

Example:
```
City: Yuzhong
Country: China
Display Name: Chongqing
Display Country: 中国
```

#### International Fonts
The **Font Family** field supports Google Fonts for international characters:
- Japanese: `Noto Sans JP`
- Korean: `Noto Sans KR`
- Arabic: `Cairo`
- Chinese: `Noto Sans SC`
- Thai: `Noto Sans Thai`

#### Resolution Presets
Select from the **Resolution** dropdown:
- **Instagram Post**: Perfect square for social media
- **Mobile Wallpaper**: Portrait format for phones
- **HD/4K Wallpaper**: Landscape for desktop backgrounds
- **A4 Print**: Standard print size at 300 DPI
- **Custom**: Manually set width and height

#### Network Types
Choose which roads to display:
- **drive**: Main roads only (default, faster)
- **all**: All roads including small streets and alleys
- **walk**: Pedestrian paths
- **bike**: Bicycle paths

#### Generate All Themes
Check "Generate all themes" to create 17 posters at once with all available themes. Great for comparing styles!

#### Custom Coordinates
For precise control, enable "Use custom coordinates" and enter latitude/longitude directly.

## Examples

### Quick Start Examples

**Classic City Poster:**
- City: `Paris`
- Country: `France`
- Theme: `noir`
- Distance: `10000`

**Coastal City:**
- City: `San Francisco`
- Country: `USA`
- Theme: `ocean`
- Distance: `12000`

**Asian Megacity:**
- City: `Tokyo`
- Country: `Japan`
- Theme: `japanese_ink`
- Distance: `15000`
- Font Family: `Noto Sans JP`

**Instagram-Ready:**
- City: `Barcelona`
- Country: `Spain`
- Theme: `warm_beige`
- Distance: `8000`
- Resolution: `Instagram Post (1080x1080)`

### Distance Guidelines
The distance parameter controls how much area is captured:

| Distance | Best For |
|----------|----------|
| 4,000-6,000m | Small/dense cities (Venice, Amsterdam center) |
| 8,000-12,000m | Medium cities, focused downtown (Paris, Barcelona) |
| 15,000-20,000m | Large metros, full city view (Tokyo, Mumbai) |
| 25,000m+ | Metropolitan regions (may be slow) |

## Output

Generated posters are saved in the `posters/` directory with this naming format:
```
{city}_{theme}_{YYYYMMDD_HHMMSS}.{format}
```

Example: `paris_noir_20260128_143052.png`

You can click **"Open Output Folder"** in the GUI to quickly access your generated posters.

## Troubleshooting

### "create_map_poster.py not found"
- Make sure `maptoposter_gui.py` is in the same directory as `create_map_poster.py`
- Check you're running the GUI from the correct directory

### Generation is slow
- Large distances (>20,000m) take longer to process
- Try using `network-type: drive` instead of `all`
- Reduce distance for faster results

### Memory errors
- Large metropolitan areas with `all` network type can use lots of memory
- Try reducing the distance
- Use `drive` network type instead

### Font not found
- The GUI will auto-download fonts from Google Fonts
- Make sure you have internet connection
- Check the font name spelling (case-sensitive)

### No output/poster not generated
- Check the output log in the GUI for error messages
- Verify the city name is spelled correctly
- Some very small towns might not be in OpenStreetMap

## Tips & Tricks

1. **Start with defaults**: First generation use default settings to ensure everything works
2. **Preview with low distance**: Test with smaller distance (5000m) for faster previews
3. **Batch processing**: Use "Generate all themes" to compare styles
4. **Custom names for districts**: Map a specific district but show the main city name
5. **Social media**: Use preset resolutions for perfect social media sizing
6. **Print quality**: Keep DPI at 300 for print, reduce to 150 for screen-only

## System Requirements

- **Python**: 3.11 or higher
- **RAM**: 4GB minimum (8GB+ recommended for large cities)
- **Disk Space**: 100MB for dependencies + space for output files
- **Internet**: Required for downloading map data from OpenStreetMap

## Dependencies

The GUI uses Python's built-in `tkinter` library, so no additional dependencies beyond the MapToPoster requirements:
- osmnx
- matplotlib
- geopandas
- shapely
- numpy
- tqdm
- Pillow
- fonttools

## Credits

- **MapToPoster** by [Ankur Gupta](https://github.com/originalankur/maptoposter)
- **GUI Wrapper** - Makes the powerful MapToPoster accessible to everyone
- **Map Data** from [OpenStreetMap](https://www.openstreetmap.org/)

## License

This GUI wrapper follows the same MIT License as the original MapToPoster project.

## Support

For issues with:
- **The GUI**: Open an issue on this project
- **Map generation/MapToPoster**: Visit the [original repository](https://github.com/originalankur/maptoposter)

## Contributing

Contributions are welcome! Some ideas:
- Additional theme preview images
- Theme editor
- Batch city processing
- Map preview before generation
- Custom color schemes
- Template management

---

**Enjoy creating beautiful map posters!** 🗺️✨
