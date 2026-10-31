# PointLabStudio — 点云综合处理平台

**v1.0.0** ｜ 桌面点云工作站（对标 CloudCompare 的个人专业工具），由 `vis_point_cloud.py` 演进而来。
PySide6 界面 + pygfx/wgpu GPU 渲染 + open3d 算法，`core/` 为不依赖 UI 的纯 Python 领域层。

产品方案见 [docs/产品方案.md](docs/产品方案.md)，版本变更见 [docs/CHANGELOG.md](docs/CHANGELOG.md)。

## 功能

- **Auto-Ingest 自动分级加载**：不论点云多大，同一窗口自动展示
  - S（<100 万点）同步加载；M/L 先显示预览，后台全量加载后无缝替换
  - `.bin` 维度沿用原脚本的启发式自动识别；>5000 万点保持采样预览并标注比例
  - **>1 亿点八叉树流式**：两遍分块扫描建稀疏八叉树索引，100M 点约 42 秒得到 800k 均匀采样，保留强度，不整体载入内存
  - 加载线程限流（最多 2 个并发），其余排队，可取消
- **Studio 风格界面**：顶栏图标化菜单 + 胶囊控件组、卡片式「场景」列表、3D 视口、右侧「数据概览」与颜色条/直方图面板、可收起日志抽屉；深/浅双主题、窗口状态记忆
- **GPU 渲染视口**（pygfx / wgpu）：脏标记按需渲染；按视距 LOD 渲染预算（150 万 / 60 万 / 15 万点三档）；颜色缓存，点大小只更新材质
- **数据保真 I/O**：原生 PLY / PCD(binary+ascii) / XYZ / PTS 读写，**保留强度、标签、法线等全部标量场**，导出不会把显示伪彩烘成 RGB；LAS 1.2 原生读（0/1/2/3/6/7/8）写
- **多格式读取**：bin / pcd / ply / xyz / xyzn / xyzrgb / pts / npy / npz / txt / csv / las / laz / e57
- **颜色体系**：auto/height/intensity/field/rgb/label/none + 7 种 colormap；任意一维标量场着色，颜色条显示直方图，可手动指定 vmin/vmax 或一键自动（2–98 百分位）
- **裁剪范围**：顶栏弹层输入 X/Y/Z 范围，视口实时线框反馈；非法范围即时提示并拒绝应用
- **处理命令**：体素 / 随机采样 / SOR / ROR / 盒裁切；参数校验统一由命令注册表驱动
- **分割与配准**：平面分割、地面提取、DBSCAN（eps 后台估算）、点到点 ICP、点到面 ICP、FPFH + RANSAC 全局配准、4×4 变换矩阵编辑器
- **测量**：连续点击累计折线（长度 + Newell 法面积），多边形区域半透明填充，可导出 CSV、一键清除
- **选择**：靶心选点 / 框选，橙色高亮，可提取或删除选中点
- **几何**：估计法线、C2C、C2M、Poisson 网格重建，可直接加入场景（参与渲染与 C2M 参照，可另行导出 PLY）
- **视口交互**：左键绕当前旋转中心旋转（水平拖拽绕世界 Z 轴、垂直做俯仰并限制 ±80°，Shift 精调）；右键/中键平移；滚轮阻尼平滑缩放；双击把旋转中心设为鼠标下的点
- **命令内核**：`Command` 数据类 + 参数规格注册表 + 序列化；撤销/重做、处理链、CLI、脚本控制台共用同一套命令
- **处理链**：处理 ▾ →「处理链…」串接多步，支持双击改参、导入/导出 JSON
- **Headless CLI**：`python -m apps.cli` 批处理，`--commands FILE` 复现命令序列，`--list-commands` 查看注册表
- **工程文件 `.pls` v2**：保存相对路径、相机、裁剪范围与派生点云（`.assets/*.npz`），兼容 v1
- **设置/日志**：主题、最近文件、窗口几何、上次目录持久化；滚动文件日志；崩溃标记与未捕获异常记录
- **插件**：把 `.py` 放进 `%APPDATA%\PointLabStudio\plugins`（或 `POINTLAB_PLUGIN_DIR`），通过 `register(api)` 注册新命令，UI 菜单与 CLI 自动可见

界面截图见 [docs/screenshots](docs/screenshots)：深色 `ui_dark.png` / 浅色 `ui_light.png` / 真实地图 `real_map.png` / 测量 `p4_measure.png` / 框选 `p4_select.png` / 处理链 `p5_pipeline.png`。

## 系统要求

| 项 | 要求 |
| --- | --- |
| 操作系统 | Windows 10 / 11 64 位（`start.bat` 为 Windows 脚本；其他平台可尝试 `python run.py` 直接启动，未做实测） |
| Python | **>= 3.11**（实测 3.12.10） |
| 显卡 | 支持 Vulkan 或 DirectX 12 的独立/集成显卡，驱动为较新版本（pygfx 基于 wgpu；实测 RTX 5060） |
| 磁盘 | 依赖约 1.3 GB（含 PySide6 / open3d）；测试数据另需约 80 MB |

## 安装

在仓库根目录（`README.md` 所在目录）打开 PowerShell：

```powershell
# 0) 获取代码
git clone https://github.com/jarviscccwl/PointLabStudio.git
cd PointLabStudio

# 1) 创建虚拟环境
python -m venv .venv

# 2) 安装依赖（推荐按锁定版本，已验证可用）
.venv\Scripts\python.exe -m pip install -U pip
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

- 想装允许范围内的最新版本，改用 `-r requirements.txt`（版本区间见 [pyproject.toml](pyproject.toml)）。
- 可选依赖：`.venv\Scripts\python.exe -m pip install laspy lazrs pye57`（读 LAZ / E57 时需要）。
- 依赖装在仓库内的 `.venv/`，不污染系统环境；该目录不入库，删掉重装即可。

## 运行

```powershell
# 双击 start.bat（无控制台窗口；依赖缺失或启动失败会保留窗口并给出原因）
.\start.bat

# 命令行等价写法
.venv\Scripts\python.exe run.py
.venv\Scripts\python.exe run.py "D:\data\points"          # 直接打开文件或目录
.venv\Scripts\python.exe run.py --background light "D:\data\points"
```

首次启动会自动创建运行时目录：

- `.tmp/pygfx/`：pygfx 字体/着色器缓存（避免写 `%LOCALAPPDATA%` 失败）
- `%APPDATA%\PointLabStudio\`：`settings.json` 与 `logs/pointlab.log`（可用 `POINTLAB_HOME` 改位置）

启动异常会弹系统消息框，完整 traceback 写入 `%APPDATA%\PointLabStudio\logs\pointlab.log`。

## 生成测试数据（可选）

仓库**不包含** `data/` 下的点云（约 80 MB，避免仓库臃肿），需要示例数据时本地生成：

```powershell
.venv\Scripts\python.exe tools\make_test_data.py --out data        # S + M 两级，约 80 MB
.venv\Scripts\python.exe tools\make_test_data.py --out data --big  # 追加 6000 万点，约 1 GB
```

生成后可直接打开 `data/scene_small.bin`。`tools/smoke_test.py`、`tools/audit_all.py` 依赖这两个文件。

## 测试与自检

```powershell
# 全量单元测试（统一入口会处理 pygfx 缓存目录与临时目录）
.venv\Scripts\python.exe tools\run_tests.py

# 在受限/只读沙箱（如 CI、文件沙箱）中运行
.venv\Scripts\python.exe tools\run_tests.py --sandbox

# 只跑某个文件 / 常用参数
.venv\Scripts\python.exe tools\run_tests.py tests\test_core.py -q
```

当前版本全量测试 **181 passed**（Windows 11 + Python 3.12 实测，含 GUI 用例）。

其他自检脚本（都需要先有 `data/`）：

```powershell
.venv\Scripts\python.exe tools\smoke_test.py     # 启动真实窗口，加载 S/M 数据并截图
.venv\Scripts\python.exe tools\audit_all.py      # 用真实鼠标/键盘事件逐项走查全部入口
.venv\Scripts\python.exe tools\bench_render.py   # GPU 适配器 + 千万点离屏渲染基准
```

> 不要用裸 `pytest` 在受限沙箱里跑：pytest 会用 `0o700` 建临时目录，某些 Windows 沙箱下会变成连创建者都列不出的目录，表现为大量 `PermissionError`。普通桌面环境裸 `pytest` 正常。

## 无界面批处理（CLI）

```powershell
# 查看统计
.venv\Scripts\python.exe -m apps.cli data\scene_small.bin --info

# 处理链 + 导出（步骤按顺序执行；--export 为文件，--outdir 为目录）
.venv\Scripts\python.exe -m apps.cli data\scene_small.bin --stage voxel:0.2 --stage sor:20,2.0 --export out.ply

# 命令序列（JSON）与注册表
.venv\Scripts\python.exe -m apps.cli data\scene_small.bin --commands steps.json --export out.las
.venv\Scripts\python.exe -m apps.cli --list-commands
```

支持步骤：`voxel:体素`、`random:点数`、`sor:k,std`、`ror:半径,最少邻居`、`crop:xmin,xmax,ymin,ymax,zmin,zmax`、`plane:距离`、`ground:距离`、`dbscan:半径,最少点数`。
其他参数：`--print-commands`（只打印命令 JSON）、`--outdir`、`--max-points`、`--bin-dim`、`--dtype`、`--npy-key`。

## 快捷键

| 键 | 功能 | 键 | 功能 |
| --- | --- | --- | --- |
| ←/↑ | 上一个点云 | →/↓ | 下一个点云 |
| R | 重置视角 | H | 帮助 |
| C | 循环颜色模式 | B | 开关裁剪范围 |
| Space | 显示/隐藏所选点云 | + / - | 点大小 |
| 测量 | 连续点击累计折线 | 选点 | 单击查看点信息 |
| 框选/套索 | 拖拽选择，可提取/删除 | Ctrl+E | 导出当前点云 |
| Esc | 退出测量/选择 | Ctrl+Z / Ctrl+Y | 撤销 / 重做 |
| W/S/A/D | 平移相机 | Q/E | 前进/后退 |
| 左键拖拽 | 旋转 | 右键拖拽 | 平移 |
| 滚轮 | 缩放 | 双击 | 设置旋转中心 |

## 目录结构

```
core/        领域核心（纯 Python，无 UI 依赖）：model / io / color / geometry / algorithms / commands / pipeline
ui/          PySide6 界面：viewport（pygfx）/ widgets / theme（Design Tokens）
apps/        应用入口（desktop.py / cli.py）
tests/       单元测试（pytest）
tools/       开发工具：统一测试入口 / 冒烟测试 / 渲染基准 / 测试数据生成 / 全功能审计
docs/        产品方案 + 变更记录 + 界面截图
resources/   SVG 图标资源
run.py       启动脚本（双击 start.bat 启动，无控制台；崩溃弹窗 + 日志）
start.bat    Windows 启动器（依赖自检、失败保留控制台）
vis_point_cloud.py  原始脚本（保留作为基线参考）
```

## 哪些文件不入库

`.venv/`、`data/`、`.tmp/`、`__pycache__/` 等**不在仓库里**，克隆后按上文命令重建即可：

| 路径 | 为什么不上传 | 如何重建 |
| --- | --- | --- |
| `.venv/` | 约 1.3 GB 的平台相关依赖，随 Python/系统变化 | `python -m venv .venv` + `pip install -r requirements-lock.txt` |
| `data/` | 80 MB 合成点云（`--big` 约 1 GB），可确定性再生成 | `python tools\make_test_data.py --out data` |
| `.tmp/`、`pygfx-*/` | 运行时缓存、临时文件、pygfx 字体缓存 | 启动或跑测试时自动创建 |
| `__pycache__/`、`*.pyc` | Python 字节码缓存 | 自动生成 |
| `.pytest_cache/`、`pytest-of-*/` | pytest 缓存与临时目录 | 自动生成 |
| `pip-*/`、`.pip-cache/` | pip 安装中途的临时目录 | 自动生成 |
| `*.pls` | 工程文件，含本机绝对路径与派生点云（`.assets/*.npz`），体积大且只对本人有意义 | 用界面「保存工程」生成 |
| `.idea/`、`.vscode/` | 个人 IDE 配置 | 各自生成 |
| `.git-old-history-*/` | 旧历史备份，仅本地保留 | 无需重建 |

完整规则见 [.gitignore](.gitignore)。仓库当前跟踪 116 个文件，`git ls-files` 可核对。

## 常见问题

**`start.bat` 提示「没有找到虚拟环境 .venv」**
按[安装](#安装)创建 `.venv` 并装依赖；`start.bat` 只认仓库根目录下的 `.venv`。

**启动后闪退 / 白屏**
看 `%APPDATA%\PointLabStudio\logs\pointlab.log`；多为显卡驱动过旧（wgpu 需要可用的 Vulkan 或 DX12）或依赖装错 Python 版本（需 3.11+，建议 3.12）。

**导入 pygfx 报字体缓存/权限错误**
用 `run.py` 或 `tools\run_tests.py` 启动，它们会把 `PYGFX_DATA_DIR` 指到 `.tmp/pygfx`；也可以手动设置该环境变量。

**测试出现大量 `PermissionError`**
这是受限沙箱对 `0o700` 临时目录的限制，不是代码问题：加 `--sandbox` 或换普通用户目录运行。

**打不开 LAZ / E57**
需自行安装可选依赖：`pip install laspy lazrs pye57`。

**没有示例数据**
运行 `tools\make_test_data.py --out data`（见上文）。

## 已知限制

① 裁剪范围使用 CPU 掩码重建；② >5000 万点以采样预览展示（已显式标注）；③ 平面主导场景的 ICP 绕竖直轴旋转退化（可先用 FPFH 全局配准）；④ DBSCAN 对连续表面会产生碎簇；⑤ 拾取为基于投影缓存的近似遮挡；⑥ LAZ/E57 需自行安装 `laspy`/`pye57`。详见 [docs/产品方案.md](docs/产品方案.md) §10–15。

## 版本与提交

- 当前版本 `1.0.0`（`core.__version__`、`pyproject.toml`、界面右下角一致），标签 `v1.0.0`。
- 发布分支 `main`，远程 `origin` → `https://github.com/jarviscccwl/PointLabStudio.git`。
- 提交前统一验证：`.venv\Scripts\python.exe tools\run_tests.py --sandbox`。
- 打标签与推送：`git tag -a v1.0.0 -m "PointLabStudio v1.0.0"`，然后 `git push origin main --tags`。

## 许可

本仓库目前未附带 `LICENSE` 文件。在未声明许可的情况下，默认保留所有权利（他人只能查看，不能直接复制分发）。
如需允许他人使用，建议补充一个许可证（例如 MIT）后再公开分享。

## 路线图

P0 技术验证 + P1 MVP 查看器 + P2 处理命令 + P3 分割配准 + P4 测量标注 +
P5 处理链/脚本/CLI + **P6 数据保真/性能/命令内核/选择/测量/配准/LOD** ✅（当前版本）→
后续：安装包与自动更新（按需求暂缓）、更多格式（E57 依赖可选安装）。
