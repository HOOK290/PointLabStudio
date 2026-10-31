"""E26：插件加载与命令注册。"""

import numpy as np

from core.commands.builtin import run_command
from core.commands.command import Command
from core.commands.spec import _REGISTRY, get_spec
from core.model.entities import CloudEntity
from core.plugin import load_plugins

PLUGIN_OK = """
from core.commands.spec import CommandSpec, ParamDef
from core.model.entities import CloudEntity

__version__ = "1.2"

def register(api):
    def apply(entity, params, progress=None, cancel=None):
        out = entity.xyz.copy()
        out[:, 2] *= params["scale"]
        return CloudEntity(name="scaled", xyz=out, fields={}, path=None)

    api.command(CommandSpec("demo_scale", "插件缩放", [ParamDef("scale", "倍数", "float", 2.0)], apply=apply))
"""

PLUGIN_BROKEN = "def register(api):\n    raise RuntimeError('boom')\n"


def _write(folder, name, text):
    path = folder / name
    path.write_text(text, encoding="utf-8")
    return path


def test_plugin_registers_command_and_runs(tmp_path, monkeypatch):
    _write(tmp_path, "good.py", PLUGIN_OK)
    monkeypatch.setenv("POINTLAB_PLUGIN_DIR", str(tmp_path))
    loaded, errors = load_plugins(force=True)
    assert errors == []
    assert [i.name for i in loaded] == ["good"]
    assert loaded[0].version == "1.2"
    assert loaded[0].commands == ["demo_scale"]
    assert get_spec("demo_scale").label == "插件缩放"

    entity = CloudEntity(name="p", xyz=np.array([[0, 0, 1.0]], np.float32), fields={})
    out = run_command(entity, Command("demo_scale", {"scale": 3.0}))
    assert abs(float(out.xyz[0, 2]) - 3.0) < 1e-6
    _REGISTRY.pop("demo_scale", None)


def test_broken_plugin_is_reported_but_others_load(tmp_path, monkeypatch):
    _write(tmp_path, "bad.py", PLUGIN_BROKEN)
    _write(tmp_path, "good.py", PLUGIN_OK)
    monkeypatch.setenv("POINTLAB_PLUGIN_DIR", str(tmp_path))
    loaded, errors = load_plugins(force=True)
    assert [i.name for i in loaded] == ["good"]
    assert len(errors) == 1 and "bad" in errors[0] and "boom" in errors[0]
    _REGISTRY.pop("demo_scale", None)


def test_missing_register_is_error(tmp_path, monkeypatch):
    _write(tmp_path, "noreg.py", "VALUE = 1\n")
    monkeypatch.setenv("POINTLAB_PLUGIN_DIR", str(tmp_path))
    loaded, errors = load_plugins(force=True)
    assert loaded == []
    assert "缺少 register" in errors[0]
