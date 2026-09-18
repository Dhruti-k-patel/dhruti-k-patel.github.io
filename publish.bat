@echo off
REM ===========================================================================
REM  Publish the website.
REM
REM  Double-click this file, or run  publish.bat  in a terminal.
REM
REM  It does the four steps in the right order:
REM    1. fetches your latest Substack posts and notes
REM    2. runs the safety check, and STOPS if anything private crept in
REM    3. bundles up the changes
REM    4. uploads them, which updates the live site
REM ===========================================================================

cd /d "%~dp0"
echo.
echo ============================================================
echo   Publishing  https://dhruti-k-patel.github.io/
echo ============================================================

echo.
echo [1/4] Fetching the latest posts and notes from Substack...
echo.
python tools\fetch_substack.py
if errorlevel 1 (
  echo.
  echo   Could not reach Substack. Your existing content was left alone.
  echo   Continuing anyway - press Ctrl+C now if you would rather stop.
  pause
)

echo.
echo [2/4] Safety check - is anything private about to go public?
echo.
python tools\check_before_publish.py
if errorlevel 1 (
  echo.
  echo ============================================================
  echo   STOPPED. Nothing was uploaded.
  echo   Fix what is listed above, then run this again.
  echo ============================================================
  echo.
  pause
  exit /b 1
)

echo.
echo [3/4] Bundling up your changes...
echo.
git add -A
git diff --cached --quiet
if not errorlevel 1 (
  echo   Nothing has changed since last time - nothing to publish.
  echo.
  pause
  exit /b 0
)
git commit -m "Update site"
if errorlevel 1 (
  echo.
  echo   Could not save the changes. Nothing was uploaded.
  echo.
  pause
  exit /b 1
)

echo.
echo [4/4] Uploading...
echo.
git push
if errorlevel 1 (
  echo.
  echo ============================================================
  echo   Upload failed. Your changes are saved on this computer,
  echo   so nothing is lost - just run this again when ready.
  echo   If it keeps failing, check your internet connection.
  echo ============================================================
  echo.
  pause
  exit /b 1
)

echo.
echo ============================================================
echo   Done. The live site updates in about a minute:
echo   https://dhruti-k-patel.github.io/
echo ============================================================
echo.
pause
