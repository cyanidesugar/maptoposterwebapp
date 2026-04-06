# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['maptoposter_gui.py'],
    pathex=[],
    binaries=[],
    datas=[('themes', 'themes'), ('fonts', 'fonts')],
    hiddenimports=['create_map_poster', 'road_categories', 'font_management', 'stl_generator', 'lat_lon_parser', 'osmnx', 'geopandas', 'trimesh', 'scipy', 'matplotlib', 'numpy', 'tqdm', 'geopy', 'shapely', 'customtkinter'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'IPython', 'notebook'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MapToPoster',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
