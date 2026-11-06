"""Make Open3D's wheel self-contained instead of depending on Homebrew."""
from importlib.util import find_spec
from pathlib import Path
import os
import shutil
import subprocess

open3d = Path(find_spec("open3d").origin).parent
libusb = Path(find_spec("libusb_package").origin).parent / "libusb-1.0.dylib"
target = open3d / "libusb-1.0.0.dylib"
shutil.copy2(libusb, target)
for library in open3d.glob("libOpen3D*.dylib"):
    dependencies = subprocess.check_output(["otool", "-L", str(library)], text=True)
    original = "/opt/homebrew/opt/libusb/lib/libusb-1.0.0.dylib"
    if original not in dependencies:
        continue
    # Replace the file first so a shared package-cache hardlink is never edited.
    temporary = library.with_name(library.name + ".patching")
    shutil.copy2(library, temporary)
    os.replace(temporary, library)
    subprocess.run([
        "install_name_tool", "-change", original,
        "@loader_path/libusb-1.0.0.dylib", str(library),
    ], check=True)
    subprocess.run(["codesign", "--force", "--sign", "-", str(library)], check=True)
print("Open3D libusb dependency is bundled locally.")
