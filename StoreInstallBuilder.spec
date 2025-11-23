# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['run_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('gk_install_builder/templates', 'gk_install_builder/templates'),
        ('helper', 'helper'),
        ('gk_install_builder/assets', 'gk_install_builder/assets')
    ],
    hiddenimports=[
        'PIL._tkinter_finder',
        'PIL._imagingtk',
        'PIL._tkinter_finder',
        'customtkinter',
        'webdavclient3',
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.ttk',
        # Fix for PyInstaller backports module error
        'backports',
        'pkg_resources.extern',
        'pkg_resources._vendor',
        # Core modules (relative imports from main.py)
        'gk_install_builder.config',
        'gk_install_builder.generator',
        'gk_install_builder.detection',
        'gk_install_builder.environment_manager',
        'gk_install_builder.pleasant_password_client',
        # Generator modules
        'gk_install_builder.generators',
        'gk_install_builder.generators.gk_install_generator',
        'gk_install_builder.generators.helper_file_generator',
        'gk_install_builder.generators.launcher_generator',
        'gk_install_builder.generators.onboarding_generator',
        'gk_install_builder.generators.template_processor',
        'gk_install_builder.generators.offline_package_helpers',
        # Configuration module
        'gk_install_builder.gen_config',
        'gk_install_builder.gen_config.generator_config',
        # UI modules
        'gk_install_builder.ui',
        'gk_install_builder.ui.helpers',
        # Utils modules
        'gk_install_builder.utils',
        'gk_install_builder.utils.tooltips',
        'gk_install_builder.utils.ui_colors',
        'gk_install_builder.utils.helpers',
        'gk_install_builder.utils.version',
        # Dialog modules
        'gk_install_builder.dialogs',
        'gk_install_builder.dialogs.about',
        'gk_install_builder.dialogs.launcher_settings',
        'gk_install_builder.dialogs.offline_package',
        'gk_install_builder.dialogs.detection_settings',
        # Feature modules
        'gk_install_builder.features',
        'gk_install_builder.features.auto_fill',
        'gk_install_builder.features.platform_handler',
        'gk_install_builder.features.version_manager',
        'gk_install_builder.features.certificate_manager',
        # Integration modules
        'gk_install_builder.integrations',
        'gk_install_builder.integrations.api_client',
        'gk_install_builder.integrations.keepass_handler'
    ],
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
    strip=True,  # Strip debug symbols to reduce size
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
    strip=True,  # Strip debug symbols from all binaries
    upx=True,
    upx_exclude=[],
    name='GK Install Builder',
) 