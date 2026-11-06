# PointLab Studio v1.1.1

基于 PySide6、pygfx/wgpu 和 Open3D 的 macOS 点云工作站，支持点云浏览、裁剪、测量、滤波、配准、网格重建与工程保存。提供深色和浅色主题。

## 直接运行 APP

从 [GitHub Releases](https://github.com/HOOK290/PointLabStudio/releases/tag/v1.1.1) 下载 `PointLabStudio-v1.1.1-macOS-arm64.zip`，解压后将整个 `PointLabStudio.app` 拖入“应用程序”或用户目录下的 `Applications`，双击运行，无需安装 Python。可直接将这个安装包发给其他人，`SHA256SUMS.txt` 提供校验值。

支持 Apple Silicon（arm64）Mac，需要 macOS 26 或更新版本，使用 Metal 图形后端。APP 已包含 Python、原生运行库和 LAZ/E57 读取依赖，不需要保留源码或安装 Homebrew。Intel Mac 需要另行构建，此安装包不适用。Windows 版本请参阅原仓库的 [main 分支](https://github.com/jarviscccwl/PointLabStudio/tree/main)。

## 从 Git 安装

环境要求：Apple Silicon Mac、macOS 26 或更新版本、Git、Python 3.12，以及 Xcode Command Line Tools。

在终端中执行：

```sh
git clone --branch macos https://github.com/HOOK290/PointLabStudio.git
cd PointLabStudio
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r packaging/requirements-macos.txt
.venv/bin/python packaging/prepare_macos.py
.venv/bin/python run.py
```

之后在项目目录执行 `.venv/bin/python run.py` 即可启动，无需手动激活虚拟环境。也可直接打开文件或目录：

```sh
.venv/bin/python run.py "/Users/你的用户名/点云目录"
```

更新项目时，在项目目录执行 `git pull`，再运行上述依赖安装及环境准备命令。获取固定版本可在克隆后执行 `git checkout v1.1.1`。

## 使用

- **逐帧浏览**：拖入文件或文件夹，或在空场景点击「打开点云或文件夹…」选择导入方式。文件夹保留真实层级，点击展开/折叠；文件按名称自然排序，默认显示第一帧。点击点云、按方向键或中央上方 ‹ / › 切换，上一帧自动隐藏。文件按需后台加载，并预取相邻帧。新导入的数据追加到当前场景。
- **叠加显示**：手动勾选其他点云后，切帧时仍保留显示；取消勾选即可隐藏。右键「临时显示」只显示所选项，「固定叠加显示」在切帧时保留。显示、隐藏、固定与取消固定均作用于全部所选点云及所选文件夹中的点云。双击聚焦，右键可重新加载。
- **文件管理**：从行尾或列表空白处按住左键拖动框选，矩形碰到的可见行都会选中，松开只选中。右键删除可选「仅移出工程」或「移到废纸篓」；选中文件夹时，磁盘删除包含其全部内容。支持整批撤销，恢复遇到同名文件会停止并保留数据，处理冲突后可重试。
- **移动与重命名**：拖住名称或图标，落在文件夹行可选择仅调整工程分组，或同步移动硬盘原文件；落在其他区域只追加打开。右键重命名会修改实际名称并同步路径，同名目标不会被覆盖。「打开文件所在文件夹」可在 Finder 中定位实际源文件，没有独立源文件的处理结果会禁用此项。
- **双窗格**：点击中央上方「双窗格」，左侧当前帧、右侧上一帧或下一帧。默认视角联动，可取消后分别旋转、平移和缩放。处理、选点与裁剪作用于左侧，右侧用于参考。
- **视角**：自由视角下，左键旋转、右键/中键平移、滚轮缩放、双击设置旋转中心。Mac 版已调整上下旋转方向；滚轮向前推放大、向后拨缩小，缩放与左侧列表滚动方向均不随系统「自然滚动」变化。固定视角锁定当前 Z 高度，拖动水平转向，滚轮沿当前朝向在 XY 平面平滑移动。
- **裁剪**：点击裁剪按钮，选择「按包围盒」，关闭面板后拖动橙色手柄。松开更新点数与范围，Esc 取消拖动。正对视线的轴需先旋转视图。
- **保存框内点**：「工程 → 导出裁剪内点云」。裁剪只改变显示；「导出当前点云」仍导出完整数据。要生成可继续处理的新点云，使用「处理 → 盒裁切」，默认沿用当前裁剪框。
- **测量与选择**：测量工具连续加点；选点查看属性；框选后在「处理」中提取或删除。测量可导出 CSV，Esc 退出工具。
- **处理**：当前帧加载完成后使用「处理」菜单。自动显示新结果、隐藏未固定的原数据，支持撤销/重做。配准或距离分析所选的参考帧若未加载，会先后台读取。底部可取消任务；部分原生算法需等待当前计算阶段结束。 处理结果不会自动保存，退出前请导出或保存工程。
- **网格**：Poisson 重建后，在「工程 → 网格结果」中显示/隐藏、移除或导出 PLY。网格随工程保存。
- **工程**：支持新建、打开、保存、另存为和关闭；标题中的 `*` 表示未保存。打开工程会先提示保存当前更改，再替换当前工作区；拖入新数据仍为追加。首次保存选择位置，之后直接写入当前文件。保存 `.pls` 和同名 `.assets` 文件夹，记录分组、源路径、显示/固定状态、相机、裁剪、派生点云及网格。移动工程时保留二者和源点云。资产按内容复用，保存失败不覆盖上次已保存的数据；旧资产版本保留以保护其他工程引用。

| 快捷键 | 操作 | 快捷键 | 操作 |
| --- | --- | --- | --- |
| Command+O | 打开文件 | Command+S / Control+S | 保存工程 |
| Command+Shift+O | 打开文件夹 | Command+P | 打开工程 |
| Command+E | 导出当前点云 | Command+Z / Command+Shift+Z | 撤销 / 重做 |
| R | 重置视角 | B | 开关裁剪 |
| C | 循环颜色 | + / − | 点大小 |
| ← / ↑ | 上一帧 | → / ↓ | 下一帧 |
| Space | 显示/隐藏选中点云 | H | 完整快捷键 |

Qt 在 Mac 上会将可移植的 Ctrl 快捷键映射为 Command；部分提示文字仍显示 Ctrl。物理 Control+S 也可保存工程。

## 格式与限制

- 读取：BIN、PLY、PCD、XYZ/XYZN/XYZRGB、PTS、LAS、LAZ、E57、NPY/NPZ、TXT/CSV。
- 导出：PLY、PCD、LAS、PTS、XYZ；字段保真优先选 PLY/PCD。
- APP 和上述源码安装命令均包含 `laspy`、`lazrs`、`pye57`，无需另外安装 LAZ/E57 读取依赖。
- 大文件可能先显示采样预览；预览上执行的处理和导出仅包含已加载点，界面会标注。
- 最近源帧缓存以 8 帧、512 MB 为回收预算；当前帧、相邻帧和手动叠加项优先保留，派生结果不自动回收。状态栏点数表示已加载的数据。
- 坐标按米显示，不自动识别或转换原始数据单位。颜色条与直方图基于原始点云。
- 体素降采样保留颜色/强度均值，其他属性不参与聚合；随机采样保留逐点属性。DBSCAN 超过 15 万点时抽样聚类，再用最近邻传播标签。
- LAS 导出采用 1.2 格式、毫米精度，分类值限 0–31；更丰富的标签使用 PLY/PCD。LAZ/E57 当前只支持读取。
- 本次格式样本验证覆盖 PLY/PCD/LAS，未对 LAZ/E57 做端到端样本验证。

## 目录与常见问题

`apps/` 应用入口 · `core/` 数据与算法 · `ui/` 界面 · `resources/` 图标 · `packaging/` APP 构建配置。`.venv/`、`build/` 和 `dist/` 不上传 Git 仓库，APP 作为 GitHub Release 附件发布。

设置、日志和渲染缓存默认位于 `~/Library/Application Support/PointLabStudio/`；可用 `POINTLAB_HOME` 指定其他位置。删除临时源码和构建环境不影响已安装应用；删除用户数据目录会重置设置。
操作失败请展开底部「日志」；启动失败查看该目录下的 `logs/pointlab.log`。若提示缺少依赖，重新执行安装及环境准备命令；若渲染不可用，检查系统与处理器是否符合要求。

本构建采用本地 ad-hoc 签名，尚未使用 Apple Developer ID 签名或进行公证。从网上下载后，macOS 可能提示开发者无法验证，请根据系统提示决定是否允许启动。

命令行：`.venv/bin/python -m apps.cli --help`。

## 构建 APP

在 Apple Silicon Mac、Python 3.12 环境中执行：

```sh
.venv/bin/python -m pip install -r packaging/requirements-macos.txt
.venv/bin/python -m unittest discover -s tests -v
./packaging/build-macos.command
```

生成 `dist/PointLabStudio.app`。构建脚本生成 Mac 图标，将 Open3D 的 libusb 依赖改为随应用携带的相对路径，再通过 PyInstaller 打包应用并验证 arm64 签名；不需要另外分发源码或依赖目录。不要直接分发 `build/` 中的中间产物。更多细节见 [packaging/README-macOS.md](packaging/README-macOS.md)。

本版 160 项测试中 159 项通过、1 项原生废纸篓测试默认跳过并已单独实测通过；在 macOS 27.2 / Apple M5 上验证独立应用、Metal 显示、降采样、导出、工程恢复及两种保存快捷键。

## 更新记录

### v1.1.1 · 2026-11-06

- 新增 Apple Silicon 原生独立 APP、Mac 图标、用户数据目录及可复现构建脚本，包含 Python 与运行依赖。
- 新增文件夹层级、空目录、左键框选和整组显示/固定叠加，支持右键批量移除或移到废纸篓及安全撤销。
- 新增工程内分组、磁盘移动/重命名、路径同步、同名保护及 Finder 源文件定位。
- 完善新建、打开、保存、另存为、关闭和未保存提示；保存分组与显示状态，并保护保存失败前的工程资产。
- 支持点击、Command+S 和物理 Control+S 保存；空场景可选择打开点云文件或文件夹。
- 修正 Mac 左键上下旋转方向，滚轮与侧栏滚动不再随系统「自然滚动」变化。

### v1.1.0 · 2026-10-31

- 新增按需逐帧加载、自动切换显示、相邻帧双窗格对比与视角联动。
- 提升浅色主题的文字、控件、直方图、无着色点云与工具线条对比度。
- 新增固定高度平滑行走、可拖动裁剪框及裁剪内点云导出。
- 完善网格管理、工程恢复、跨盘保存、任务取消与安全关闭。
- 优化侧栏排版，精简项目目录，文档统一到 README。
- 修复粗配准衔接 ICP、抽样法线对应、任务取消及预览状态保存；降低法线与聚类的峰值内存。
- 修复 LAS 范围/分类信息与 E57 多扫描位姿、颜色读取；提供 Windows 单文件 EXE。
- 修复系统临时目录不可写时 EXE 无法启动的问题，自动选择可写目录并在退出后清理。
