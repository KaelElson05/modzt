# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['tkinter', 'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox', 'tkinter.simpledialog', 'tkinter.font', 'tkinter.scrolledtext', 'tkinter.colorchooser']
hiddenimports += collect_submodules('modules')


a = Analysis(
    ['modzt.py'],
    pathex=['D:\\Development\\modzt'],
    binaries=[],
    datas=[('D:\\Development\\modzt\\translations.json', '.'), ('D:\\Development\\modzt\\theme_remaster_sirgoose.mp3', '.'), ('D:\\Development\\modzt\\modzt.png', '.'), ('D:\\Development\\modzt\\modzt.ico', '.')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='ModZT',
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
    icon=['modzt.ico'],
)
