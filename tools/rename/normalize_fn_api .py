# normalize_fn_api.py
from __future__ import annotations
from pathlib import Path
from datetime import date
import re
from typing import List, Dict, Optional, Union

_TR_MAP = str.maketrans({
    "ç":"c","ğ":"g","ı":"i","ö":"o","ş":"s","ü":"u",
    "Ç":"c","Ğ":"g","İ":"i","I":"i","Ö":"o","Ş":"s","Ü":"u",
})

def _slug(s: str) -> str:
    s = (s or "").strip().translate(_TR_MAP).lower()
    s = s.replace(" ", "_").replace("-", "_")
    s = re.sub(r"[^a-z0-9_]+", "", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "x"

def _val_date(d: Union[str, date]) -> str:
    if isinstance(d, date):
        return d.isoformat()
    try:
        date.fromisoformat(d)
        return d
    except Exception:
        raise ValueError("cekim_tarihi 'YYYY-MM-DD' olmalı")

def _norm_version(v: str) -> str:
    """
    'v01' ya da '01' → '01'
    """
    m = re.fullmatch(r"v?(\d{1,2})", str(v).strip().lower())
    if not m:
        raise ValueError("versiyon '01' ya da 'v01' biçiminde olmalı")
    return f"{int(m.group(1)):02d}"

def _strip_copy_suffix(p: Path) -> str:
    # "foo (1).xlsx" -> "foo.xlsx"
    return re.sub(r"\s*\(\d+\)(\.[^.]+)$", r"\1", p.name)

def _collect(folder: Path, exts: List[str]) -> List[Path]:
    exts = [e.lower().lstrip(".") for e in exts]
    return sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.lower().lstrip(".") in exts],
                  key=lambda x: x.name.lower())
# --- yeni yardımcı: dosya adı eşleştirme (stem + adın tamamı üzerinden) ---
def _name_matches(p: Path, needle: str) -> bool:
    """
    needle biçimleri:
      - "2021"              -> ad/stem içinde '2021' geçiyorsa eşleşir (contains)
      - "=rapor_2021"       -> ad (uzantısız stem) tam eşit ise eşleşir
      - "re:^rapor_2021$"   -> REGEX ile eşleşir
    """
    name = p.name.lower()
    stem = p.stem.lower()
    s = needle.strip()
    if s.startswith("re:"):
        pat = s[3:]
        return re.search(pat, name, flags=re.IGNORECASE) is not None
    if s.startswith("="):
        return stem == s[1:].lower()
    return (s.lower() in stem) or (s.lower() in name)

def donusturme(
    folder: Union[str, Path],
    kategori: str,
    cekim_tarihi: Union[str, date],
    versiyon: str,
    *,
    yil: Optional[str] = None,
    ay: Optional[str] = None,
    system: Optional[str] = None,
    part: Optional[str] = "",
    exts: List[str] = ("xlsx","csv"),
    mevcut_dosya_adi: Optional[str] = None,   # <<---- YENİ
    dry_run: bool = False
) -> Dict[str, int]:
    """
    <system>_<kategori>_<yil veya yıl-ay>_<cekim_tarihi>_part-<PP>_v<NN>.<ext>
    Sadece belli bir dosyayı dönüştürmek için 'mevcut_dosya_adi' kullan:
      - '2021'         -> içinde '2021' geçen dosyalar
      - '=tablo1_2021' -> adı (stem) tam olarak 'tablo1_2021' olan
      - 're:^2021_'    -> regex ile eşleşen
    """
    folder = Path(folder).expanduser().resolve()
    if not folder.is_dir():
        raise FileNotFoundError(f"Klasör bulunamadı: {folder}")

    # system/yıl çıkarımı (gerekirse)
    if not system or not yil:
        parts = [p.name for p in folder.parts]
        if not yil:
            for p in reversed(parts):
                if re.fullmatch(r"\d{4}", p):
                    yil = p; break
        if not system and yil and yil in parts:
            idx = parts.index(yil)
            if idx-2 >= 0: system = parts[idx-2]

    if not yil:
        raise ValueError("yil belirlenemedi: parametre ver veya yolunda /<yil>/ olsun")
    system = _slug(system or "data")
    kategori = _slug(kategori)
    if ay:
        if not re.fullmatch(r"(0[1-9]|1[0-2])", ay):
            raise ValueError("ay 'MM' olmalı")
    ytoken = f"{yil}-{ay}" if ay else yil
    cap = _val_date(cekim_tarihi)
    ver = _norm_version(versiyon)

    # dosyaları topla + filtrele
    all_files = _collect(folder, list(exts))
    if mevcut_dosya_adi:
        files = [p for p in all_files if _name_matches(p, mevcut_dosya_adi)]
    else:
        files = all_files

    if not files:
        return {"renamed":0, "skipped":0, "total":0}

    multi = len(files) > 1
    fixed_part = None
    if part:
        m = re.fullmatch(r"(?:part-)?(\d{1,2})", str(part).strip().lower())
        if not m:
            raise ValueError("part boş, '05' ya da 'part-05' olmalı")
        fixed_part = f"part-{int(m.group(1)):02d}"

    renamed = skipped = 0
    for i, src in enumerate(files, start=1):
        suffix = f".{src.suffix.lstrip('.').lower()}"
        part_token = f"_{fixed_part}" if fixed_part else (f"_part-{i:02d}" if multi else "")
        new_name = f"{system}_{kategori}_{ytoken}_{cap}{part_token}_v{ver}{suffix}"
        dst = src.with_name(new_name)

        if src.name == new_name:
            skipped += 1
            continue
        if not dry_run:
            if dst.exists() and src.resolve() != dst.resolve():
                raise FileExistsError(f"Hedef zaten var: {dst.name}")
            src.rename(dst)
        renamed += 1

    return {"renamed": renamed, "skipped": skipped, "total": len(files)}


def batch_donustur(jobs: List[dict]) -> List[Dict[str,int]]:
    """
    jobs içindeki her dict, donusturme(...) ile aynı parametreleri taşır.
    Örn.:
      jobs = [
        dict(folder=".../tablo1/csv", kategori="tablo1", cekim_tarihi="2025-10-01", versiyon="v01", yil="2021", system="oms", mevcut_dosya_adi="2021"),
        dict(folder=".../tablo1/csv", kategori="tablo1", cekim_tarihi="2025-10-01", versiyon="v01", yil="2022", system="oms", mevcut_dosya_adi="2022"),
        dict(folder=".../tablo1/csv", kategori="tablo1", cekim_tarihi="2025-10-01", versiyon="v01", yil="2023", system="oms", mevcut_dosya_adi="2023"),
      ]
    """
    results = []
    for t in jobs:
        results.append(donusturme(**t))
    return results

# dikkat et csv/2021 , yil=2021, mevcut_dosya_adi=2021 hepsi aynı olmalı

jobs = [
  dict(folder="data/rapor/ham_veri/oms/tablo1/csv/2021/", kategori="tablo1", cekim_tarihi="2025-10-01", versiyon="v01", yil="2021", system="oms", mevcut_dosya_adi="2021"),
  dict(folder="data/rapor/ham_veri/oms/tablo1/csv/2022/", kategori="tablo1", cekim_tarihi="2025-10-01", versiyon="v01", yil="2022", system="oms", mevcut_dosya_adi="2022"),
  dict(folder="data/rapor/ham_veri/oms/tablo1/csv/2023/", kategori="tablo1", cekim_tarihi="2025-10-01", versiyon="v01", yil="2023", system="oms", mevcut_dosya_adi="2023"),
  dict(folder="data/rapor/ham_veri/oms/periyodik/bildirim/csv/2021/", kategori="bildirim", cekim_tarihi="2025-10-01", versiyon="v01", yil="2021", system="oms", mevcut_dosya_adi="2021"),
  dict(folder="data/rapor/ham_veri/oms/periyodik/bildirim/csv/2022/", kategori="bildirim", cekim_tarihi="2025-10-01", versiyon="v01", yil="2022", system="oms", mevcut_dosya_adi="2022"),
  dict(folder="data/rapor/ham_veri/oms/periyodik/bildirim/csv/2023/", kategori="bildirim", cekim_tarihi="2025-10-01", versiyon="v01", yil="2023", system="oms", mevcut_dosya_adi="2023"),
  dict(folder="data/rapor/ham_veri/oms/periyodik/kesinti/csv/2021/", kategori="kesinti", cekim_tarihi="2025-10-01", versiyon="v01", yil="2021", system="oms", mevcut_dosya_adi="2021"),
  dict(folder="data/rapor/ham_veri/oms/periyodik/kesinti/csv/2022/", kategori="kesinti", cekim_tarihi="2025-10-01", versiyon="v01", yil="2022", system="oms", mevcut_dosya_adi="2022"),
  dict(folder="data/rapor/ham_veri/oms/periyodik/kesinti/csv/2023/", kategori="kesinti", cekim_tarihi="2025-10-01", versiyon="v01", yil="2023", system="oms", mevcut_dosya_adi="2023"),
  dict(folder="data/rapor/ham_veri/osos/erisim_raporu/2021/", kategori="erisim_raporu", cekim_tarihi="2025-07-10", versiyon="v01", yil="2021", system="osos"), # mevcut dosya adi yazmadım tüm dosyalara otomatik part ekledi
  dict(folder="data/rapor/ham_veri/osos/erisim_raporu/2022/", kategori="erisim_raporu", cekim_tarihi="2025-07-10", versiyon="v01", yil="2022", system="osos"),
  dict(folder="data/rapor/ham_veri/osos/erisim_raporu/2023/", kategori="erisim_raporu", cekim_tarihi="2025-07-10", versiyon="v01", yil="2023", system="osos"),
  dict(folder="data/rapor/ham_veri/osos/haberlesme_unitesi/2021/", kategori="haberlesme_unitesi", cekim_tarihi="2025-07-12", versiyon="v01", yil="2021", system="osos"),
  dict(folder="data/rapor/ham_veri/osos/haberlesme_unitesi/2022/", kategori="haberlesme_unitesi", cekim_tarihi="2025-07-12", versiyon="v01", yil="2022", system="osos"),
  dict(folder="data/rapor/ham_veri/osos/haberlesme_unitesi/2023/", kategori="haberlesme_unitesi", cekim_tarihi="2025-07-12", versiyon="v01", yil="2023", system="osos"),
  dict(folder="data/rapor/ham_veri/crm/bildirim/2022/", kategori="bildirim", cekim_tarihi="2025-06-18", versiyon="v01", yil="2022", system="crm"),
  dict(folder="data/rapor/ham_veri/crm/bildirim/2023/", kategori="bildirim", cekim_tarihi="2025-06-18", versiyon="v01", yil="2023", system="crm"),
  dict(folder="data/rapor/ham_veri/inavitas/duzeltme/kesinti_tahminleme/", kategori="duzeltme_kesinti_tahminleme_cakisanlar", cekim_tarihi="2025-10-02", versiyon="v01", yil="2022", system="inavitas", mevcut_dosya_adi="CAKISAN_KESINTILER"),
  dict(folder="data/rapor/ham_veri/inavitas/duzeltme/kesinti_tahminleme/", kategori="duzeltme_kesinti_tahminleme_bildirimler", cekim_tarihi="2025-10-02", versiyon="v01", yil="2022", system="inavitas", mevcut_dosya_adi="KESINTI_BILDIRIM_LISTESI"),
  dict(folder="data/rapor/ham_veri/inavitas/duzeltme/kesinti_tahminleme/", kategori="duzeltme_kesinti_tahminleme_kesintiler", cekim_tarihi="2025-10-02", versiyon="v01", yil="2022", system="inavitas", mevcut_dosya_adi="KESINTILER"),
  dict(folder="data/rapor/ham_veri/inavitas/duzeltme/kesinti_tahminleme/", kategori="duzeltme_kesinti_tahminleme_bildirimler_crmid", cekim_tarihi="2025-10-02", versiyon="v01", yil="2022", system="inavitas", mevcut_dosya_adi="CRM_ID_ESLESTIRME"),
  dict(folder="data/rapor/ham_veri/inavitas/duzeltme/eslesmeyen_cbs/", kategori="duzeltme_eslesmeyen_cbs", cekim_tarihi="2025-09-19", versiyon="v01", yil="2022", system="inavitas"),

]
batch_donustur(jobs)