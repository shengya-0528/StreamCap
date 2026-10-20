# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

datas = [('D:\\抖音\\修改\\StreamCap\\config', 'config'), ('D:\\抖音\\修改\\StreamCap\\locales', 'locales'), ('D:\\抖音\\修改\\StreamCap\\assets', 'assets'), ('D:\\抖音\\修改\\StreamCap\\vendor\\ffmpeg\\ffmpeg-2026-10-19-git-2344518cc5-essentials_build\\bin\\ffmpeg.exe', 'ffmpeg'), ('D:\\抖音\\修改\\StreamCap\\vendor\\node\\windows\\node.exe', 'node')]
datas += collect_data_files('streamget')


a = Analysis(
    ['D:\\抖音\\修改\\StreamCap\\main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['pyexpat', '_multiprocessing', 'tzdata', 'plyer.platforms.win.notification'],
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
    [],
    exclude_binaries=True,
    name='StreamCap',
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
    version='D:\\抖音\\修改\\StreamCap\\version_info.txt',
    icon=['D:\\抖音\\修改\\StreamCap\\assets\\icon.ico'],
    contents_directory='_internal',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='StreamCap',
)
