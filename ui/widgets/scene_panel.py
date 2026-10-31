"""左侧「场景」面板：卡片式点云列表（原创 Studio 风格，非 CloudCompare DB Tree）。

每张卡片：勾选框（显示/隐藏）+ 名称 + 点数/预览状态。
点击卡片选中；双击聚焦；右键菜单。
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMenu, QPushButton,
    QToolButton, QVBoxLayout, QWidget,
)

from core.model.entities import CloudEntity

CARD_HEIGHT = 66


class SceneCard(QWidget):
    clicked = Signal()
    double_clicked = Signal()
    context_menu = Signal(object)  # global pos
    visibility_toggle = Signal()

    def __init__(self, entity: CloudEntity, parent=None):
        super().__init__(parent)
        self.entity = entity
        self.setObjectName("sceneCard")
        self.setAttribute(Qt.WA_Hover, True)
        self.setCursor(Qt.PointingHandCursor)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(10, 9, 12, 9)
        outer.setSpacing(9)

        self.dot = QCheckBox()  # 勾选 = 显示；保留属性名兼容外部接口
        self.dot.setObjectName("sceneCheck")
        self.dot.setChecked(entity.visible)
        self.dot.setCursor(Qt.PointingHandCursor)
        self.dot.setToolTip("勾选显示 / 取消隐藏（Space）")
        self.dot.toggled.connect(self._on_dot)
        outer.addWidget(self.dot, 0, Qt.AlignVCenter)

        col = QVBoxLayout()
        col.setSpacing(2)

        top = QHBoxLayout()
        top.setSpacing(6)
        self.name = QLabel(entity.name)
        self.name.setObjectName("cardTitle")
        self.name.setToolTip(entity.path or entity.name)
        top.addWidget(self.name, 1)
        col.addLayout(top)

        self.sub = QLabel()
        self.sub.setObjectName("cardSub")
        col.addWidget(self.sub)
        outer.addLayout(col, 1)

        self.refresh()

    # ---------------- 数据 ----------------
    def refresh(self):
        e = self.entity
        self.name.setText(e.name)
        points = f"{e.point_count:,} 点"
        if e.is_preview:
            points += f" · 预览 {int(e.loaded * 100)}%"
        self.sub.setText(points)
        self.dot.blockSignals(True)
        self.dot.setChecked(e.visible)
        self.dot.blockSignals(False)

    def set_selected(self, selected: bool):
        if self.property("selected") != selected:
            self.setProperty("selected", selected)
            self.style().unpolish(self)
            self.style().polish(self)
            self.update()

    # ---------------- 内部 ----------------
    def _on_dot(self, checked: bool):
        self.entity.visible = bool(checked)
        self.visibility_toggle.emit()

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(ev)

    def mouseDoubleClickEvent(self, ev):
        self.double_clicked.emit()
        super().mouseDoubleClickEvent(ev)

    def contextMenuEvent(self, ev):
        self.context_menu.emit(ev.globalPos())


class ScenePanel(QWidget):
    entity_selected = Signal(object)
    visibility_changed = Signal(object)
    focus_requested = Signal(object)
    remove_requested = Signal(object)
    reload_requested = Signal(object)
    open_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("scenePanel")
        self._rows: list[tuple[QListWidgetItem, SceneCard]] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        head = QHBoxLayout()
        title = QLabel("场景")
        title.setObjectName("sectionTitle")
        self.lbl_count = QLabel("0")
        self.lbl_count.setObjectName("dim")
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(self.lbl_count)
        root.addLayout(head)

        self.list = QListWidget()
        self.list.setObjectName("sceneList")
        self.list.setSpacing(4)
        self.list.setFrameShape(QListWidget.NoFrame)
        self.list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.list.itemSelectionChanged.connect(self._on_selection)
        root.addWidget(self.list, 1)

        # 空状态
        self.empty = QWidget()
        ev = QVBoxLayout(self.empty)
        ev.setContentsMargins(0, 0, 0, 0)
        ev.setSpacing(8)
        hint = QLabel("还没有点云")
        hint.setObjectName("sectionTitle")
        hint.setAlignment(Qt.AlignCenter)
        sub = QLabel("拖入文件或文件夹，或点击下方按钮")
        sub.setObjectName("dim")
        sub.setAlignment(Qt.AlignCenter)
        btn = QPushButton("打开点云…")
        btn.setObjectName("primary")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self.open_requested.emit)
        ev.addWidget(hint)
        ev.addWidget(sub)
        ev.addWidget(btn)
        root.addWidget(self.empty, 1)

    # ---------------- 数据 ----------------
    def set_entities(self, entities: list):
        self.list.clear()
        self._rows = []
        for e in entities:
            self.add_entity(e)

    def add_entity(self, entity: CloudEntity):
        item = QListWidgetItem()
        item.setData(Qt.UserRole, entity)
        item.setSizeHint(QSize(0, CARD_HEIGHT))
        self.list.addItem(item)
        card = SceneCard(entity)
        card.clicked.connect(lambda c=card: self._select_card(c))
        card.double_clicked.connect(lambda c=card: self.focus_requested.emit(c.entity))
        card.context_menu.connect(lambda pos, c=card: self._context_menu(c, pos))
        card.visibility_toggle.connect(lambda c=card: self._on_visibility(c))
        self.list.setItemWidget(item, card)
        self._rows.append((item, card))
        self._refresh_chrome()

    def update_entity(self, entity: CloudEntity):
        row = self._row_of(entity)
        if row is None:
            return
        item, card = self._rows[row]
        card.entity = entity  # 全量加载后对象被替换
        item.setData(Qt.UserRole, entity)
        card.refresh()
        self._refresh_chrome()

    def remove_entity(self, entity: CloudEntity):
        row = self._row_of(entity)
        if row is None:
            return
        item, _card = self._rows.pop(row)
        self.list.takeItem(self.list.row(item))
        self._refresh_chrome()

    def current_entity(self):
        item = self.list.currentItem()
        return None if item is None else item.data(Qt.UserRole)

    def select_entity(self, entity: CloudEntity):
        row = self._row_of(entity)
        if row is not None:
            self.list.setCurrentRow(row)

    def set_visible(self, entity: CloudEntity, visible: bool):
        row = self._row_of(entity)
        if row is None:
            return
        if entity.visible == visible:
            return
        entity.visible = visible
        self._rows[row][1].refresh()
        self.visibility_changed.emit(entity)

    def card_count(self) -> int:
        return len(self._rows)

    def card_summary(self, index: int) -> dict:
        if not (0 <= index < len(self._rows)):
            return {}
        card = self._rows[index][1]
        return {
            "name": card.name.text(),
            "points": card.sub.text(),
            "selected": bool(card.property("selected")),
        }

    # ---------------- 内部 ----------------
    def _refresh_chrome(self):
        self.lbl_count.setText(str(len(self._rows)))
        has_rows = bool(self._rows)
        self.list.setVisible(has_rows)
        self.empty.setVisible(not has_rows)
        self._sync_selected()

    def _row_of(self, entity: CloudEntity):
        for i, (item, card) in enumerate(self._rows):
            if card.entity is entity or (entity.path and card.entity.path == entity.path):
                return i
        return None

    def _select_card(self, card: SceneCard):
        row = self._row_of(card.entity)
        if row is not None:
            self.list.setCurrentRow(row)

    def _on_selection(self):
        self._sync_selected()
        self.entity_selected.emit(self.current_entity())

    def _sync_selected(self):
        current = self.list.currentRow()
        for i, (_item, card) in enumerate(self._rows):
            card.set_selected(i == current)

    def _on_visibility(self, card: SceneCard):
        self.visibility_changed.emit(card.entity)

    def _context_menu(self, card: SceneCard, global_pos):
        self._select_card(card)
        entity = card.entity
        menu = QMenu(self)
        act_focus = menu.addAction("聚焦视图")
        act_hide = menu.addAction("隐藏" if entity.visible else "显示")
        act_reload = menu.addAction("重新加载")
        menu.addSeparator()
        act_remove = menu.addAction("移除")
        chosen = menu.exec(global_pos)
        if chosen is act_focus:
            self.focus_requested.emit(entity)
        elif chosen is act_hide:
            self.set_visible(entity, not entity.visible)
        elif chosen is act_reload:
            self.reload_requested.emit(entity)
        elif chosen is act_remove:
            self.remove_requested.emit(entity)
