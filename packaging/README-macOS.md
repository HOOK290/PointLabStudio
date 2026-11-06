# PointLabStudio for macOS (Apple Silicon)

This local port packages the original PointLabStudio 1.1.0 UI and processing code as a standalone `.app`. It uses the native arm64 Python/Qt/Open3D libraries and wgpu's Metal backend. macOS 26 or newer is required by the selected PySide6 6.12 wheels. The build was verified on macOS 27.2 / Apple M5.

## Build

With Python 3.12 and uv available:

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r packaging/requirements-macos.txt
.venv/bin/python packaging/prepare_macos.py
.venv/bin/python -m unittest discover -s tests -v
./packaging/build-macos.command
```

The output is `dist/PointLabStudio.app`. Copy the entire app to `~/Applications`; it contains Python and its dependencies and does not need the source checkout or a shell environment at runtime. Do not copy only `Contents/MacOS/PointLabStudio`.

The Open3D 0.20 macOS wheel references a Homebrew libusb path. `prepare_macos.py` copies the native library from `libusb-package`, rewrites that reference to a relative path, and re-signs the changed library. It does not install Homebrew or modify system libraries.

Settings, logs and GPU cache are saved in `~/Library/Application Support/PointLabStudio/`. `POINTLAB_HOME` overrides this directory when explicitly set. Runtime failures are logged in `logs/pointlab.log` there.

Qt maps its portable `Ctrl` shortcuts to Command on macOS: use Command+O to open, Command+S to save a project, Command+E to export and Command+Z to undo. Existing help text retains the upstream portable shortcut names.

The macOS build reverses vertical left-button orbit relative to upstream's Windows controls. Horizontal orbit and right/middle-button pan retain their original behavior. Left-button orbit uses mouse-position deltas and is independent of the system Natural Scrolling preference. Wheel input compensates for Qt's `inverted()` flag: rolling the wheel forwards (away from the user) zooms in, and rolling backwards zooms out, regardless of Natural Scrolling. This normalization covers both angle/pixel deltas and fixed-height wheel navigation.

The app is ad-hoc signed for local use, not Developer ID signed or notarized for distribution. Intel Macs require a separate native x86_64 build. Upstream files, source and build scripts are retained so the application can be rebuilt or updated.
