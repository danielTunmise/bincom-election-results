"""URLs of the elections app: 3 pages + 2 small JSON endpoints."""
from django.urls import path

from . import views

urlpatterns = [
    # The three pages
    path("", views.polling_unit_result, name="polling_unit_result"),       # Question 1
    path("lga-total/", views.lga_total, name="lga_total"),                 # Question 2
    path("add-result/", views.add_polling_unit, name="add_polling_unit"),  # Question 3
    # JSON endpoints used by the chained dropdowns (JavaScript fetch())
    path("api/wards/", views.api_wards, name="api_wards"),
    path("api/polling-units/", views.api_polling_units, name="api_polling_units"),
]
