"""Standalone Apple Silicon bundle; build with packaging/build-macos.command."""
import ast
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, copy_metadata

root = Path(SPECPATH).parent
tree = ast.parse((root / "core" / "__init__.py").read_text(encoding="utf-8"))
version = next(
    ast.literal_eval(node.value)
    for node in tree.body if isinstance(node, ast.Assign)
    if any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets)
)
datas = [(str(root / "resources"), "resources")]
for package in ("pygfx.data_files", "pygfx.renderers.wgpu.wgsl", "wgpu", "dash", "plotly"):
    datas += collect_data_files(package)
for package in ("open3d", "numpy", "scipy", "pygfx", "wgpu", "rendercanvas", "laspy", "pye57", "dash", "plotly"):
    datas += copy_metadata(package)
binaries = []
for package in ("open3d", "wgpu", "pye57"):
    binaries += collect_dynamic_libs(package)
binaries = [
    (src, dst) for src, dst in binaries
    if "torch_ops" not in src and "tf_ops" not in src
]

a = Analysis(
    [str(root / "run.py")],
    pathex=[str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        "wgpu.backends.auto", "wgpu.backends.wgpu_native", "rendercanvas.qt",
        "open3d.pybind", "laspy", "lazrs", "laspy._compression.lazrsbackend",
        "pye57", "pye57.libe57",
    ],
    excludes=[
        "tkinter", "IPython", "jupyter", "notebook", "pytest", "_pytest", "pip",
        "ipykernel", "debugpy", "jupyter_client", "jupyter_core", "torch", "tensorflow",
        "mitsuba", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineQuick", "PySide6.QtQml", "PySide6.QtQuick",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name="PointLabStudio", debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False, target_arch="arm64",
)
collection = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="PointLabStudio")
app = BUNDLE(
    collection,
    name="PointLabStudio.app",
    icon=str(root / "build" / "macos-icon" / "PointLabStudio.icns"),
    bundle_identifier="com.pointlabstudio.desktop",
    version=version,
    info_plist={
        "CFBundleDisplayName": "PointLab Studio",
        "CFBundleShortVersionString": version,
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "26.0",
        "LSApplicationCategoryType": "public.app-category.graphics-design",
        "NSPrincipalClass": "NSApplication",
        "NSHumanReadableCopyright": "PointLabStudio contributors. macOS local build.",
    },
)
