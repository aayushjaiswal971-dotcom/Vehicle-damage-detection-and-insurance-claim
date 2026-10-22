"""
core/urls.py — URL patterns for the core app.
"""

from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    # Landing / auth
    path("", views.landing, name="index"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # Protected views
    path("dashboard/", views.dashboard, name="dashboard"),
    path("upload/", views.upload_image, name="upload"),
    path("result/<int:pk>/", views.image_result, name="result"),
    path("history/", views.history, name="history"),

    # Claim Estimator & ROI Benchmarking (Adapted from 21st.dev template)
    path("claim-estimator/", views.claim_estimator, name="claim_estimator"),
    path("claim-estimator/calculate/", views.calculate_claim_api, name="calculate_claim_api"),
]
