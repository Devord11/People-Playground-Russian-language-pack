#!/usr/bin/env python3
"""
Собирает ZIP для установки перевода «в одно действие».

Что делает:
  1. Скачивает официальные архивы BepInEx и XUnity.AutoTranslator с GitHub.
  2. Проверяет их SHA-256 (значения зашиты ниже) — при несовпадении останавливается.
  3. Складывает всё в один ZIP так, чтобы его содержимое можно было просто
     скопировать в папку с игрой (корень архива = корень папки игры).

Запуск:
    python tools/build_release.py
    python tools/build_release.py --font путь/к/arialuni_sdf_u2019   # положить шрифт в архив

Шрифт по умолчанию НЕ включается (см. THIRD-PARTY-NOTICES.md).
"""
import argparse, hashlib, sys, urllib.request, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
CACHE = DIST / "cache"

SOURCES = {
    "BepInEx_win_x64_5.4.23.6.zip": (
        "https://github.com/BepInEx/BepInEx/releases/download/v5.4.23.6/BepInEx_win_x64_5.4.23.6.zip",
        "6c57a714a892efb4e9e1fef63d608a3391f30ec984031c465404e4ee381a0755",
    ),
    "XUnity.AutoTranslator-BepInEx-5.6.3.1.zip": (
        "https://github.com/bbepis/XUnity.AutoTranslator/releases/download/v5.6.3.1/XUnity.AutoTranslator-BepInEx-5.6.3.1.zip",
        "6c3ff03aafe9708f25c2115c0c04c255b6a9d88e716896ae7bacb590a8777609",
    ),
}
SKIP = {"BepInEx/plugins/README (AutoTranslator).md"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(name: str) -> Path:
    url, expected = SOURCES[name]
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / name
    if not path.exists():
        print(f"Скачиваю {name} ...")
        urllib.request.urlretrieve(url, path)
    got = sha256(path)
    if got != expected:
        path.unlink(missing_ok=True)
        sys.exit(f"ОШИБКА: контрольная сумма {name} не совпала.\n  ожидалось {expected}\n  получено  {got}")
    print(f"OK  {name}  sha256 {got[:16]}...")
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", help="файл шрифтового бандла (arialuni_sdf_u2019), если хотите включить его в архив")
    args = ap.parse_args()

    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    DIST.mkdir(exist_ok=True)
    out = DIST / f"PeoplePlayground-RU-v{version}.zip"
    if out.exists():
        out.unlink()

    written = set()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        def put(arcname, data):
            if arcname in written:
                return
            written.add(arcname)
            z.writestr(arcname, data)

        # наши файлы — первыми, чтобы они имели приоритет
        put("BepInEx/config/AutoTranslatorConfig.ini", (ROOT / "config/AutoTranslatorConfig.ini").read_bytes())
        put("BepInEx/Translation/ru/Text/main.txt", (ROOT / "translation/main.txt").read_bytes())
        put("BepInEx/Translation/ru/LICENSE", (ROOT / "LICENSE").read_bytes())
        put("BepInEx/Translation/ru/THIRD-PARTY-NOTICES.md", (ROOT / "THIRD-PARTY-NOTICES.md").read_bytes())
        if args.font:
            fp = Path(args.font)
            put(fp.name, fp.read_bytes())

        for name in SOURCES:
            with zipfile.ZipFile(fetch(name)) as src:
                for info in src.infolist():
                    if info.is_dir() or info.filename in SKIP:
                        continue
                    put(info.filename, src.read(info))

    print(f"\nГотово: {out}\nSHA-256: {sha256(out)}\nФайлов в архиве: {len(written)}")
    if not args.font:
        print("Шрифтовой бандл в архив не включён — пользователь добавляет его сам (см. README).")


if __name__ == "__main__":
    main()
