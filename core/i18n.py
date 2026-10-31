"""E26：界面文案的多语言脚手架。

当前只有中文与英文两份核心文案，用于窗口标题与“关于”对话框；
其余界面暂保持中文。新增语言只需扩展 ``_CATALOGS``。
"""

from __future__ import annotations

_CATALOGS: dict[str, dict[str, str]] = {
    "zh": {},
    "en": {
        "PointLab Studio — 点云工作站": "PointLab Studio — Point Cloud Workbench",
        "关于 PointLab Studio": "About PointLab Studio",
        "加载失败": "Load failed",
        "已取消": "Cancelled",
        "就绪": "Ready",
    },
}

_language = "zh"


def available_languages() -> list[str]:
    return sorted(_CATALOGS)


def set_language(lang: str) -> None:
    global _language
    if lang not in _CATALOGS:
        raise ValueError(f"不支持的语言: {lang}")
    _language = lang


def get_language() -> str:
    return _language


def tr(text: str) -> str:
    """把中文原文翻译成当前语言；缺词条时原样返回。"""
    return _CATALOGS.get(_language, {}).get(text, text)
