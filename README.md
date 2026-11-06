# PointLab Studio · macOS 版

基于 PySide6、pygfx/wgpu 和 Open3D 的桌面点云工作站。此 `macos` 分支提供 Apple Silicon 原生应用，保留点云浏览、裁剪、测量、滤波、地面提取、配准、网格重建、工程保存及深色／浅色主题。

Windows 版本请参阅 [`main` 分支](https://github.com/jarviscccwl/PointLabStudio/tree/main)。

## 下载与安装

在 [macOS Release](https://github.com/HOOK290/PointLabStudio/releases/tag/v1.1.0-macos.1) 下载：

- `PointLabStudio-v1.1.0-macOS-arm64.zip`：包含完整的 `PointLabStudio.app`。
- `SHA256SUMS.txt`：安装包的 SHA-256 校验值。

解压后，将 **整个 `PointLabStudio.app`** 拖入“应用程序”或用户目录下的 `Applications` 文件夹，然后双击运行。应用已包含 Python 与运行依赖，不需要安装 Python、uv、Homebrew 或保留源码。

| 项目 | 要求 |
| --- | --- |
| 处理器 | Apple Silicon，arm64 |
| 系统 | macOS 26 或更新版本 |
| 图形后端 | Metal，由 wgpu 自动选择 |
| 本次验证环境 | macOS 27.2、Apple M5 |

本构建采用本地 ad-hoc 签名，尚未使用 Apple Developer ID 签名或进行公证。从网上下载后，macOS 可能提示开发者无法验证；请根据系统安全提示决定是否允许启动。Intel Mac 需要另行构建 x86_64 版本，本安装包不适用。

## 基本使用

1. 点击“打开”或将点云文件／文件夹拖入窗口。
2. 文件夹按自然文件名排序；点击左侧列表、上方前后按钮或方向键切换帧。
3. 使用“处理”菜单进行降采样、滤波、裁剪、地面提取或配准。完成后会在场景中添加结果，不会覆盖原始文件。
4. 需要保留结果时，导出点云或保存工程。

### 鼠标操作

| 操作 | 功能 |
| --- | --- |
| 按住左键拖动 | 旋转视角；Mac 版已调整上下旋转方向 |
| 按住右键或中键拖动 | 平移 |
| 滚轮向前推，远离自己 | 放大 |
| 滚轮向后拨，朝向自己 | 缩小 |
| 双击点云 | 设置旋转中心 |
| 按住 Shift 旋转 | 精细调整 |

**滚轮缩放方向固定，不随 macOS 的“自然滚动”开关变化。** 普通滚轮和高分辨率像素滚动均作方向归一化；固定高度模式的滚轮前后移动也保持一致。

### 保存处理结果

**处理结果不会自动保存到磁盘。** 地面提取、滤波、裁剪等结果先保存在当前会话内存中，退出前请手动保存：

- **导出结果**：在左侧选中处理后的点云，选择“工程 → 导出当前点云”，或按 `⌘E`，保存为 PLY、PCD、LAS 等格式。
- **保存工作区**：按 `⌘S` 保存 `.pls` 工程。派生点云和网格会写入同名 `.assets` 文件夹，工程同时记录视角、裁剪及显示状态。
- 移动工程时，保留 `.pls`、同名 `.assets` 文件夹及原始点云；源文件仍由工程引用。

关闭应用会丢失尚未保存或导出的处理结果。

### 快捷键

| 快捷键 | 功能 | 快捷键 | 功能 |
| --- | --- | --- | --- |
| `⌘O` | 打开点云 | `⌘⇧O` | 打开文件夹 |
| `⌘P` | 打开工程 | `⌘S` | 保存工程 |
| `⌘E` | 导出当前点云 | `⌘L` | 展开／收起日志 |
| `⌘Z` | 撤销 | `⌘⇧Z` | 重做 |
| `R` | 重置视角 | `B` | 开关裁剪 |
| `C` | 循环颜色 | `+`／`−` | 调整点大小 |
| 方向键 | 切换前后帧 | 空格 | 显示／隐藏选中点云 |
| `H` | 完整快捷键帮助 | `Esc` | 退出交互工具 |

Qt 在 Mac 上会将可移植的 Ctrl 快捷键映射为 Command；部分上游提示文字仍显示 Ctrl。

## 格式与功能说明

- 读取：BIN、PLY、PCD、XYZ／XYZN／XYZRGB、PTS、LAS、LAZ、E57、NPY／NPZ、TXT／CSV。
- 导出：PLY、PCD、LAS、PTS、XYZ；优先使用 PLY／PCD 保留字段。LAZ／E57 当前仅支持读取。
- 安装包已包含 `laspy`、`lazrs`、`pye57`，不需要额外安装 LAZ／E57 读取依赖。
- 支持相邻帧双窗格、视角联动、固定叠加、测量、选点及包围盒裁剪。
- 大文件可能先显示采样预览；基于预览进行的处理和导出只包含已加载点，界面会标注。
- 最近源帧缓存以 8 帧、512 MB 为预算；当前帧、相邻帧及固定叠加项优先保留。派生结果不会自动回收。
- 坐标按米显示，不会自动识别或换算数据单位。LAS 导出使用 1.2 格式、毫米精度，分类值限 0–31。

## 设置、日志与故障排查

用户数据目录为 `~/Library/Application Support/PointLabStudio/`，其中包括 `settings.json`、`logs/pointlab.log` 和 `pygfx/` 渲染缓存。`POINTLAB_HOME` 可覆盖此路径。

删除源码、虚拟环境或构建目录不会影响已安装应用；删除上述用户数据目录则会重置设置。处理出错时，先展开窗口底部“日志”。

## 从源码运行与构建

仅开发者需要这些步骤。准备 Apple Silicon Mac、Python 3.12、uv 和 Xcode Command Line Tools，然后执行：

```sh
git clone --branch macos https://github.com/HOOK290/PointLabStudio.git
cd PointLabStudio
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r packaging/requirements-macos.txt
.venv/bin/python packaging/prepare_macos.py
.venv/bin/python run.py
```

构建独立应用：

```sh
.venv/bin/python -m unittest discover -s tests -v
./packaging/build-macos.command
```

生成 `dist/PointLabStudio.app`。构建脚本会从项目原始 SVG 生成 Mac 图标，将 Open3D 的 libusb 依赖改为随应用携带的相对路径，再通过 PyInstaller 生成并校验 arm64 应用签名，不依赖本机 Homebrew 库。

更多构建细节见 [packaging/README-macOS.md](packaging/README-macOS.md)。构建结果通过 Release 附件分发，`.venv/`、`build/`、`dist/` 不提交到 Git。

## 本版验证

- 18 项自动化测试通过，包括点云读写、降采样、用户设置和鼠标交互回归。
- 已实际验证独立应用启动、Metal 点云显示、降采样、`⌘E` 导出和工程恢复。
- 临时移开整个源码目录后，已安装应用仍能独立启动并加载点云。
- LAZ／E57 依赖已打包；本次格式回归使用 PLY、PCD、LAS，未对 LAZ／E57 做端到端样本验证。

## macOS 更新记录

### v1.1.0-macos.1 · 2026-11-06

- 新增 Apple Silicon 原生 `.app`、Mac 图标和可复现的打包脚本。
- 配置、日志和 GPU 缓存使用 macOS 用户数据目录。
- 补齐并打包 Open3D 的 libusb 原生依赖。
- 修正 Mac 左键上下旋转方向。
- 滚轮缩放方向不再随系统“自然滚动”开关变化。
- 保留上游 v1.1.0 的点云浏览、处理和工程功能。
