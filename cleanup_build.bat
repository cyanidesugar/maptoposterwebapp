@echo off
echo ============================================
echo   Cleaning Build Folders
echo ============================================
echo.

echo Removing build folder...
if exist build (
    rmdir /s /q build
    echo   [OK] Removed build/
) else (
    echo   [SKIP] build/ doesn't exist
)

echo Removing dist folder...
if exist dist (
    rmdir /s /q dist
    echo   [OK] Removed dist/
) else (
    echo   [SKIP] dist/ doesn't exist
)

echo Removing MapToPoster_Distribution folder...
if exist MapToPoster_Distribution (
    rmdir /s /q MapToPoster_Distribution
    echo   [OK] Removed MapToPoster_Distribution/
) else (
    echo   [SKIP] MapToPoster_Distribution/ doesn't exist
)

echo Removing MapToPoster_Distribution.zip...
if exist MapToPoster_Distribution.zip (
    del /q MapToPoster_Distribution.zip
    echo   [OK] Removed MapToPoster_Distribution.zip
) else (
    echo   [SKIP] MapToPoster_Distribution.zip doesn't exist
)

echo Removing __pycache__ folder...
if exist __pycache__ (
    rmdir /s /q __pycache__
    echo   [OK] Removed __pycache__/
) else (
    echo   [SKIP] __pycache__/ doesn't exist
)

echo Removing *.spec files...
if exist *.spec (
    del /q *.spec
    echo   [OK] Removed .spec files
) else (
    echo   [SKIP] No .spec files found
)

echo.
echo ============================================
echo   Cleanup Complete!
echo ============================================
echo.
echo You can now run build_package.py again.
echo.
pause
