#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
照片分类工具 - EXE打包脚本（针对 Card Tools.py）
使用 PyInstaller 将 Python 程序打包为独立 exe
"""

import os
import sys
import subprocess
import shutil
import time


def check_dependencies() -> bool:
    required = ["PyQt5", "pyinstaller"]
    missing = []
    for name in required:
        try:
            __import__(name)
            print(f"✅ {name} 已安装")
        except ImportError:
            missing.append(name)
            print(f"❌ {name} 未安装")
    if missing:
        print("正在安装缺失依赖：", ", ".join(missing))
        for name in missing:
            subprocess.check_call([sys.executable, "-m", "pip", "install", name])
    return True


def build_exe() -> bool:
    main_script = "Card Tools.py"
    if not os.path.exists(main_script):
        print(f"错误：找不到主程序文件 {main_script}")
        return False

    assets_dir = os.path.join(os.getcwd(), "assets")
    icon_path = os.path.join(assets_dir, "app.ico")
    icon_arg = f"--icon={icon_path}" if os.path.exists(icon_path) else "--icon=NONE"

    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name=照片分类工具",
        icon_arg,
        "--add-data=data;data",
        "--hidden-import=PyQt5.sip",
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=PyQt5.QtWidgets",
        "--collect-all=PyQt5",
        "--clean",
        "--noconfirm",
        main_script,
    ]

    print("执行命令:", " ".join(cmd))
    start = time.time()
    subprocess.run(cmd, check=True)
    print(f"PyInstaller 完成，用时 {time.time()-start:.2f}s")

    exe_path = os.path.join("dist", "照片分类工具.exe")
    if not os.path.exists(exe_path):
        print("❌ 未找到生成的 exe")
        return False

    # 复制 data 到 dist
    if os.path.exists("data"):
        dist_data = os.path.join("dist", "data")
        if os.path.exists(dist_data):
            shutil.rmtree(dist_data)
        shutil.copytree("data", dist_data)
        print("✅ 已复制 data/ 到 dist/")

    # 写入简要说明
    readme_path = os.path.join("dist", "使用说明.txt")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("# 使用说明\n\n双击 照片分类工具.exe 运行。\n")

    # 生成精简发布目录
    release_dir = os.path.join("dist", "release")
    if os.path.exists(release_dir):
        shutil.rmtree(release_dir)
    os.makedirs(release_dir, exist_ok=True)
    shutil.copy2(exe_path, os.path.join(release_dir, os.path.basename(exe_path)))
    if os.path.exists(os.path.join("dist", "data")):
        shutil.copytree(os.path.join("dist", "data"), os.path.join(release_dir, "data"))
    shutil.copy2(readme_path, os.path.join(release_dir, "使用说明.txt"))
    print("✅ 已创建 dist/release 发布目录")
    return True


def main():
    print("=" * 60)
    print("打包 Card Tools.py 为 EXE")
    print("=" * 60)
    check_dependencies()
    ok = False
    try:
        ok = build_exe()
    except subprocess.CalledProcessError as e:
        print("❌ PyInstaller 执行失败", e)
    except Exception as e:
        print("❌ 打包异常", e)
    print("完成" if ok else "失败")


if __name__ == "__main__":
    main()


