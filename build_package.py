"""
MapToPoster Build & Package Script
Builds a standalone EXE using PyInstaller and creates a distributable ZIP.
"""

import subprocess
import sys
import os
import shutil


def clean_build_folders():
    """Remove old build artifacts"""
    print()
    print("=" * 60)
    print("  Cleaning Old Build Files")
    print("=" * 60)
    print()

    folders_to_clean = ['build', 'dist', 'MapToPoster_Distribution', '__pycache__']

    for folder in folders_to_clean:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
                print(f"  [OK] Removed {folder}/")
            except Exception as e:
                print(f"  [WARN] Could not remove {folder}/: {e}")
        else:
            print(f"  [SKIP] {folder}/ doesn't exist")

    # Clean .spec files (will be regenerated)
    for f in os.listdir('.'):
        if f.endswith('.spec') and f != 'MapToPoster.spec':
            try:
                os.remove(f)
                print(f"  [OK] Removed {f}")
            except Exception:
                pass

    print()


def install_pyinstaller():
    """Ensure PyInstaller is installed"""
    print("Checking PyInstaller...")
    try:
        import PyInstaller
        print(f"  [OK] PyInstaller {PyInstaller.__version__} found")
        return True
    except ImportError:
        print("  [INFO] Installing PyInstaller...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("  [OK] PyInstaller installed")
            return True
        except Exception as e:
            print(f"  [FAIL] Could not install PyInstaller: {e}")
            return False


def check_required_files():
    """Check all required files exist"""
    print()
    print("=" * 60)
    print("  Checking Required Files")
    print("=" * 60)
    print()

    required = [
        'maptoposter_gui.py',
        'create_map_poster.py',
        'road_categories.py',
        'font_management.py',
    ]

    optional = [
        'stl_generator.py',
        'lat_lon_parser.py',
    ]

    required_dirs = [
        'themes',
        'fonts',
    ]

    all_ok = True

    for f in required:
        if os.path.exists(f):
            print(f"  [OK] {f}")
        else:
            print(f"  [FAIL] {f} - REQUIRED, NOT FOUND!")
            all_ok = False

    for f in optional:
        if os.path.exists(f):
            print(f"  [OK] {f}")
        else:
            print(f"  [SKIP] {f} (optional)")

    for d in required_dirs:
        if os.path.exists(d) and os.path.isdir(d):
            count = len(os.listdir(d))
            print(f"  [OK] {d}/ ({count} files)")
        else:
            print(f"  [WARN] {d}/ not found")

    print()
    return all_ok


def build_executable():
    """Build the executable using the spec file"""
    print()
    print("=" * 60)
    print("  Building Executable")
    print("=" * 60)
    print()
    print("This will take 5-10 minutes...")
    print()

    try:
        result = subprocess.run(
            [sys.executable, "-m", "PyInstaller", "MapToPoster.spec", "--clean", "--noconfirm"],
            capture_output=False,
            text=True,
        )

        if result.returncode == 0:
            return True
        else:
            print(f"\n  [FAIL] Build exited with code {result.returncode}")
            return False

    except Exception as e:
        print(f"\n  [FAIL] Build failed: {e}")
        return False


def create_distribution():
    """Create a distribution folder with exe and required files"""
    print()
    print("=" * 60)
    print("  Creating Distribution Package")
    print("=" * 60)
    print()

    exe_path = os.path.join('dist', 'MapToPoster.exe')
    if not os.path.exists(exe_path):
        print("  [FAIL] MapToPoster.exe not found in dist/")
        return False

    dist_dir = 'MapToPoster_Distribution'

    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
    os.makedirs(dist_dir)

    # Copy exe
    shutil.copy2(exe_path, dist_dir)
    print("  [OK] Copied MapToPoster.exe")

    # Copy themes
    if os.path.exists('themes'):
        shutil.copytree('themes', os.path.join(dist_dir, 'themes'))
        print("  [OK] Copied themes/")

    # Copy fonts
    if os.path.exists('fonts'):
        shutil.copytree('fonts', os.path.join(dist_dir, 'fonts'))
        print("  [OK] Copied fonts/")

    # Create empty output directories
    for d in ['posters', 'cache']:
        os.makedirs(os.path.join(dist_dir, d), exist_ok=True)
        print(f"  [OK] Created {d}/")

    # Create ZIP
    print()
    print("  Creating ZIP archive...")
    try:
        shutil.make_archive(dist_dir, 'zip', '.', dist_dir)
        zip_size = os.path.getsize(f'{dist_dir}.zip') / (1024 * 1024)
        print(f"  [OK] Created {dist_dir}.zip ({zip_size:.1f} MB)")
    except Exception as e:
        print(f"  [WARN] Could not create ZIP: {e}")

    return True


def main():
    print()
    print("=" * 60)
    print("  MapToPoster Build Script")
    print("=" * 60)
    print()

    if not check_required_files():
        print("[FAIL] Missing required files. Cannot build.")
        print("\nPress Enter to exit...")
        input()
        return False

    if not install_pyinstaller():
        print("\n[FAIL] Could not install PyInstaller.")
        print("\nPress Enter to exit...")
        input()
        return False

    clean_build_folders()
    success = build_executable()

    if success:
        create_distribution()

        print()
        print("=" * 60)
        print("  BUILD COMPLETE!")
        print("=" * 60)
        print()
        print("  Your exe is in:   dist/MapToPoster.exe")
        print("  Distribution:     MapToPoster_Distribution/")
        print("  ZIP archive:      MapToPoster_Distribution.zip")
        print()
    else:
        print()
        print("=" * 60)
        print("  BUILD FAILED")
        print("=" * 60)
        print()
        print("Check the error messages above for details.")
        print()

    print("Press Enter to exit...")
    input()
    return success


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[FAIL] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        print("\nPress Enter to exit...")
        input()
