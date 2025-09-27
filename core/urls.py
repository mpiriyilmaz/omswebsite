"""
URL configuration for aras project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView  # <-- EKLE

urlpatterns = [
    path("admin/", admin.site.urls),

    # /index/ -> duzeltme:ozet (vendor/yıl default)
    # login olduğun zaman yönlendirilecek sayfa belirliyoruz 
    # account/views.py/ def login_request(request): fonksiyonundan yönlendiriyoruz
    path(
        "index/",
        RedirectView.as_view(
            pattern_name="duzeltme:ozet",
            permanent=False
        ),
        {"vendor": "inavitas", "year": 2022},   # <-- default hedef
        name="index",
    ),

    # Login & logout (account.urls içinde name="login" mevcut)
    path("", include("account.urls")),

    # Diğer app’ler
    # path("rapor/", include(("rapor.urls", "rapor"), namespace="rapor")),
    path("duzeltme/", include(("duzeltme.urls", "duzeltme"), namespace="duzeltme")),
    # path("imports/", include(("imports.urls","imports"), namespace="imports")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
