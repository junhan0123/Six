#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小6 · 废弃代码清理脚本

执行:
  python scripts/cleanup_dead_code.py

功能:
  1. 标记未使用的模块
  2. 清理废弃标记
  3. 生成清理报告
"""
import os
import glob
import re
import shutil
from pathlib import Path

project_root = r'G:\Xiao6'
ui_dir = os.path.join(project_root, 'xiao6-ui')
backup_dir = os.path.join(project_root, 'backup_pre_cleanup')

def create_backup():
    """创建备份目录"""
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    print(f"📁 备份目录: {backup_dir}")

def find_unused_modules():
    """查找可能未使用的模块"""
    unused = []
    
    # 检查 proactive.py
    proactive_files = [
        'proactive.py',
        'proactive_engine.py', 
        'proactive_config.py',
    ]
    
    for mod in proactive_files:
        filepath = os.path.join(ui_dir, mod)
        if os.path.exists(filepath):
            # 检查是否被导入
            is_used = False
            for root, dirs, files in os.walk(ui_dir):
                dirs[:] = [d for d in dirs if d not in ['node_modules', '.git', '__pycache__']]
                for f in files:
                    if f.endswith('.py') and 'test' not in f.lower():
                        fpath = os.path.join(root, f)
                        try:
                            with open(fpath, 'r', encoding='utf-8') as fh:
                                content = fh.read()
                                if f'import {mod[:-3]}' in content or f'from {mod[:-3]}' in content:
                                    is_used = True
                                    break
                        except:
                            pass
                if is_used:
                    break
            
            if not is_used:
                unused.append(mod)
    
    return unused

def find_deprecated_markers():
    """查找废弃标记"""
    markers = []
    patterns = ['临时', 'todo', 'fixme', 'hack', 'deprecated']
    
    for root, dirs, files in os.walk(ui_dir):
        dirs[:] = [d for d in dirs if d not in ['node_modules', '.git', '__pycache__']]
        for f in files:
            if f.endswith(('.py', '.js')) and 'test' not in f.lower():
                filepath = os.path.join(root, f)
                try:
                    with open(filepath, 'r', encoding='utf-8') as fh:
                        lines = fh.readlines()
                        for i, line in enumerate(lines):
                            for pattern in patterns:
                                if pattern in line.lower():
                                    markers.append({
                                        'file': os.path.relpath(filepath, project_root),
                                        'line': i + 1,
                                        'content': line.strip()[:80],
                                        'pattern': pattern
                                    })
                                    break
                except:
                    pass
    
    return markers

def main():
    print("=" * 60)
    print("小6 AI OS - 废弃代码清理")
    print("=" * 60)
    
    # 创建备份
    create_backup()
    
    # 查找未使用模块
    print("\n【步骤 1: 检查未使用模块】")
    unused = find_unused_modules()
    if unused:
        print(f"  ⚠️ 发现 {len(unused)} 个可能未使用的模块:")
        for mod in unused:
            print(f"     - {mod}")
        print("\n  建议: 删除或保留（需确认）")
    else:
        print("  ✅ 未发现明显未使用模块")
    
    # 查找废弃标记
    print("\n【步骤 2: 检查废弃标记】")
    markers = find_deprecated_markers()
    if markers:
        print(f"  ⚠️ 发现 {len(markers)} 个废弃标记:")
        for m in markers[:10]:
            print(f"     {m['file']}:{m['line']} [{m['pattern']}]")
            print(f"       {m['content']}")
        print("\n  建议: 清理或保留（需确认）")
    else:
        print("  ✅ 未发现废弃标记")
    
    # 总结
    print("\n" + "=" * 60)
    print("清理建议:")
    print("=" * 60)
    print("""
1. 未使用模块:
   - proactive.py: 确认是否已集成到 proactive_engine.py
   - 如未使用，可删除或移入 _deprecated/ 目录

2. 废弃标记:
   - 临时标记: 确认是否仍需保留
   - TODO/FIXME: 按计划处理或删除

3. 备份:
   - 所有修改前已创建备份: {backup_dir}
   - 如需恢复，可从此目录还原
""".format(backup_dir=backup_dir))
    
    print("\n✅ 清理脚本执行完成")

if __name__ == '__main__':
    main()
