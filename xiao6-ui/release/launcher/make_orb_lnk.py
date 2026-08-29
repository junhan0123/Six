import os
import pythoncom
from win32com.shell import shell

desktop   = r'F:\桌面'
lnk_path  = os.path.join(desktop, '打开语音球.lnk')
target    = r'C:\Windows\System32\wscript.exe'
args      = r'"G:\ZhuangZhou\zhuangzhou-ui\launcher\open-orb.vbs"'
wd        = r'G:\ZhuangZhou\zhuangzhou-ui\launcher'
icon      = r'G:\ZhuangZhou\zhuangzhou-ui\launcher\electron-bin\electron.exe'
desc      = '一键打开小6 语音球（自动检查后端与前端依赖）'

shortcut = pythoncom.CoCreateInstance(
    shell.CLSID_ShellLink, None,
    pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
shortcut.SetPath(target)
shortcut.SetArguments(args)
shortcut.SetWorkingDirectory(wd)
shortcut.SetDescription(desc)
shortcut.SetIconLocation(icon, 0)
shortcut.SetShowCmd(1)  # SW_SHOWNORMAL

persist = shortcut.QueryInterface(pythoncom.IID_IPersistFile)
persist.Save(lnk_path, 0)
print('created:', lnk_path)
print('exists :', os.path.exists(lnk_path))
print('size   :', os.path.getsize(lnk_path), 'bytes')
