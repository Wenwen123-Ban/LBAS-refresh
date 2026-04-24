from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.views.static import serve
import os

urlpatterns = [
    path('api/', include('api.urls')),
    path('', TemplateView.as_view(template_name='Index.html')),
    path('admin-portal/', TemplateView.as_view(template_name='Admin_dashboard_portal.html')),
    path('student-portal/', TemplateView.as_view(template_name='Student_dashboard_portal.html')),
]

if settings.DEBUG:
    # Serve static files (CSS, JS, etc.)
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', serve, {
            'document_root': os.path.join(settings.BASE_DIR, 'static'),
            'show_indexes': False,
        }),
        re_path(r'^media/(?P<path>.*)$', serve, {
            'document_root': os.path.join(settings.BASE_DIR, 'media'),
            'show_indexes': False,
        }),
    ]
