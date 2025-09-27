# duzeltme/importers.py
import csv, io

from imports.base import BaseImporter
from imports.registry import register         # registry decorator
from imports.utils import to_seconds_naive    # <<< yeni yardımcı (saniyeye kırp / tz'i at)
from .models import HaberlesmeKesinti


@register("haberlesme_kesinti")   # Upload formundaki “hedef” anahtarı
class HaberlesmeKesintiImporter(BaseImporter):
    model = HaberlesmeKesinti
    file_kinds = ("csv",)
    required_headers = ("modem", "baslangic", "bitis", "sure")

    # Her yüklemede tabloyu komple temizle (TRUNCATE) ve baştan doldur
    replace_all = True

    def parse(self, file, kind: str, sheet: str | None = None):
        """
        CSV; ayraç ';'
        Başlıklar: modem;baslangic;bitis;sure
        """
        wrapper = io.TextIOWrapper(file, encoding="utf-8-sig", newline="")
        reader = csv.DictReader(wrapper, delimiter=";")

        for row in reader:
            modem = (row.get("modem") or "").strip()
            bas   = to_seconds_naive(row.get("baslangic"))  # -> 2022-01-01 10:43:32
            bit   = to_seconds_naive(row.get("bitis"))      # -> 2022-01-01 10:43:32
            sure  = int((row.get("sure") or "0").strip())

            # Zorunlu alanlar boşsa satırı atla
            if not (modem and bas and bit):
                continue

            yield {
                "modem": modem,
                "baslangic": bas,
                "bitis": bit,
                "sure": sure,
            }

    def to_instance(self, data: dict):
        return HaberlesmeKesinti(**data)
