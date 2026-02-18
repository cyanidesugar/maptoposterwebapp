"""
Project Cleanup Script
Cleans up build artifacts and organizes the project structure
"""

import os
import shutil
from pathlib import Path

def cleanup_project():
    """Clean up the project folder"""
    
    print("🧹 Cleaning up project folder...")
    
    # Folders to delete (build artifacts)
    delete_folders = [
        'build',
        'dist', 
        'cache',
        '__pycache__',
    ]
    
    # Optional: Uncomment to delete old distributions too
    # delete_folders.extend(['MapToPoster_Distribution'])
    
    for folder in delete_folders:
        if os.path.exists(folder):
            print(f"  Deleting {folder}/")
            shutil.rmtree(folder)
    
    # Delete specific files
    delete_files = [
        '*.pyc',
        'uv.lock',
    ]
    
    for pattern in delete_files:
        for file in Path('.').rglob(pattern):
            print(f"  Deleting {file}")
            file.unlink()
    
    # Optional: Delete old ZIPs
    # for file in Path('.').glob('*.zip'):
    #     print(f"  Deleting {file}")
    #     file.unlink()
    
    print("✅ Cleanup complete!")
    print()
    print("📁 Recommended next steps:")
    print("  1. Create 'src/' folder")
    print("  2. Move all .py files except build scripts to src/")
    print("  3. Update imports if needed")
    print("  4. Rebuild your EXE")

if __name__ == "__main__":
    cleanup_project()
