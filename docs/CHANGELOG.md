# 变更记录

## v1.0.0（2026-10-31）

首个正式版。

- 版本号统一 `1.0.0`（`core.__version__`、`pyproject.toml`、界面）。
- 文档精简为产品说明与使用指南。
- 修复全新克隆测试失败：`tools/run_tests.py` 现确保 `.tmp/pygfx` 存在。
- `start.bat` 缺环境提示改用 `requirements.txt`。
- 依赖清单合并为单一 `requirements.txt`（精确版本），删除 `requirements-lock.txt`。

## v0.8.1（2026-10-31）

- 相机：水平拖拽绕 Z 轴、俯仰限 ±80°、Shift 精调。
- 滚轮阻尼缩放，到位后刷新 LOD。
- 新增 3 项相机回归测试。

## v0.8（2026-10）

- 八叉树流式加载，1 亿点约 42 秒得到 80 万采样点。
- 网格实体化，Poisson 重建可加入场景。
- LAZ / E57 实机验证。
- 相机重写（转盘 + pivot），工程保存 pivot。
- 测量面积半透明填充。
- `start.bat` 依赖自检；`run.py` 准备缓存目录与启动失败弹窗。
- 版本号 `0.8.0`。

## v0.7（2026-10）

- `pyproject.toml`、`requirements.txt`、统一测试入口 `tools/run_tests.py`。
- 原生读写 PLY / PCD / XYZ / PTS，保留标量字段。
- 工程 v2（相对路径、相机、裁剪范围、派生点云）。
- 命令内核：撤销/重做、处理链、CLI、脚本控制台。
- 框选、测量与 CSV 导出、标量场着色、点到面 ICP、FPFH+RANSAC、4×4 矩阵编辑、LAS 读写、LOD、法线/C2C/C2M/Poisson、插件、崩溃恢复。
- 性能：脏标记渲染、颜色缓存、加载队列、可取消任务。

## v0.6（2026-10）

- P0–P5 里程碑：技术验证、查看器、处理命令、分割配准、测量标注、处理链与脚本。

## v0.5 及更早

- `vis_point_cloud.py` 单文件基线。
