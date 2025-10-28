# 照片分类工具

一个基于 PyQt5 的本地图片分类与重命名桌面工具。支持从源文件夹批量筛选、重命名并按证件类型输出到目标路径；提供打包脚本，一键生成 Windows 可执行文件（.exe）。

## 功能
- 可视化界面（PyQt5）。
- 拖拽/选择源目录与目标目录。
- 证件类型列表可编辑、排序，自动保存到 `data/card.txt`。
- 自定义命名格式，默认值保存在 `data/name*.txt`。
- 打包脚本：`build_exe.py`（基于 PyInstaller）。

## 环境要求
- Windows 10/11（建议）
- Python 3.8+（运行源码时需要）

## 开发与测试环境
- Windows 10 64 位
- Python 3.9.9
- PyQt5 5.15.10

## 获取代码
- 方式一：在 GitHub 上点击 Code → Download ZIP，解压后进入项目目录。
- 方式二（推荐）：使用 Git 克隆仓库并进入目录：

```powershell
git clone https://github.com/ZhaoSirAdmin/Card-Tools.git
cd Card-Tools
```

仓库地址：[`https://github.com/ZhaoSirAdmin/Card-Tools`](https://github.com/ZhaoSirAdmin/Card-Tools)

## 依赖与安装
必需软件：
- Python 3.8–3.12（64 位）
- pip（随 Python 一起安装）

安装步骤（PowerShell）：
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
# 如在国内，可使用镜像：
# pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

## 快速开始（运行源码）
1) 启动应用：

```powershell
python "Card Tools.py"
```

首次运行会在 `data/` 下自动创建配置文件：
- `card.txt`：证件类型列表
- `path.txt`：默认目标路径
- `name.txt`：命名格式候选
- `name_default.txt`：默认命名格式

## 使用指南（图形界面）
1) 选择文件夹：
   - 左中部依次设置【源文件夹】与【目标文件夹】。
   - 支持在输入框中拖拽路径或点击按钮选择。
   - 目标路径会自动保存到 `data/path.txt`，下次自动填充。

2) 选择证件类型：
   - 左侧列表勾选需要的证件类型（可多选）。
   - 可用按钮【全选/取消/新增/删除】管理列表；也可拖拽排序。
   - 点击列表项左侧编号区域可快速调整顺序（顺序会影响文件对应关系）。

3) 设置命名格式：
   - 右侧“图片命名格式”中选择或输入命名模板，必须包含占位符 `{n}`（数字序号）。
   - 例如：`图片 {n}`、`IMG_{n}`、`{n}号照片`。
   - 双击列表项可取消选择、恢复为默认；点击【设为默认】可保存为系统默认（写入 `data/name_default.txt`）。

4) 输入姓名+身份证号：
   - 中部“大文本框”每行一个，格式：`姓名+身份证号`，如：`李四+110101199001011234`。
   - 身份证要求18位，最后一位支持 X/x（将自动标准化为大写 X）。

5) 开始处理：
   - 点击【开始处理】，程序将：
     - 按所选命名格式从源目录匹配并按序号排序图片（仅匹配扩展名：jpg/jpeg/png/bmp/gif/tiff/tif/webp/heic/heif/raw/cr2/nef/arw/ico/jfif/pjpeg/pjp）。
     - 校验数量：总图片数必须等于“人员数 × 选中证件类型数”。
     - 在目标目录创建 `输出目录`（若存在则创建 `输出目录1`、`输出目录2`…）。
     - 为每个人创建子目录 `姓名+身份证号/`，复制并重命名图片为：`姓名+身份证号-证件类型.原扩展名`。
   - 过程可在底部日志区域查看，支持【导出日志】保存为 txt。

### 输入规范与示例
- 命名格式与源文件示例：
  - 选择模板：`图片 {n}` → 源文件应类似：`图片 1.jpg`、`图片 2.jpg`…
  - 选择模板：`IMG_{n}` → 源文件应类似：`IMG_1.png`、`IMG_2.png`…
- 姓名+身份证号示例（每行一条）：
  - `张三+110101199001011234`
  - `李四+11010119951212345X`

### 结果说明
- 目标目录生成：`输出目录/姓名+身份证号/姓名+身份证号-证件类型.扩展名`
- 证件类型、命名格式和默认命名会分别保存在 `data/card.txt`、`data/name.txt`、`data/name_default.txt`。

## 打包为 EXE
使用内置脚本（会自动安装缺失的依赖并调用 PyInstaller）：

```powershell
python build_exe.py
```

构建完成后在 `dist/` 下生成：
- `照片分类工具.exe`
- `data/`（运行所需配置）
- `使用说明.txt`
- `release/`（精简发布目录，可直接发给用户）

可选：为程序设置图标，将 `assets/app.ico` 放入项目后再次打包。

## 目录结构
```
2025-9-3/
├─ Card Tools.py        # 主程序（PyQt5 GUI）
├─ build_exe.py         # 一键打包脚本（PyInstaller）
├─ data/                # 配置文件目录（运行时自动创建或更新）
├─ requirements.txt     # 依赖清单
└─ README.md
```

## 常见问题
- 无法启动：请用 PowerShell 执行并确保已安装依赖，且路径不含特殊字符。
- 中文路径/文件名：本项目已针对 Windows 做路径规范化处理，如仍异常，请将项目移动到英文目录重试。
- 打包后双击无反应：在命令行运行 `dist/照片分类工具.exe` 以查看错误输出；或重新执行 `python build_exe.py`。

## 许可证
未设置。如需开源，请补充 `LICENSE` 文件（例如 MIT）。



