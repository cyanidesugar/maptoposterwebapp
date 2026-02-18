# Sync Map Studio (local) → GitHub (maptoposterwebapp Desktop branch)

This document compares your local **Map Studio New** project with the [GitHub repo](https://github.com/cyanidesugar/maptoposterwebapp/tree/Desktop) and explains how to update the repo.

---

## Comparison summary

| Area | GitHub (Desktop) | Your local (Map Studio New) |
|------|------------------|-----------------------------|
| **Entry points** | `streamlit_app.py` (web), CLI `create_map_poster.py` | `maptoposter_gui.py` (desktop GUI), CLI `create_map_poster.py`, PyInstaller build |
| **requirements.txt** | Pinned deps + streamlit + duplicate loose deps; no customtkinter; includes flake8/pycodestyle/pyflakes | Pinned runtime only; customtkinter; dev deps moved to requirements-dev.txt |
| **.gitignore** | No distribution folder or gui_settings | MapToPoster_Distribution/, gui_settings.json added |
| **create_map_poster.py** | Relative paths (themes/), uses `args` inside create_poster, bare `except:` | BASE_DIR for frozen/script, optional STL, `except Exception` fixes |
| **Extra local files** | — | maptoposter_gui.py, build_exe.py, build_package.py, MapToPoster.spec, stl_generator.py, lat_lon_parser.py, requirements_stl.txt, requirements-dev.txt |

---

## How to update the GitHub repo

You need Git installed and the repo cloned. From a terminal:

### 1. Clone (if you don’t have it yet)

```bash
git clone https://github.com/cyanidesugar/maptoposterwebapp.git
cd maptoposterwebapp
git checkout Desktop
```

### 2. Copy these files from your project into the clone

From **Map Studio New** into the **maptoposterwebapp** repo root:

Overwrite in the repo root:

- **`github_sync/requirements.txt`** → replace repo’s `requirements.txt`  
  (adds customtkinter, keeps streamlit, removes dev deps from main list.)

- **`github_sync/.gitignore`** → replace repo’s `.gitignore`  
  (adds MapToPoster_Distribution, gui_settings.json.)

Add as new file:

- **`github_sync/requirements-dev.txt`** → add as **`requirements-dev.txt`** in repo root.

**Quick copy (PowerShell)** — run from **Map Studio New** with the repo cloned at `../maptoposterwebapp`:

```powershell
$repo = "e:\3D Stuff\01 Coding STuff\maptoposterwebapp"   # adjust path to your clone
Copy-Item "github_sync\requirements.txt" $repo -Force
Copy-Item "github_sync\.gitignore" $repo -Force
Copy-Item "github_sync\requirements-dev.txt" $repo -Force
```

### 3. (Optional) Add full desktop app to the Desktop branch

To make the GitHub Desktop branch match your desktop app and build:

Copy these from **Map Studio New** (project root) into the repo root:

- `maptoposter_gui.py`
- `build_exe.py`
- `build_package.py`
- `MapToPoster.spec`
- `requirements_stl.txt` (optional, for STL/3D print support)

Optional modules (if you use them):

- `stl_generator.py`
- `lat_lon_parser.py`

### 4. (Optional) Sync create_map_poster.py improvements

GitHub’s `create_map_poster.py` is structured for the web app (uses `args` inside `create_poster`, relative paths). Your local version adds:

- `BASE_DIR` / frozen detection for themes and fonts when run as EXE
- Optional STL import and `STL_AVAILABLE`
- `except Exception` instead of bare `except:`

To bring those into the repo without replacing the whole file you can:

- Manually apply the same pattern (frozen check, `BASE_DIR`, THEMES_DIR/FONTS_DIR from BASE_DIR) and the exception fixes, **or**
- Replace `create_map_poster.py` in the repo with your local file and then re-apply any streamlit-specific behavior (e.g. passing options without `args`) if the web app needs it.

### 5. Commit and push

```bash
git add requirements.txt .gitignore requirements-dev.txt
# If you added desktop files:
# git add maptoposter_gui.py build_exe.py build_package.py MapToPoster.spec requirements_stl.txt

git commit -m "Sync from Map Studio: requirements (customtkinter, streamlit), .gitignore, requirements-dev"
git push origin Desktop
```

If you added desktop files:

```bash
git commit -m "Add desktop GUI and PyInstaller build (Map Studio)"
git push origin Desktop
```

---

## Files in `github_sync/`

- **requirements.txt** – Single file to drop in as the repo’s `requirements.txt` (runtime + streamlit + customtkinter).
- **requirements-dev.txt** – Dev/lint deps; add to repo as `requirements-dev.txt`.
- **.gitignore** – Drop in to replace repo’s `.gitignore`.

After copying and pushing, the GitHub repo will be updated to match these optimizations and optional desktop setup.
