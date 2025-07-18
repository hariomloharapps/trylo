
# urls.py
from django.urls import path
from . import views

urlpatterns = [
    # HTML Template View
    path('contact/', views.contact_view, name='contact'),
    path('about/', views.about, name='about'),
    path('', views.index, name='index'),  # Home page view
    path('nowcloset_waitlist/', views.nowcloset_waitlist, name='nowcloset_waitlist'),

    # Admin dashboard (custom path)
    path('adminerstatin/jjsch/', views.admin_dashboard, name='admin_dashboard'),
    path('api/dashboard-data/', views.dashboard_data, name='dashboard_data'),
    path('api/export-waitlist/', views.export_waitlist_csv, name='export_waitlist_csv'),
    path('api/export-contact/', views.export_contact_csv, name='export_contact_csv'),

    # API View for saving data
    path('api/waitlist/join/', views.join_waitlist, name='join_waitlist'),
    path('api/waitlist/stats/', views.waitlist_stats, name='waitlist_stats'),
    path('api/contact/', views.contact_api, name='contact_api'),
]