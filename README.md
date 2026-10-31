# PointLabStudio — 点云综合处理平台

基于 `vis_point_cloud.py` 演进的桌面点云工作站（对标 CloudCompare 的个人专业工具）。
产品方案见 [docs/产品方案.md](docs/产品方案.md)。

## 功能（v0.8 · CloudCompare 风格交互 / 网格实体 / 数据保真）

- **Auto-Ingest 自动分级加载**：无论点云大小，同一窗口自动展示
  - S（<100 万点）同步加载；M/L 先显示预览，后台全量加载无缝替换
  - `.bin` 维度沿用原脚本的启发式自动识别；>5000 万点保持采样预览并明确标注比例
  - **>1 亿点八叉树流式**：两遍分块扫描建稀疏八叉树索引，100M 点约 42 秒得到 800k 均匀采样，保留强度，不整体载入内存
  - 加载线程限流（最多 2 个并发），其余排队，可取消
- **Studio 风格界面**：顶栏（图标化菜单 + 胶囊控件组）、卡片式「场景」列表、
  3D 视口、右侧「数据概览」+ **颜色条/直方图**面板、可收起日志抽屉；深/浅双主题、窗口状态记忆
- **GPU 渲染视口**：pygfx (wgpu)，脏标记按需渲染；按视距 LOD 渲染预算
  （150 万 / 60 万 / 15 万点三档）；颜色缓存，点大小只更新材质
- **数据保真 I/O**：原生 PLY / PCD(binary+ascii) / XYZ / PTS 读写，**保留强度、标签、法线等全部标量场**，
  导出不再把显示伪彩烘成 RGB；LAS 1.2 原生读（0/1/2/3/6/7/8）写；LAZ/E57 可选依赖提示
- **多格式读取**：bin / pcd / ply / xyz / xyzn / xyzrgb / pts / npy / npz / txt / csv / las / laz / e57
- **颜色体系**：auto/height/intensity/field/rgb/label/none + 7 种 colormap；
  **任意一维标量场着色**，颜色条显示直方图，可手动指定 vmin/vmax 或一键自动（2–98 百分位）
- **裁剪范围**：顶栏弹层输入 X/Y/Z 范围，视口实时线框反馈；非法范围即时提示并拒绝应用
- **处理命令**：体素 / 随机采样 / SOR / ROR / 盒裁切；参数校验统一由命令注册表驱动
- **分割与配准**：平面分割、地面提取、DBSCAN（eps 后台估算）、
  点到点 ICP、**点到面 ICP**、**FPFH + RANSAC 全局配准**、4×4 变换矩阵编辑器
- **测量**：连续点击累计折线（长度 + Newell 法面积），**多边形区域半透明填充**直观标出被测面积，
  可**导出 CSV**、一键清除
- **选择**：**框选** 选择点云（靶心选点 / 框选两个图标），橙色高亮，可提取或删除选中点
- **几何**：估计法线、C2C（点云到点云）、C2M（点到三角网格）、Poisson 网格重建
  **直接加入场景**（参与渲染与 C2M 参照，可另行导出 PLY）
- **视口交互（v0.8）**：左键旋转（绕当前旋转中心，CloudCompare 风格）——
  水平拖拽严格绕世界 Z 轴转动、垂直拖拽做俯仰（限制 ±80°，不会翻到背面）、按住 Shift 精调；
  右键/中键平移、**滚轮阻尼平滑缩放**、**双击把旋转中心设为鼠标下的点**
- **命令内核**：`Command` 数据类 + 参数规格注册表 + 序列化；
  撤销/重做、处理链、CLI、脚本控制台共用同一套命令
- **处理链**：处理 ▾ →「处理链…」串接多步，支持双击改参、导入/导出 JSON
- **Headless CLI**：`python -m apps.cli` 批处理；`--commands FILE` 复现命令序列、`--list-commands` 查看注册表
- **工程文件** `.pls` v2：保存**相对路径**、相机、裁剪范围与**派生点云**（`.assets/*.npz`），兼容 v1
- **设置/日志**：主题、最近文件、窗口几何、上次目录持久化；滚动文件日志；崩溃标记与未捕获异常记录
- **插件**：把 `.py` 放进 `%APPDATA%\PointLabStudio\plugins`（或 `POINTLAB_PLUGIN_DIR`），
  通过 `register(api)` 注册新命令，UI 菜单与 CLI 自动可见

界面截图见 [docs/screenshots](docs/screenshots)（深色 `ui_dark.png` / 浅色 `ui_light.png` /
真实地图 `real_map.png` / 测量 `p4_measure.png` / 框选 `p4_select.png` / 处理链 `p5_pipeline.png`）。

## 快速开始

```powershell
# 首次：创建虚拟环境并安装依赖（已创建则跳过）
python -m venv --system-site-packages --without-pip .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt

# 运行：直接双击 start.bat（无控制台窗口）
# 启动失败会弹出系统消息框，并把 traceback 写入日志
# 命令行等价写法：
.venv\Scripts\python.exe run.py
.venv\Scripts\python.exe run.py "D:\data\points"   # 直接打开文件或目录
```

## 无界面批处理（CLI）

```powershell
# 查看统计
.venv\Scripts\python.exe -m apps.cli data\cloud.pcd --info

# 处理链 + 导出（步骤按顺序执行；--export 为文件，--outdir 为目录）
.venv\Scripts\python.exe -m apps.cli data\cloud.pcd --stage voxel:0.2 --stage sor:20,2.0 --export out.ply

# 命令序列（JSON）与注册表
.venv\Scripts\python.exe -m apps.cli data\cloud.pcd --commands steps.json --export out.las
.venv\Scripts\python.exe -m apps.cli --list-commands
```

支持步骤：`voxel:体素`、`random:点数`、`sor:k,std`、`ror:半径,最少邻居`、
`crop:xmin,xmax,ymin,ymax,zmin,zmax`、`plane:距离`、`ground:距离`、`dbscan:半径,最少点数`。

## 已验证

- RTX 5060：1000 万点离屏渲染 407 FPS；主窗口 520 万点约 30 FPS，改为脏标记渲染后空场景不再持续提交帧
- 真实建图数据 6.6M 点地图：加载 ~4s，高度着色结构清晰
- 体素降采样 6.6M → 940k 点 2.69s；地面提取 200k 点 0.11s；ICP 已知变换恢复误差 0.0000
- 点到面 ICP 在起伏曲面 60 次迭代收敛到 1e-7；FPFH+RANSAC 可恢复已知平移
- LAS 往返：位置误差 < 1mm（0.001 量化）、intensity/classification/RGB 精确往返
- CLI：200k → 体素 2.0m → 13,029 点导出 PLY，`intensity` 字段保留（头部含 `property float intensity`）
- v0.8：真实鼠标事件验证转盘相机（左键绕 pivot 旋转、右键平移、滚轮缩放、双击设旋转中心）；
  测量面积多边形填充、框选松手正确触发
- 全功能审计 **48/48 通过**（`tools/audit_all.py`，真实鼠标/键盘事件）
- 自动化测试 **149 passed / 1 skipped**（`python tools/run_tests.py`；沙箱内加 `--sandbox`）
- 当前功能与验证范围见 [功能检查报告](docs/功能检查报告.md)

已知限制：① 裁剪范围使用 CPU 掩码重建；② >5000 万点以采样预览展示（已显式标注）；
③ 平面主导场景的 ICP 绕竖直轴旋转退化（可先用 FPFH 全局配准）；
④ DBSCAN 对连续表面会产生碎簇；⑤ 拾取为基于投影缓存的近似遮挡；
⑥ LAZ/E57 需自行安装 `laspy`/`pye57`。详见 docs/产品方案.md §10–15。

## 操作

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
| 滚轮 | 缩放 | | |

## 目录结构

```
.venv/       运行环境（已装好全部依赖，勿删除；没它无法运行）
core/        领域核心（纯 Python，无 UI 依赖）：model / io / color / geometry / algorithms / commands / pipeline
ui/          PySide6 界面：viewport（pygfx）/ widgets / theme（Design Tokens）
apps/        应用入口（desktop.py / cli.py）
tools/       开发工具：统一测试入口 / 冒烟测试 / 渲染基准 / 测试数据生成 / 审计
tests/       单元测试（pytest）
docs/        产品方案 + 界面截图 + 变更记录
run.py       启动脚本（双击 start.bat 启动，无控制台；崩溃弹窗+日志）
vis_point_cloud.py  原始脚本（保留作为基线参考）
```

> 若需重建环境：按「快速开始」命令即可（依赖会装进 `.venv`）。
> 测试数据已移除，需要时运行 `tools/make_test_data.py` 重新生成。

## 路线图

P0 技术验证 + P1 MVP 查看器 + P2 处理命令 + P3 分割配准 + P4 测量标注 +
P5 处理链/脚本/CLI + **P6 数据保真/性能/命令内核/选择/测量/配准/LOD** ✅（本版本）→
后续：安装包与自动更新（按需求暂缓）、更多格式（E57 依赖可选安装）。

## 分支与提交

- 当前发布分支：`main`（v0.8 的相机/选择/测量/网格实体改动已合入）。
- 本仓库为本地仓库，未配置远程（`git remote` 为空），因此无法执行 `git push`；
  需要推送时先 `git remote add origin <你的仓库地址>`，再 `git push -u origin main`。
- 提交前统一验证：`.venv\Scripts\python.exe toolsun_tests.py --sandbox`
