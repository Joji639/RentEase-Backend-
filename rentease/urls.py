"""
URL configuration for rentease project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('common/',include('common.urls')),
    path('accounts/',include('accounts.urls')),
    path('authentication/',include('authentication.urls')),
    path('technicians/',include('technicians.urls')),
    path("admin_panel/", include("admin_panel.urls")),
    path("services/", include("services.urls")),
    path("listings/", include("listings.urls")),
    path("bookings/", include("bookings.urls")),
    path("chat/", include("chat.urls")),
    path("wishlist/", include("wishlist.urls")),
    path("rag/", include("rag.urls")),
    path("notifications/", include("notifications.urls")),

]
