# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
datas=[]; binaries=[]; hiddenimports=[]
for package in ["PIL","reportlab"]:
    d,b,h=collect_all(package)
    datas += d; binaries += b; hiddenimports += h
a=Analysis(["magazine_imposer.py"], pathex=[], binaries=binaries, datas=datas,
           hiddenimports=hiddenimports, hookspath=[], hooksconfig={},
           runtime_hooks=[], excludes=[], noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz, a.scripts, a.binaries, a.datas, [], name="PrintMagazineBD_A3_Imposer",
        debug=False, bootloader_ignore_signals=False, strip=False, upx=True, console=False)
