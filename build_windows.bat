@echo off
echo [Visuarium] Building Windows EXE...
pip install -r requirements.txt
pip install pyinstaller
pyinstaller build.spec --clean
echo.
echo Build complete! Check dist\Visuarium\ folder.
pause
