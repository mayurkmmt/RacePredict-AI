from django.urls import path
from . import views

app_name = "racing"
urlpatterns = [
    path("", views.dashboard_view, name="dashboard_ui"),
    path("race-center/", views.race_center_view, name="race_center_ui"),
    path("races/by-date/", views.races_by_date_api, name="races_by_date"),
    path("races/<int:id>/predict/", views.race_predict_api, name="race_predict"),
    path("races/<int:id>/details/", views.race_details_api, name="race_details"),
]
