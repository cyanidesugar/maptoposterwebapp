"""
Build Script for MapToPoster
Creates standalone EXE using PyInstaller
"""

import PyInstaller.__main__
import os
import shutil
from pathlib import Path


def build_exe():
    """Build standalone EXE with PyInstaller"""

    print("Building MapToPoster EXE...")
    print()

    # Clean previous builds
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            print(f"Cleaning old {folder} folder...")
            shutil.rmtree(folder)

    if not os.path.exists('maptoposter_gui.py'):
        print("Error: maptoposter_gui.py not found!")
        return

    # Check required files
    required = ['create_map_poster.py', 'road_categories.py', 'font_management.py']
    optional = ['stl_generator.py', 'lat_lon_parser.py']

    for f in required:
        status = "OK" if os.path.exists(f) else "MISSING"
        print(f"  [{status}] {f}")

    for f in optional:
        status = "OK" if os.path.exists(f) else "SKIP"
        print(f"  [{status}] {f}")

    # PyInstaller arguments
    args = [
        'maptoposter_gui.py',
        '--name=MapToPoster',
        '--onefile',
        '--windowed',

        # Project modules
        '--hidden-import=create_map_poster',
        '--hidden-import=road_categories',
        '--hidden-import=font_management',
        '--hidden-import=stl_generator',
        '--hidden-import=lat_lon_parser',

        # Dependencies
        '--hidden-import=osmnx',
        '--hidden-import=geopandas',
        '--hidden-import=trimesh',
        '--hidden-import=scipy',
        '--hidden-import=matplotlib',
        '--hidden-import=numpy',
        '--hidden-import=tqdm',
        '--hidden-import=geopy',
        '--hidden-import=shapely',
        '--hidden-import=customtkinter',

        # Exclude unnecessary modules
        '--exclude-module=pytest',
        '--exclude-module=IPython',
        '--exclude-module=notebook',

        '--clean',
        '--noconfirm',
    ]

    if os.path.exists('icon.ico'):
        args.append('--icon=icon.ico')

    if os.path.exists('themes'):
        args.append('--add-data=themes;themes')
        print("  Adding themes/ folder")

    if os.path.exists('fonts'):
        args.append('--add-data=fonts;fonts')
        print("  Adding fonts/ folder")

    print()
    print("Running PyInstaller...")
    PyInstaller.__main__.run(args)

    print()
    exe_path = Path('dist/MapToPoster.exe')
    if exe_path.exists():
        print("Build complete!")
        print(f"  EXE location: {exe_path.absolute()}")
        print(f"  EXE size: {exe_path.stat().st_size / 1024 / 1024:.1f} MB")
    else:
        print("Build failed - EXE not found in dist/")


if __name__ == "__main__":
    print("MapToPoster Build Script")
    print("=" * 50)
    print()
    build_exe()
