"""处理链编辑器：按顺序串起多个处理步骤，应用到当前点云。

步骤通过「添加」菜单选择（体素/随机/SOR/ROR/盒裁切/平面/地面/DBSCAN），
参数复用 ParamDialog；支持双击改参数、上移/下移/删除，以及 JSON 导入导出
（与 CLI 的 --commands、历史记录里的命令完全同构）。
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QLabel, QListWidget, QMenu,
    QMessageBox, QPushButton, QToolButton, QVBoxLayout,
)

from core.model.entities import CloudEntity
from core.commands import (
    Command, commands_from_json, commands_to_json, get_spec, specs,
)
from ui.widgets.param_dialog import ParamDialog


class PipelineDialog(QDialog):
    def __init__(self, parent, entity: CloudEntity):
        super().__init__(parent)
        self.setWindowTitle("处理链")
        self.setMinimumSize(460, 420)
        self._entity = entity
        self._steps: list[dict] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 12)
        root.setSpacing(10)

        hint = QLabel(f"当前点云：{entity.name}（{entity.point_count:,} 点）\n"
                      "按顺序执行下列步骤，生成一个新的处理结果点云。")
        hint.setObjectName("dim")
        hint.setWordWrap(True)
        root.addWidget(hint)

        self.list = QListWidget()
        self.list.setObjectName("pipelineList")
        self.list.itemDoubleClicked.connect(lambda _item: self._edit_selected())
        root.addWidget(self.list, 1)

        buttons = QHBoxLayout()
        self.btn_add = QToolButton()
        self.btn_add.setText("添加步骤")
        self.btn_add.setObjectName("headerBtn")
        menu = QMenu(self.btn_add)
        for op, spec in specs().items():
            menu.addAction(spec.label, lambda checked=False, o=op: self._add_step(o))
        self.btn_add.setMenu(menu)
        self.btn_add.setPopupMode(QToolButton.InstantPopup)
        buttons.addWidget(self.btn_add)

        self.btn_remove = QPushButton("删除")
        self.btn_up = QPushButton("上移")
        self.btn_down = QPushButton("下移")
        self.btn_clear = QPushButton("清空")
        self.btn_import = QPushButton("导入…")
        self.btn_export = QPushButton("导出…")
        self.btn_remove.clicked.connect(self._remove)
        self.btn_up.clicked.connect(lambda: self._move(-1))
        self.btn_down.clicked.connect(lambda: self._move(+1))
        self.btn_clear.clicked.connect(self._clear)
        self.btn_import.clicked.connect(self._import_json)
        self.btn_export.clicked.connect(self._export_json)
        for button in (self.btn_remove, self.btn_up, self.btn_down, self.btn_clear,
                       self.btn_import, self.btn_export):
            buttons.addWidget(button)
        buttons.addStretch(1)
        root.addLayout(buttons)

        dialog_buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dialog_buttons.button(QDialogButtonBox.Ok).setText("运行")
        dialog_buttons.button(QDialogButtonBox.Cancel).setText("取消")
        dialog_buttons.accepted.connect(self.accept)
        dialog_buttons.rejected.connect(self.reject)
        root.addWidget(dialog_buttons)

    # ---------------- 数据 ----------------
    def steps(self) -> list:
        return list(self._steps)

    def _add_step(self, op: str):
        fields, hint = self._fields_for(op)
        dialog = ParamDialog(self, f"添加步骤：{get_spec(op).label}", fields, hint=hint)
        if dialog.exec() != QDialog.Accepted:
            return
        spec = get_spec(op)
        self._steps.append({"op": op, "params": spec.normalize(dialog.values())})
        self._refresh()
        self.list.setCurrentRow(len(self._steps) - 1)

    def _edit_selected(self):
        row = self._selected_row()
        if row < 0:
            return
        step = self._steps[row]
        spec = get_spec(step["op"])
        fields = spec.dialog_fields()
        for field, param in zip(fields, spec.params):
            field["default"] = step["params"].get(param.key, param.default)
        dialog = ParamDialog(self, f"编辑步骤：{spec.label}", fields, hint=spec.hint)
        if dialog.exec() != QDialog.Accepted:
            return
        step["params"] = spec.normalize(dialog.values())
        self._refresh()
        self.list.setCurrentRow(row)

    def _export_json(self):
        if not self._steps:
            QMessageBox.information(self, "处理链", "还没有步骤可导出。")
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出处理链", "pipeline.json",
                                              "JSON 文件 (*.json)")
        if not path:
            return
        commands = [Command.from_step(step) for step in self._steps]
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(commands_to_json(commands))
        except OSError as exc:
            QMessageBox.warning(self, "导出失败", str(exc))

    def _import_json(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入处理链", "", "JSON 文件 (*.json)")
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as fh:
                commands = commands_from_json(fh.read())
            steps = []
            for command in commands:
                spec = get_spec(command.op)
                steps.append({"op": command.op, "params": spec.normalize(command.params)})
        except (OSError, KeyError, ValueError) as exc:
            QMessageBox.warning(self, "导入失败", str(exc))
            return
        self._steps = steps
        self._refresh()

    def _fields_for(self, op: str):
        spec = get_spec(op)
        entity = self._entity
        extent = max(entity.extent(), 1e-6)
        mn, mx = entity.bounds()
        overrides = {}
        if op == "voxel":
            overrides["voxel"] = extent / 300.0
        elif op == "random":
            overrides["count"] = min(500_000, entity.point_count)
        elif op == "ror":
            overrides["radius"] = extent / 500.0
        elif op == "crop":
            overrides.update({"xmin": float(mn[0]), "xmax": float(mx[0]),
                              "ymin": float(mn[1]), "ymax": float(mx[1]),
                              "zmin": float(mn[2]), "zmax": float(mx[2])})
        elif op in ("plane", "ground"):
            overrides["dist"] = max(extent / 400.0, 0.02)
        elif op == "dbscan":
            from core.algorithms.segmentation import suggest_eps
            overrides["eps"] = round(suggest_eps(entity.xyz, 10), 3)
        fields = []
        for param in spec.params:
            field = param.to_dialog_field()
            if param.key in overrides:
                field["default"] = overrides[param.key]
            fields.append(field)
        return fields, spec.hint

    # ---------------- 列表操作 ----------------
    def _refresh(self):
        self.list.clear()
        for index, step in enumerate(self._steps):
            label = f"{index + 1}. {get_spec(step['op']).label}"
            params = step.get("params", {})
            if params:
                text = "，".join(f"{k}={v:g}" if isinstance(v, (int, float)) else f"{k}={v}"
                                 for k, v in params.items())
                label += f"   （{text}）"
            self.list.addItem(label)

    def _selected_row(self):
        items = self.list.selectedItems()
        return self.list.row(items[0]) if items else -1

    def _remove(self):
        row = self._selected_row()
        if row >= 0:
            del self._steps[row]
            self._refresh()
            self.list.setCurrentRow(min(row, len(self._steps) - 1))

    def _move(self, delta: int):
        row = self._selected_row()
        target = row + delta
        if row < 0 or not (0 <= target < len(self._steps)):
            return
        self._steps[row], self._steps[target] = self._steps[target], self._steps[row]
        self._refresh()
        self.list.setCurrentRow(target)

    def _clear(self):
        self._steps = []
        self._refresh()
