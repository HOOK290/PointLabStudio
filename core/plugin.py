"""E26：轻量插件机制。

插件是一个普通 .py 文件，放在以下任一目录：
  * 环境变量 POINTLAB_PLUGIN_DIR 指向的目录
  * <app_home>/plugins

插件通过模块级 ``register(api)`` 注册命令：

    from core.commands.spec import ParamDef

    def register(api):
        api.command(CommandSpec("demo", "示例", [ParamDef("k", "倍数", "float", 2.0)],
                                apply=lambda entity, p, progress=None, cancel=None: entity))

`api.command` 会拒绝重复 op，避免覆盖内置命令。
"""

from __future__ import annotations

import importlib.util
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from core.commands.spec import CommandSpec, get_spec, register
from core.settings import app_home


@dataclass
class PluginInfo:
    name: str
    version: str
    path: str
    commands: list[str] = field(default_factory=list)


class PluginApi:
    def __init__(self, info: PluginInfo) -> None:
        self.info = info

    def command(self, spec: CommandSpec) -> None:
        try:
            get_spec(spec.op)
        except KeyError:
            register(spec)
            self.info.commands.append(spec.op)
            return
        raise ValueError(f"命令 {spec.op!r} 已存在，插件不能覆盖")

    def log(self, message: str) -> None:
        from core.applog import get_logger
        get_logger("plugin").info("[%s] %s", self.info.name, message)


def plugin_dirs() -> list[Path]:
    dirs: list[Path] = []
    env = os.environ.get("POINTLAB_PLUGIN_DIR", "").strip()
    if env:
        dirs.extend(Path(p) for p in env.split(os.pathsep) if p.strip())
    dirs.append(app_home() / "plugins")
    seen, result = set(), []
    for d in dirs:
        key = str(d).lower()
        if key not in seen:
            seen.add(key)
            result.append(d)
    return result


def discover_plugins() -> list[Path]:
    found: list[Path] = []
    for folder in plugin_dirs():
        if not folder.is_dir():
            continue
        found.extend(sorted(p for p in folder.glob("*.py") if not p.name.startswith("_")))
    return found


_CACHE: tuple[list[PluginInfo], list[str]] | None = None


def load_plugins(force: bool = False) -> tuple[list[PluginInfo], list[str]]:
    """导入所有插件；单个插件失败只记录错误，不影响其它插件。

    结果缓存，避免同一进程里重复注册命令（重复调用只返回缓存）。
    """
    global _CACHE
    if _CACHE is not None and not force:
        return _CACHE
    loaded: list[PluginInfo] = []
    errors: list[str] = []
    for path in discover_plugins():
        name = path.stem
        info = PluginInfo(name=name, version="?", path=str(path))
        try:
            mod_name = f"pointlab_plugin_{name}"
            spec = importlib.util.spec_from_file_location(mod_name, path)
            if spec is None or spec.loader is None:
                raise ImportError("无法加载模块")
            module = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = module
            spec.loader.exec_module(module)
            info.version = str(getattr(module, "__version__", "?"))
            register_fn = getattr(module, "register", None)
            if not callable(register_fn):
                raise ValueError("缺少 register(api) 函数")
            register_fn(PluginApi(info))
            loaded.append(info)
        except Exception as exc:  # noqa: BLE001 - 插件错误必须兜住
            errors.append(f"{name}: {exc}")
    _CACHE = (loaded, errors)
    return _CACHE
