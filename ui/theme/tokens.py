"""Design Tokens：Apple / Google 风格配色、字体、圆角、间距（方案 §5）。

深色为默认主题；浅色可选。视口背景用渐变（径向微光，类 Apple 3D 展示风格）。
"""

from __future__ import annotations

# 字体：Inter（风格接近 SF Pro，开源可分发）；中文回退微软雅黑/PingFang SC
FONTS = {
    "ui": '"Inter", "Segoe UI Variable", "Segoe UI", "PingFang SC", "Microsoft YaHei UI", "Microsoft YaHei"',
    "mono": '"JetBrains Mono", "Cascadia Code", "Consolas"',
}

RADII = {"control": 6, "input": 8, "card": 12, "dialog": 16}
SPACING = {"xs": 4, "s": 8, "m": 12, "l": 16, "xl": 24, "xxl": 32}

DARK = {
    "name": "dark",
    "bg": "#0D0D0F",
    "panel": "#1C1C1E",
    "panel2": "#2C2C2E",
    "panel3": "#3A3A3C",
    "border": "rgba(255, 255, 255, 0.08)",
    "border_strong": "rgba(255, 255, 255, 0.16)",
    "text": "#F5F5F7",
    "text2": "#98989D",
    "text3": "#636366",
    "accent": "#0A84FF",
    "accent_hover": "#3395FF",
    "accent_text": "#FFFFFF",
    "selection": "rgba(10, 132, 255, 0.35)",
    "success": "#30D158",
    "warning": "#FF9F0A",
    "danger": "#FF453A",
    "viewport_top": "#101016",
    "viewport_bottom": "#050507",
    "pill_bg": "rgba(28, 28, 30, 0.90)",
    "pill_border": "rgba(255, 255, 255, 0.14)",
    "pill_hover": "rgba(255, 255, 255, 0.10)",
    "disabled": "rgba(255, 255, 255, 0.35)",
}

LIGHT = {
    "name": "light",
    "bg": "#F5F5F7",
    "panel": "#FFFFFF",
    "panel2": "#F2F2F7",
    "panel3": "#E2E5EB",
    "border": "#C8CDD5",
    "border_strong": "#959DA9",
    "text": "#1D1D1F",
    "text2": "#454B56",
    "text3": "#59616D",
    "accent": "#005FCC",
    "accent_hover": "#0054B5",
    "accent_text": "#FFFFFF",
    "selection": "#DFEBFC",
    "success": "#21743A",
    "warning": "#965000",
    "danger": "#C52D25",
    "viewport_top": "#EDEDF0",
    "viewport_bottom": "#D8D8DD",
    "pill_bg": "rgba(255, 255, 255, 0.92)",
    "pill_border": "rgba(0, 0, 0, 0.10)",
    "pill_hover": "rgba(0, 0, 0, 0.06)",
    "disabled": "#737B87",
}

THEMES = {"dark": DARK, "light": LIGHT}


def get_theme(name: str) -> dict:
    return THEMES.get(name, DARK)


def theme_names() -> list:
    return list(THEMES.keys())
