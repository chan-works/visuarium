# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect whisper package assets (assets/, mel_filters.npz, etc.)
whisper_datas = collect_data_files('whisper')

# Bundle the pre-downloaded whisper model file
whisper_cache = os.path.join(os.path.expanduser('~'), '.cache', 'whisper')
model_datas = []
if os.path.isdir(whisper_cache):
    for fname in os.listdir(whisper_cache):
        if fname.endswith('.pt'):
            model_datas.append((os.path.join(whisper_cache, fname), 'whisper_models'))

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('config.json', '.'),
        ('src', 'src'),
    ] + whisper_datas + model_datas,
    hiddenimports=[
        'customtkinter',
        'anthropic',
        'whisper',
        'sounddevice',
        'scipy',
        'numpy',
        'websockets',
        'pythonosc',
        'openpyxl',
        'tkinter',
        'sqlite3',
    ] + collect_submodules('customtkinter')
      + collect_submodules('whisper'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,   # No terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='agent',
)
