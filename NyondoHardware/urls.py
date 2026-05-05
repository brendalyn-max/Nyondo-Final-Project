"""
URL configuration for NyondoHardware project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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
from django.urls import path
# from . import views
from web import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Authentication
    path('', views.index, name="index"),
    path('logout/', views.logout_view, name="logout"),
    
    # Dashboards (This handles the Home/Dashboard redirect)
    path('home/', views.home, name="home"),
    
    # Stock Management (Inventory)
    path('stock/', views.stock_list, name='stock_list'),
    path('stock/add/', views.add_stock, name='add_stock'),
    path('stock/edit/<int:item_id>/', views.edit_stock, name='edit_stock'),
    path('stock/delete/<int:item_id>/', views.delete_stock, name='delete_stock'),

    path('record_sale/', views.record_sale, name='record_sale'),

    # path('deposits/', views.Deposit, name='deposits'),
    path('deposits/', views.credit_scheme, name='credit_scheme'),

]
