# -*- mode: python ; coding: utf-8 -*-
block_cipher = None
a = Analysis(
    ['gui_launch.py'],
    pathex=['.'],
    binaries=[],
    datas=[('rmidi/profiles', 'rmidi/profiles'), ('tools', 'tools')],
    hiddenimports=['rtmidi', 'mido.backends.rtmidi', 'yaml',
                   'rmidi.targets.resolve_target', 'rmidi.targets.aftereffects_target',
                   'rmidi.targets.premiere_target', 'rmidi.targets.logic_target',
                   'rmidi.targets.macos_target', 'rmidi.targets.keystroke_base',
                   'rmidi.autoswitch', 'rmidi.perms', 'Quartz', 'AppKit', 'Foundation', 'objc'],
    hookspath=[], runtime_hooks=[], excludes=['tkinter', 'matplotlib', 'numpy'],
    win_no_prefer_redirects=False, win_private_assemblies=False,
    cipher=block_cipher, noarchive=False)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='rmidi',
          debug=False, bootloader_ignore_signals=False, strip=False,
          upx=False, console=False, target_arch=None, codesign_identity=None,
          entitlements_file=None)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=False, name='rmidi')
app = BUNDLE(coll, name='rmidi.app', icon='build_icon.icns',
             bundle_identifier='com.rmidi.app',
             version='1.2.4',
             info_plist={
                'CFBundleName': 'rmidi',
                'CFBundleDisplayName': 'rmidi',
                'CFBundleShortVersionString': '1.2.4',
                'CFBundleVersion': '1.2.4',
                'NSHighResolutionCapable': True,
                'LSMinimumSystemVersion': '11.0',
                'LSApplicationCategoryType': 'public.app-category.video',
                'NSAppleEventsUsageDescription': 'rmidi controls DaVinci Resolve.',
             })
