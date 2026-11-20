from django.urls import path, re_path

from . import views

urlpatterns = [
    path('health/', views.health, name='health'),
    re_path(r'^v1/routes/plan/?$', views.PlanRouteView.as_view(), name='routes-plan'),
]
