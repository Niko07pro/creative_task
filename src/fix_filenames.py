"""Чинит mojibake в именах файлов: UTF-8, прочитанный как CP866 → обратно в UTF-8."""
from pathlib import Path
import sys

SRC_DIR = Path("data/raw/dataset")
DRY_RUN = False

def try_fix(name: str):
    """Возвращает (исправленное_имя, был_ли_фикс_возможен)."""
    try:
        candidate = name.encode("cp866").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return name, False
    return candidate, candidate != name


def main():
    files = sorted(SRC_DIR.glob("*.jpg"))
    print(f"Found {len(files)} .jpg files in {SRC_DIR}")
    print(f"DRY_RUN = {DRY_RUN}")
    print()

    to_fix, ok, fail, collision = [], [], [], []

    for f in files:
        new_name, was_fixed = try_fix(f.name)
        if not was_fixed:
            ok.append(f.name)
            continue
        new_path = f.parent / new_name
        if new_path.exists() and new_path != f:
            collision.append((f.name, new_name))
            continue
        to_fix.append((f, new_path))

    print(f"  to fix     : {len(to_fix)}")
    print(f"  already ok : {len(ok)}")
    print(f"  collisions : {len(collision)}")
    print(f"  failed     : {len(fail)}")
    print()

    print("Примеры из to_fix (первые 10):")
    for old, new in to_fix[:10]:
        print(f"  {old.name!r}")
        print(f"    -> {new.name!r}")

    if collision:
        print("\nКоллизии (первые 5):")
        for old_name, new_name in collision[:5]:
            print(f"  {old_name!r} -> {new_name!r}")

    if not DRY_RUN:
        print("\nПереименовываю...")
        for old_path, new_path in to_fix:
            old_path.rename(new_path)
        print(f"Переименовано: {len(to_fix)} файлов")


if __name__ == "__main__":
    main()