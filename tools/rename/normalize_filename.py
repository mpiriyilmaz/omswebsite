# rename_batch.py
'''
klasor altındaki dosya isimlerini standart haline getirir
'''
from __future__ import annotations
import re
from pathlib import Path
from datetime import date
from typing import List, Tuple

def ask(prompt: str, default: str | None = None, validator=None) -> str:
    while True:
        raw = input(f"{prompt}{f' [{default}]' if default else ''}: ").strip()
        val = raw or (default or "")
        if not validator or validator(val):
            return val
        print("⚠️  Geçersiz değer, tekrar deneyin.")

def val_nonempty(s: str) -> bool:
    return len(s.strip()) > 0

def val_year(s: str) -> bool:
    return bool(re.fullmatch(r"\d{4}", s))

def val_month_or_empty(s: str) -> bool:
    return s == "" or bool(re.fullmatch(r"(0[1-9]|1[0-2])", s))

def val_iso_date(s: str) -> bool:
    try:
        date.fromisoformat(s)
        return True
    except Exception:
        return False

def val_version(s: str) -> bool:
    return bool(re.fullmatch(r"\d{1,2}", s))

def slugify_piece(s: str) -> str:
    # Basit normalizasyon: boşluk -> _, sadece a-z0-9-_
    s = s.strip().lower().replace(" ", "_").replace("-", "_")
    s = re.sub(r"[^a-z0-9_]+", "", s)
    return s

def collect_files(folder: Path, exts: List[str], sort_key: str) -> List[Path]:
    items = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower().lstrip(".") in exts]
    if sort_key == "name":
        items.sort(key=lambda p: p.name.lower())
    elif sort_key == "mtime":
        items.sort(key=lambda p: p.stat().st_mtime)
    else:
        items.sort(key=lambda p: p.name.lower())
    return items

def build_targets(files: List[Path], base: str, version: str) -> List[Tuple[Path, Path]]:
    ops: List[Tuple[Path, Path]] = []
    multi = len(files) > 1
    for idx, f in enumerate(files, start=1):
        part = f"_part-{idx:02d}" if multi else ""
        new_name = f"{base}{part}_v{int(version):02d}{f.suffix.lower()}"
        ops.append((f, f.with_name(new_name)))
    return ops

def ensure_no_collisions(ops: List[Tuple[Path, Path]]) -> None:
    targets = [t for _, t in ops]
    # Aynı hedefe iki farklı kaynaktan gitme kontrolü
    names = [t.name for t in targets]
    dups = {n for n in names if names.count(n) > 1}
    if dups:
        raise RuntimeError(f"Aynı hedef adına birden fazla dosya üretiliyor: {sorted(dups)}")
    # Var olan dosya üzerine yazma kontrolü (kaynakla aynı değilse)
    for src, dst in ops:
        if dst.exists() and src.resolve() != dst.resolve():
            raise RuntimeError(f"Hedef zaten var: {dst.name}")

def preview(ops: List[Tuple[Path, Path]]) -> None:
    print("\n— Önizleme —")
    for src, dst in ops:
        if src.name == dst.name:
            print(f"  = {src.name}  (zaten uyumlu, atlanacak)")
        else:
            print(f"  {src.name}  →  {dst.name}")
    print(f"Toplam: {len(ops)} dosya")

def main():
    print("🧩 Toplu Dosya Yeniden Adlandırma (CSV/XLSX)")

    print(f"""
<system>_<kategori>_<yıl>_<çekim-tarihi>_part-<PP>_v<NN>.xlsx
örn:osos/osos_entegrasyonoms_2021-01_2025-07-08_part-03_v01.xlsx
    └klasör └─sys  └kategori  └yıl └ay └tarihi   └parça  └versiyon
          
""")

    # 1) Girdi parametreleri
    folder_str = ask("Klasör yolu", default=".", validator=val_nonempty)
    folder = Path(folder_str).expanduser().resolve()
    if not folder.is_dir():
        raise SystemExit(f"Bulunamadı veya klasör değil: {folder}")

    exts_raw = ask("Eklentiler (virgülle)", default="xlsx,csv", validator=val_nonempty)
    exts = [e.strip().lower().lstrip(".") for e in exts_raw.split(",") if e.strip()]

    sort_key = ask("Sıralama anahtarı (name|mtime)", default="name",
                   validator=lambda x: x in {"name", "mtime"})

    system = slugify_piece(ask("Sistem", validator=val_nonempty))                # örn: osos / oms / inavitas
    category = slugify_piece(ask("Kategori", validator=val_nonempty))            # örn: entegrasyon_oms
    year = ask("Yıl (YYYY)", validator=val_year)
    month = ask("Ay (MM, boş geçebilirsin)", default="", validator=val_month_or_empty)
    ytoken = f"{year}-{month}" if month else year

    today_iso = date.today().isoformat()
    cap_date = ask("Çekim tarihi (YYYY-MM-DD)", default=today_iso, validator=val_iso_date)

    version = ask("Versiyon (NN)", default="01", validator=val_version)

    # 2) Dosyaları topla
    files = collect_files(folder, exts, sort_key)
    if not files:
        raise SystemExit(f"Seçilen uzantılarda dosya yok: {folder}")

    # 3) Taban ad
    base = f"{system}_{category}_{ytoken}_{cap_date}"

    # 4) Hedefleri üret
    ops = build_targets(files, base, version)

    # 5) Çakışma kontrolü ve önizleme
    ensure_no_collisions(ops)
    preview(ops)

    # 6) Onay
    go = ask("Uygulansın mı? (y/N)", default="N").lower()
    if go != "y":
        print("İptal edildi.")
        return

    # 7) Yeniden adlandır
    changed = 0
    skipped = 0
    for src, dst in ops:
        if src.name == dst.name:
            skipped += 1
            continue
        src.rename(dst)
        changed += 1

    print(f"✅ Bitti. {changed} dosya yeniden adlandırıldı, {skipped} dosya zaten uyumluydu.")

if __name__ == "__main__":
    main()
