from django.contrib import admin
from django.urls import path, include  # ← исправленный импорт

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main.urls')),
    path('reg/', include('reg.urls'))
]
