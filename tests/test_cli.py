"""D16：CLI 命令解析与 --commands JSON 执行。"""

from __future__ import annotations

import json

import numpy as np

from apps import cli
from core.io.readers import ReadOptions, read_cloud


def _write_xyz(path, n=500):
    rng = np.random.default_rng(0)
    xyz = rng.uniform(-2, 2, (n, 3)).astype(np.float32)
    np.savetxt(path, xyz, fmt="%.5f")


def test_list_commands(capsys):
    assert cli.main(["--list-commands"]) == 0
    out = capsys.readouterr().out
    assert "voxel" in out and "dbscan" in out


def test_stage_and_print_commands(tmp_path, capsys):
    src = tmp_path / "a.xyz"
    _write_xyz(src)
    assert cli.main([str(src), "--stage", "voxel:0.5", "--print-commands"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data[0] == {"op": "voxel", "params": {"voxel": 0.5}}


def test_commands_json_file_executes(tmp_path):
    src = tmp_path / "b.xyz"
    out = tmp_path / "b.ply"
    _write_xyz(src)
    cmd_file = tmp_path / "cmds.json"
    cmd_file.write_text(json.dumps([
        {"op": "voxel", "params": {"voxel": 0.8}},
        {"op": "crop", "params": {"xmin": -1, "xmax": 1, "ymin": -1, "ymax": 1,
                                  "zmin": -1, "zmax": 1}},
    ]), encoding="utf-8")
    code = cli.main([str(src), "--commands", str(cmd_file), "--export", str(out)])
    assert code == 0 and out.exists()
    result = read_cloud(str(out), ReadOptions())
    assert 0 < result.point_count < 500


def test_commands_reject_bad_params(tmp_path, capsys):
    src = tmp_path / "c.xyz"
    _write_xyz(src)
    cmd_file = tmp_path / "bad.json"
    cmd_file.write_text(json.dumps([{"op": "sor", "params": {"k": 1}}]), encoding="utf-8")
    assert cli.main([str(src), "--commands", str(cmd_file), "--info"]) == 1
    assert "参数错误" in capsys.readouterr().err


def test_stage_and_commands_are_exclusive(tmp_path, capsys):
    src = tmp_path / "d.xyz"
    _write_xyz(src)
    cmd_file = tmp_path / "x.json"
    cmd_file.write_text("[]", encoding="utf-8")
    assert cli.main([str(src), "--stage", "voxel:1", "--commands", str(cmd_file)]) == 1
