# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['gk_install_builder/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('gk_install_builder/templates', 'templates'),
        ('helper', 'helper'),
        ('gk_install_builder/assets', 'assets')
    ],
    hiddenimports=[],
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
    name='GK Install Builder',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Set to True for console output
    icon='gk_install_builder/assets/gk_logo.png',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Add COLLECT to create the directory with all files
COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GK Install Builder',
) 