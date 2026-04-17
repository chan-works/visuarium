# -*- mode: python ; coding: utf-8 -*-
import sys
import os
import glob
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# 버전은 build_mac.sh에서 APP_VERSION 환경변수로 전달
_version = os.environ.get('APP_VERSION', '1.0.0')

# ── Faster-Whisper 패키지 데이터 ──────────────────────────────────────────
faster_whisper_datas = collect_data_files('faster_whisper')

# ── HuggingFace Hub 캐시에서 모델 파일 번들 ───────────────────────────────
hf_hub = os.path.join(os.path.expanduser('~'), '.cache', 'huggingface', 'hub')
model_datas = []

for model_name in ['base']:
    pattern = os.path.join(hf_hub, f'models--Systran--faster-whisper-{model_name}',
                           'snapshots', '*')
    snapshots = glob.glob(pattern)
    if snapshots:
        snapshot_dir = snapshots[0]
        dst = os.path.join('fw_models', model_name)
        for fname in os.listdir(snapshot_dir):
            src = os.path.join(snapshot_dir, fname)
            model_datas.append((src, dst))
        print(f"[build] bundling {model_name} model from {snapshot_dir}")
    else:
        print(f"[build] WARNING: {model_name} model not found in HF cache, will download at runtime")

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
        'av',
    ] + collect_submodules('customtkinter')
      + collect_submodules('faster_whisper')
      + collect_submodules('ctranslate2'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
        'matplotlib', 'pandas', 'scipy.signal',
        'sphinx', 'docutils', 'nbformat', 'black',
        'IPython', 'jupyter', 'notebook',
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
    [],
    exclude_binaries=True,
    name='Agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # macOS에서 UPX 불안정 — 비활성화
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
    upx=False,
    upx_exclude=[],
    name='Agent',
)

app = BUNDLE(
    coll,
    name='Agent.app',
    icon=None,
    bundle_identifier='com.visuarium.agent',
    info_plist={
        'CFBundleDisplayName': 'Agent',
        'CFBundleShortVersionString': _version,
        'CFBundleVersion': _version,
        'NSMicrophoneUsageDescription': '음성 인식을 위해 마이크 접근이 필요합니다.',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '11.0',
    },
)
