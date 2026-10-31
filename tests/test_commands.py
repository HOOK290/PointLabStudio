"""D14：命令数据模型、参数校验与历史记录。"""

from __future__ import annotations

import json

import numpy as np
import pytest

from core.commands import Command, History, commands_from_json, commands_to_json, get_spec
from core.commands.spec import ParamDef, CommandSpec, register
from core.model.entities import CloudEntity, ScalarField
from core.pipeline import apply_step, parse_stage


def _cloud(n=2000, seed=0):
    rng = np.random.default_rng(seed)
    xyz = rng.uniform(-5, 5, (n, 3)).astype(np.float32)
    return CloudEntity(name="c", xyz=xyz,
                       fields={"intensity": ScalarField("intensity", rng.uniform(size=n).astype(np.float32))})


def test_command_roundtrip_and_validation():
    cmd = Command("voxel", {"voxel": 0.5})
    assert cmd.to_dict() == {"op": "voxel", "params": {"voxel": 0.5}}
    assert Command.from_json(cmd.to_json()) == cmd
    assert Command.from_step({"op": "sor"}) == Command("sor", {})
    with pytest.raises(ValueError):
        Command.from_dict({"params": {}})
    with pytest.raises(ValueError):
        Command.from_dict({"op": "voxel", "params": []})
    with pytest.raises(ValueError):
        Command.from_json("{not json}")


def test_command_list_json():
    items = [Command("voxel", {"voxel": 0.5}), Command("sor", {"k": 20})]
    text = commands_to_json(items)
    assert json.loads(text)[0]["op"] == "voxel"
    assert commands_from_json(text) == items


def test_spec_normalize_fills_defaults_and_validates():
    spec = get_spec("sor")
    assert spec.normalize({}) == {"k": 20, "std": 2.0}
    assert spec.normalize({"k": "12", "std": "1.5"}) == {"k": 12, "std": 1.5}
    with pytest.raises(ValueError):
        spec.normalize({"k": 1})
    with pytest.raises(ValueError):
        spec.normalize({"nope": 1})


def test_custom_command_registration_and_run():
    reg = register(CommandSpec("scale_test", "缩放测试",
                               (ParamDef("factor", "倍数", default=2.0, minimum=0.1, maximum=10.0),),
                               lambda e, p, progress, cancel: e))
    assert get_spec("scale_test") is reg
    with pytest.raises(ValueError):
        get_spec("scale_test").normalize({"factor": 100})


def test_apply_step_matches_run_command():
    cloud = _cloud()
    a = apply_step(cloud, {"op": "voxel", "params": {"voxel": 1.0}})
    b = apply_step(cloud, Command("voxel", {"voxel": 1.0}))
    assert a.point_count == b.point_count
    with pytest.raises(KeyError):
        apply_step(cloud, {"op": "不存在"})


def test_history_records_commands_and_undo():
    history = History()
    applied = []
    cmd = Command("voxel", {"voxel": 0.5})
    history.push("添加 a", lambda: applied.append("undo"), lambda: applied.append("redo"), cmd)
    history.push("显示 a", lambda: None, lambda: None)
    assert history.commands() == [cmd]
    assert json.loads(history.commands_json())[0]["params"] == {"voxel": 0.5}
    assert [e["label"] for e in history.entries()] == ["添加 a", "显示 a"]
    assert history.undo() == "显示 a"
    assert history.undo() == "添加 a"
    assert applied == ["undo"]
    assert history.redo() == "添加 a"
    assert history.redo() == "显示 a"
    assert applied == ["undo", "redo"]


def test_parse_stage_uses_spec_types():
    assert parse_stage("voxel:0.5") == {"op": "voxel", "params": {"voxel": 0.5}}
    assert parse_stage("sor:20,2.0")["params"] == {"k": 20, "std": 2.0}
    with pytest.raises(ValueError):
        parse_stage("bogus:1")
    with pytest.raises(ValueError):
        parse_stage("voxel:0.5,extra")
