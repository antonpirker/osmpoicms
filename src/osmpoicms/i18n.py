import json
from pathlib import Path

from fastapi import Request

_SUPPORTED = {"en", "de"}
_DEFAULT = "en"
_translations: dict[str, dict] = {}

for _lang in _SUPPORTED:
    _path = Path(__file__).parent / "translations" / f"{_lang}.json"
    with open(_path, encoding="utf-8") as _f:
        _translations[_lang] = json.load(_f)


def get_lang(request: Request) -> str:
    lang = request.cookies.get("lang")
    if lang in _SUPPORTED:
        return lang
    accept = request.headers.get("accept-language", "")
    for part in accept.split(","):
        tag = part.split(";")[0].strip().lower()[:2]
        if tag in _SUPPORTED:
            return tag
    return _DEFAULT


def get_t(request: Request) -> tuple[str, dict]:
    lang = get_lang(request)
    return lang, _translations[lang]
