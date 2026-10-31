"""E26：多语言脚手架。"""

import pytest

from core import i18n


def test_default_language_is_passthrough():
    i18n.set_language("zh")
    assert i18n.tr("就绪") == "就绪"
    assert i18n.tr("不存在的文案") == "不存在的文案"


def test_english_catalog_and_fallback():
    i18n.set_language("en")
    assert i18n.tr("就绪") == "Ready"
    assert i18n.tr("不存在的文案") == "不存在的文案"
    i18n.set_language("zh")


def test_unknown_language_rejected():
    with pytest.raises(ValueError):
        i18n.set_language("fr")
    assert "en" in i18n.available_languages()
