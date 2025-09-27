from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse
from django.http import Http404

def _template_path(vendor: str, year: int, page: str) -> str:
    # Örn: templates/duzeltme/inavitas/2022/ozet.html
    return f"duzeltme/{vendor}/{year}/{page}.html"

def _tabs(vendor: str, year: int):
    # Üst sekmeler: vendor’a göre farklı menü
    if vendor == "inavitas":
        return [
            {"slug": "ozet",           "label": "Özet",
             "url": reverse("duzeltme:ozet", args=[vendor, year])},
            {"slug": "tablo1_detay",   "label": "Tablo1 Detay",
             "url": reverse("duzeltme:page", args=[vendor, year, "tablo1_detay"])},
            {"slug": "tablo1_yeni",    "label": "Yeni Tablo1",
             "url": reverse("duzeltme:page", args=[vendor, year, "tablo1_yeni"])},
        ]
    if vendor == "oms":
        return [
            {"slug": "ag_duzeltmeler",     "label": "AG Düzeltmeler",
             "url": reverse("duzeltme:page", args=[vendor, year, "ag_duzeltmeler"])},
            {"slug": "ic_ice_duzeltmeler", "label": "İç İçe Düzeltmeler",
             "url": reverse("duzeltme:page", args=[vendor, year, "ic_ice_duzeltmeler"])},
        ]
    return []

@login_required
def ozet(request, vendor: str, year: int):
    tabs = _tabs(vendor, year)
    if not tabs:
        raise Http404("Bilinmeyen vendor")
    ctx = {
        "vendor": vendor, "year": year,
        "top_tabs": tabs, "active_tab": "ozet",
        # SEO blokları için (global base.html’deki block’ları dolduruyoruz)
        "page_title": f"Tablo1 Düzeltme – {vendor.upper()} {year}",
        "page_description": f"{vendor.upper()} {year} özet sayfası",
        "page_keywords": f"{vendor},{year},tablo1,duzeltme",
    }
    return render(request, _template_path(vendor, year, "ozet"), ctx)

@login_required
def page(request, vendor: str, year: int, page: str):
    tabs = _tabs(vendor, year)
    if not tabs:
        raise Http404("Bilinmeyen vendor")
    ctx = {
        "vendor": vendor, "year": year,
        "top_tabs": tabs, "active_tab": page,
        "page_title": f"Tablo1 Düzeltme – {vendor.upper()} {year} – {page}",
        "page_description": f"{vendor.upper()} {year} {page} sayfası",
        "page_keywords": f"{vendor},{year},{page},tablo1,duzeltme",
    }
    return render(request, _template_path(vendor, year, page), ctx)
