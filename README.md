# PointLab Studio v1.1.0

基于 PySide6、pygfx/wgpu 和 Open3D 的 Windows 点云工作站，支持点云浏览、裁剪、测量、滤波、配准、网格重建与工程保存。提供深色和浅色主题。

## 直接运行 EXE

从 GitHub Releases 下载 `PointLabStudio-v1.1.0-Windows-x64.exe`，双击运行，无需安装 Python。可直接将这个 EXE 发给其他人。

支持 Windows 10/11 64 位，需要支持 Vulkan 或 DirectX 12 的显卡及驱动。单文件启动时会自动选择可写目录并解压内置运行库，请稍候；正常退出后清理临时运行文件。EXE 已包含 LAZ/E57 读取依赖。

## 从 Git 安装

环境要求：Windows 10/11 64 位、Git、Python 3.12 64 位，以及支持 Vulkan 或 DirectX 12 的显卡和驱动。

在 PowerShell 中执行：

```powershell
git clone https://github.com/jarviscccwl/PointLabStudio.git
cd PointLabStudio
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.\start.bat
```

之后双击 `start.bat` 即可启动，无需手动激活虚拟环境。也可直接打开文件或目录：

```powershell
.venv\Scripts\python.exe run.py "D:\点云目录"
```

更新项目时，在项目目录执行 `git pull`，再运行上述依赖安装命令。获取固定版本可在克隆后执行 `git checkout v1.1.0`。

## 使用

- **逐帧浏览**：拖入文件夹后按文件名自然排序，默认显示第一帧。点击列表、按方向键或中央上方 ‹ / › 切换，上一帧自动隐藏。文件按需后台加载，并预取相邻帧。
- **叠加显示**：手动勾选其他点云后，切帧时仍保留显示；取消勾选即可隐藏。要保留当前帧，可右键「固定叠加显示」。双击聚焦，右键可移除或重新加载。
- **双窗格**：点击中央上方「双窗格」，左侧当前帧、右侧上一帧或下一帧。默认视角联动，可取消后分别旋转、平移和缩放。处理、选点与裁剪作用于左侧，右侧用于参考。
- **视角**：自由视角下，左键旋转、右键/中键平移、滚轮缩放、双击设置旋转中心。固定视角锁定当前 Z 高度，拖动水平转向，滚轮沿当前朝向在 XY 平面平滑移动。
- **裁剪**：点击裁剪按钮，选择「按包围盒」，关闭面板后拖动橙色手柄。松开更新点数与范围，Esc 取消拖动。正对视线的轴需先旋转视图。
- **保存框内点**：「工程 → 导出裁剪内点云」。裁剪只改变显示；「导出当前点云」仍导出完整数据。要生成可继续处理的新点云，使用「处理 → 盒裁切」，默认沿用当前裁剪框。
- **测量与选择**：测量工具连续加点；选点查看属性；框选后在「处理」中提取或删除。测量可导出 CSV，Esc 退出工具。
- **处理**：当前帧加载完成后使用「处理」菜单。自动显示新结果、隐藏未固定的原数据，支持撤销/重做。配准或距离分析所选的参考帧若未加载，会先后台读取。底部可取消任务；部分原生算法需等待当前计算阶段结束。
- **网格**：Poisson 重建后，在「工程 → 网格结果」中显示/隐藏、移除或导出 PLY。网格随工程保存。
- **工程**：保存 `.pls` 和同名 `.assets` 文件夹；移动工程时二者一起移动，并保留源点云。打开工程会将数据加入当前场景。

| 快捷键 | 操作 | 快捷键 | 操作 |
| --- | --- | --- | --- |
| Ctrl+O | 打开文件 | Ctrl+S | 保存工程 |
| Ctrl+E | 导出当前点云 | Ctrl+Z / Ctrl+Y | 撤销 / 重做 |
| R | 重置视角 | B | 开关裁剪 |
| C | 循环颜色 | + / − | 点大小 |
| ← / ↑ | 上一帧 | → / ↓ | 下一帧 |
| Space | 显示/隐藏选中点云 | H | 完整快捷键 |

## 格式与限制

- 读取：BIN、PLY、PCD、XYZ/XYZN/XYZRGB、PTS、LAS、NPY/NPZ、TXT/CSV。
- 导出：PLY、PCD、LAS、PTS、XYZ；字段保真优先选 PLY/PCD。
- LAZ/E57 读取需额外安装：`.venv\Scripts\python.exe -m pip install laspy lazrs pye57`。
- 大文件可能先显示采样预览；预览上执行的处理和导出仅包含已加载点，界面会标注。
- 最近源帧缓存以 8 帧、512 MB 为回收预算；当前帧、相邻帧和手动叠加项优先保留，派生结果不自动回收。状态栏点数表示已加载的数据。
- 坐标按米显示，不自动识别或转换原始数据单位。颜色条与直方图基于原始点云。
- 体素降采样保留颜色/强度均值，其他属性不参与聚合；随机采样保留逐点属性。DBSCAN 超过 15 万点时抽样聚类，再用最近邻传播标签。
- LAS 导出采用 1.2 格式、毫米精度，分类值限 0–31；更丰富的标签使用 PLY/PCD。LAZ/E57 当前只支持读取。

## 目录与常见问题

`apps/` 应用入口 · `core/` 数据与算法 · `ui/` 界面 · `resources/` 图标 · `packaging/` EXE 构建配置。`.venv/` 和 `dist/` 不上传 Git 仓库，EXE 作为 GitHub Release 附件发布。

设置、日志和渲染缓存默认位于 `%APPDATA%\PointLabStudio\`；可用 `POINTLAB_HOME` 指定其他位置。EXE 遇到用户数据目录不可写时，会自动回退到 EXE 旁的 `.PointLabStudio/`，保留该文件夹即可保留设置。
操作失败请展开底部「日志」；启动失败查看该目录下的 `logs/pointlab.log`。若提示缺少依赖，重新执行安装命令；若渲染不可用，检查显卡驱动。

EXE 会自动避开不可写的 `%TEMP%` / `%TMP%`。如果所有候选目录均不可写，请将 EXE 移到自己有写入权限的文件夹后再打开，无需修改系统权限。

命令行：`.venv\Scripts\python.exe -m apps.cli --help`。

## 构建 EXE

在 Windows 64 位、Python 3.12 环境中执行：

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
powershell -ExecutionPolicy Bypass -File packaging/build.ps1
```

生成 `dist/PointLabStudio-v1.1.0-Windows-x64.exe`。构建脚本先用 PyInstaller 打包应用，再用 Windows 自带的 .NET Framework 编译目录回退启动器；不需要另外分发源码或依赖目录。不要直接分发 `build/` 中的中间产物。

## 更新记录

### v1.1.0 · 2026-10-31

- 新增按需逐帧加载、自动切换显示、相邻帧双窗格对比与视角联动。
- 提升浅色主题的文字、控件、直方图、无着色点云与工具线条对比度。
- 新增固定高度平滑行走、可拖动裁剪框及裁剪内点云导出。
- 完善网格管理、工程恢复、跨盘保存、任务取消与安全关闭。
- 优化侧栏排版，精简项目目录，文档统一到 README。
- 修复粗配准衔接 ICP、抽样法线对应、任务取消及预览状态保存；降低法线与聚类的峰值内存。
- 修复 LAS 范围/分类信息与 E57 多扫描位姿、颜色读取；提供 Windows 单文件 EXE。
- 修复系统临时目录不可写时 EXE 无法启动的问题，自动选择可写目录并在退出后清理。
