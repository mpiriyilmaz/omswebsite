from django.urls import path
from . import views

app_name = "duzeltme"

urlpatterns = [
    # Varsayılan sayfa: /tablo1duzeltme/<vendor>/<year>/
    path("<str:vendor>/<int:year>/", views.ozet, name="ozet"),

    # Esnek sayfa rotası: /tablo1duzeltme/<vendor>/<year>/<page>/
    # page = "tablo1_detay", "tablo1_yeni", "ag_duzeltmeler", "ic_ice_duzeltmeler" ...
    path("<str:vendor>/<int:year>/<slug:page>/", views.page, name="page"),
]
