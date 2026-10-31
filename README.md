# PointLabStudio — 点云综合处理平台

**v1.0.0** ｜ 桌面点云工作站，PySide6 + pygfx/wgpu + open3d，Windows 应用。

打开点云 → 查看/测量 → 处理/配准 → 导出，一个窗口完成。

## 功能

- **自动分级加载**：<100 万点直接载入；中大点云先预览、后台载入全量后替换；>1 亿点八叉树流式（1 亿点约 42 秒得到 80 万采样点，保留强度），可取消。
- **GPU 渲染**：按视距三档 LOD，脏标记按需重绘。
- **格式**：PLY / PCD / XYZ / XYZN / XYZRGB / PTS / LAS 读写；BIN / NPY / NPZ / TXT / CSV 读取；LAZ / E57 需装 `laspy`、`lazrs`、`pye57`。
- **字段保真**：强度、标签、法线等标量场全保留，导出不烘焙显示伪彩。
- **颜色**：默认 / 高度 / 强度 / 标量场 / RGB / 标签 / 单色，7 种色带，直方图，手动或自动值域。
- **处理命令**：体素降采样、随机采样、SOR、ROR、盒式裁切，可撤销/重做。
- **分割配准**：平面分割、地面提取、DBSCAN、点到点/点到面 ICP、FPFH+RANSAC、4×4 矩阵编辑。
- **几何**：法线估计、C2C、C2M、Poisson 网格重建。
- **测量选择**：折线长度与面积（导出 CSV）；点选/框选，可提取或删除选中点。
- **命令内核**：处理链、脚本控制台、CLI 共用同一套命令注册表。
- **工程文件** `.pls`：保存点云引用、相机、裁剪范围与派生数据。
- **插件**：`register(api)` 注册命令，界面与 CLI 自动出现。
- **界面**：深/浅主题、卡片式场景列表、颜色条与概览面板、可收起日志、窗口状态记忆。

## 环境要求

| 项 | 要求 |
| --- | --- |
| 操作系统 | Windows 10 / 11 64 位 |
| Python | 3.11+（实测 3.12.10） |
| 显卡 | 支持 Vulkan 或 DirectX 12，驱动较新 |
| 磁盘 | 依赖约 1.3 GB |

## 安装

```powershell
git clone https://github.com/jarviscccwl/PointLabStudio.git
cd PointLabStudio
python -m venv .venv
.venv\Scripts\python.exe -m pip install -U pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

LAZ / E57 可选依赖：`.venv\Scripts\python.exe -m pip install laspy lazrs pye57`。

## 启动

```powershell
.\start.bat                                          # 双击亦可
.venv\Scripts\python.exe run.py                      # 命令行等价
.venv\Scripts\python.exe run.py "D:\data\points"     # 直接打开文件/目录
```

运行时目录：`.tmp/pygfx/`（着色器缓存）、`%APPDATA%\PointLabStudio\`（设置与日志）。

## 基本操作

| 操作 | 方式 | 操作 | 方式 |
| --- | --- | --- | --- |
| 旋转 | 左键拖拽（Shift 精调） | 平移 | 右键/中键拖拽 |
| 缩放 | 滚轮 | 旋转中心 | 双击点云位置 |
| 切换点云 | ← ↑ / → ↓ | 显示/隐藏 | Space |
| 重置视角 | R | 颜色模式 | C |
| 点大小 | + / - | 裁剪范围 | B |
| 导出 | Ctrl+E | 撤销/重做 | Ctrl+Z / Ctrl+Y |
| 退出工具 | Esc | 帮助 | H |

打开：拖入窗口或 文件菜单。保存：`文件 → 保存工程`（`.pls`）。

## 支持格式

| 格式 | 读 | 写 | 说明 |
| --- | --- | --- | --- |
| PLY | ✅ | ✅ | 保留全部标量字段 |
| PCD | ✅ | ✅ | binary / ascii |
| XYZ / XYZN / XYZRGB | ✅ | ✅ | 字段名自动识别 |
| PTS | ✅ | ✅ | 支持强度 |
| LAS | ✅ | ✅ | 1.2，点格式 0/1/2/3/6/7/8 |
| LAZ / E57 | ✅ | — | 需可选依赖 |
| NPY / NPZ / TXT / CSV | ✅ | — | 数值矩阵 |
| BIN | ✅ | — | 维度自动识别 |

## 命令行

```powershell
.venv\Scripts\python.exe -m apps.cli data\scene.bin --info
.venv\Scripts\python.exe -m apps.cli data\scene.bin --stage voxel:0.2 --stage sor:20,2.0 --export out.ply
.venv\Scripts\python.exe -m apps.cli data\scene.bin --commands steps.json --export out.las
.venv\Scripts\python.exe -m apps.cli --list-commands
```

步骤：`voxel:体素`、`random:点数`、`sor:k,std`、`ror:半径,邻居数`、`crop:x0,x1,y0,y1,z0,z1`、`plane:距离`、`ground:距离`、`dbscan:半径,点数`。
其他参数：`--outdir`、`--max-points`、`--bin-dim`、`--dtype`、`--npy-key`。

## 常见问题

| 现象 | 处理 |
| --- | --- |
| `start.bat` 提示找不到 `.venv` | 按「安装」建 `.venv`，须在仓库根目录 |
| 启动闪退/白屏 | 看 `%APPDATA%\PointLabStudio\logs\pointlab.log`；多为驱动过旧或 Python <3.11 |
| pygfx 字体缓存报错 | 用 `run.py` 启动，会设 `PYGFX_DATA_DIR` |
| 打不开 LAZ / E57 | 装 `laspy lazrs pye57` |
| 缺少示例数据 | `tools\make_test_data.py --out data`，打开 `data/scene_small.bin` |
| 大文件只显示采样点 | >5000 万点为采样预览，界面标注比例 |
