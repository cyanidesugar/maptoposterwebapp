# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Data files (non-Python assets)
datas = []

import os

if os.path.exists('themes'):
    datas.append(('themes', 'themes'))

if os.path.exists('fonts'):
    datas.append(('fonts', 'fonts'))

a = Analysis(
    ['maptoposter_gui.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # Project modules (imported directly by GUI in frozen mode)
        'create_map_poster',
        'road_categories',
        'font_management',
        'stl_generator',
        'lat_lon_parser',
        # GUI framework
        'customtkinter',
        'PIL._tkinter_finder',
        # Map/geo libraries
        'osmnx',
        'geopandas',
        'shapely',
        'shapely.geometry',
        'geopy',
        'geopy.geocoders',
        # Data/plotting
        'matplotlib',
        'matplotlib.font_manager',
        'matplotlib.pyplot',
        'matplotlib.colors',
        'networkx',
        'numpy',
        'tqdm',
        # STL (optional but included)
        'trimesh',
        'scipy',
        'scipy.ndimage',
        # Network
        'requests',
        'urllib3',
        'certifi',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter.test',
        'test',
        'pytest',
        'IPython',
        'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MapToPoster',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
