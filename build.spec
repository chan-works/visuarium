# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect faster_whisper package assets
faster_whisper_datas = collect_data_files('faster_whisper')

# Bundle the pre-downloaded faster-whisper model files
fw_cache = os.path.join(os.path.expanduser('~'), '.cache', 'faster_whisper')
model_datas = []
if os.path.isdir(fw_cache):
    for root, dirs, files in os.walk(fw_cache):
        for fname in files:
            src = os.path.join(root, fname)
            rel = os.path.relpath(root, fw_cache)
            dst = os.path.join('faster_whisper_models', rel)
            model_datas.append((src, dst))

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('config.json', '.'),
        ('src', 'src'),
    ] + faster_whisper_datas + model_datas,
    hiddenimports=[
        'customtkinter',
        'anthropic',
        'openai',
        'faster_whisper',
        'ctranslate2',
        'sounddevice',
        'scipy',
        'numpy',
        'websockets',
        'pythonosc',
        'openpyxl',
        'tkinter',
        'sqlite3',
        'huggingface_hub',
        'tokenizers',
    ] + collect_submodules('customtkinter')
      + collect_submodules('faster_whisper')
      + collect_submodules('ctranslate2'),
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
    console=False,
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
