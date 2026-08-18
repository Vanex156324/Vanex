# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['UI.py'],
    pathex=[''],
    binaries=[],
    datas=[
    ('web/', 'web/'),
    ('windows_info', 'windows_info/')
    ],
    hiddenimports=[
    ('keyinfo.key_display'),
    ('Radar.radar_display'),
    ('Status_info.Status_Display'),
    ('windows_info.windows_Display')
    ],
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
    name='Vanex',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)