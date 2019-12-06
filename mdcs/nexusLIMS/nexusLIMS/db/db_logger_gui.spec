# -*- mode: python ; coding: utf-8 -*-
# Run this file with Pyinstaller v3.5, on Python 3.4.4 (32-bit) via:
# C:\Python34-32\Scripts\pyinstaller.exe db_logger_gui.spec

block_cipher = None


a = Analysis(['db_logger_gui.py'],
             pathex=['C:\\Users\\***REMOVED***\\git_repos\\NexusMicroscopyLIMS\\mdcs\\nexusLIMS\\nexusLIMS\\db'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries + [
              ('logo_bare.ico', 
              'C:\\Users\\***REMOVED***\\git_repos\\NexusMicroscopyLIMS\\mdcs\\nexusLIMS\\nexusLIMS\\db\\logo_bare.ico', 
              'DATA'),
              ('logo_text_250x100.png',
              'C:\\Users\\***REMOVED***\\git_repos\\NexusMicroscopyLIMS\\mdcs\\nexusLIMS\\nexusLIMS\\db\\logo_text_250x100.png',
              'DATA')],
          a.zipfiles,
          a.datas,
          [],
          name='db_logger_gui',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True, 
          icon='logo_bare.ico')
