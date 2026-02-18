# Quick Start Guide - MapToPoster GUI

## Installation (5 minutes)

### 1. Get the MapToPoster code
```bash
git clone https://github.com/originalankur/maptoposter.git
cd maptoposter
```

### 2. Add the GUI files
Download these 3 files and place them in the `maptoposter` directory:
- `maptoposter_gui.py` (the GUI application)
- `setup_gui.py` (setup helper)
- `README_GUI.md` (documentation)

### 3. Run the setup
```bash
python setup_gui.py
```

This will:
- ✓ Check your Python version
- ✓ Verify all files are present
- ✓ Install required dependencies
- ✓ Test the installation
- ✓ Create the output folder

### 4. Launch the GUI
```bash
python maptoposter_gui.py
```

## First Poster (2 minutes)

1. **Enter Location**
   - City: `Paris`
   - Country: `France`

2. **Choose Style**
   - Theme: `noir` (or any other theme you like)

3. **Click "Generate Poster"**
   - Wait ~30 seconds for download and processing
   - Your poster will be in the `posters/` folder

4. **Open the result**
   - Click "Open Output Folder" button
   - Or navigate to `posters/` manually

## Understanding the Settings

### Distance (Map Coverage)
Think of this as "zoom level":
- **Small (4,000-6,000m)**: Focuses on city center, shows more detail
- **Medium (8,000-12,000m)**: Typical city view, good balance
- **Large (15,000-20,000m)**: Wide metropolitan area

### Themes
17 pre-made color schemes:
- **noir**: Classic black & white (great for any city)
- **neon_cyberpunk**: Futuristic style (perfect for modern cities like Tokyo)
- **japanese_ink**: Minimalist Asian aesthetic
- **ocean**: Blues (ideal for coastal cities)
- **warm_beige**: Vintage look (excellent for European cities)

### Resolution Presets
One-click sizing for common uses:
- **Instagram Post**: 1080×1080 square
- **Phone Wallpaper**: 1080×1920 portrait
- **Desktop Wallpaper**: 1920×1080 or 3840×2160
- **Print**: A4 at 300 DPI

## Common Use Cases

### Social Media
1. Set Resolution: `Instagram Post (1080x1080)`
2. Choose a bold theme: `neon_cyberpunk` or `noir`
3. Distance: 8,000-12,000m for recognizable layout

### Desktop Wallpaper
1. Set Resolution: `4K Wallpaper (3840x2160)`
2. Choose softer themes: `pastel_dream`, `ocean`, `sunset`
3. Distance: 15,000-20,000m for sweeping view

### Print Poster
1. Keep Resolution: `Default Poster (12x16)` or `A4 Print`
2. Ensure DPI: `300` (default)
3. Any theme works great for printing!

### Gift/Personalization
1. Use Display Name for special text (nickname, anniversary date)
2. Choose theme matching recipient's style
3. Consider their favorite city or birthplace

## Pro Tips

### Speed Up Generation
- Start with distance ~5,000m for quick preview
- Use `drive` network type (default) instead of `all`
- Generate one theme first, then batch if you like it

### Best Results
- **Grid cities** (New York, Barcelona): Any theme works
- **Organic cities** (Tokyo, Marrakech): Try `japanese_ink`, `warm_beige`
- **Coastal** (San Francisco, Sydney): Use `ocean`, `sunset`
- **Historic** (Paris, Rome): Try `warm_beige`, `copper_patina`

### Avoid Common Mistakes
- ❌ Don't use distance >25,000m (too slow, too much memory)
- ❌ Don't forget to check spelling of city names
- ❌ Don't use network type `all` for first attempt (slower)
- ✓ DO start with defaults, then experiment
- ✓ DO use the output log to track progress
- ✓ DO try multiple themes for comparison

## Troubleshooting Quick Fixes

### "Script not found"
→ Make sure `maptoposter_gui.py` is in the same folder as `create_map_poster.py`

### Generation takes forever
→ Reduce distance to 8,000m or less

### Out of memory
→ Reduce distance or use `drive` instead of `all` for network type

### Can't find city
→ Check spelling, try adding state/region (e.g., "Cambridge, Massachusetts")

### Weird characters in display
→ Set Font Family (e.g., `Noto Sans JP` for Japanese)

## Example Workflows

### Explore a New City (5 minutes)
```
1. Enter city name
2. Click "Generate all themes" checkbox
3. Set distance to 10,000m
4. Generate
5. Compare all 17 themes in output folder
6. Regenerate favorite theme with adjustments
```

### Perfect Gift Poster (10 minutes)
```
1. City: Where they're from or love
2. Display Name: Their name or special date
3. Theme: Match their style/decor
4. Distance: 8,000m for recognizable landmarks
5. Resolution: A4 Print or Default Poster
6. Generate and print!
```

### Social Media Series (15 minutes)
```
1. Pick 3-5 cities with interesting layouts
2. Use same theme for consistency
3. Resolution: Instagram Post
4. Distance: 10,000m
5. Generate all
6. Post as carousel!
```

## Next Steps

Once you're comfortable:
- Experiment with custom coordinates for specific neighborhoods
- Try different fonts for international cities
- Create themed collections (all noir, all Japanese cities, etc.)
- Mix themes and distances to find your style

## Getting Help

- **GUI issues**: Check this guide first
- **Map generation problems**: See main MapToPoster documentation
- **OpenStreetMap errors**: Try different city spelling or coordinates
- **Installation problems**: Run `setup_gui.py` again

---

**Ready to create something beautiful? Launch the GUI and start exploring!** 🗺️✨
