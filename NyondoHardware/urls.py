"""
URL configuration for NyondoHardware project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djan
  goproject.com/en/6.0/topics/http/urls/
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

    # Main dashboard (role-based redirect)
    path('home/', views.home, name="home"),

    # Role-specific dashboards
    path('admin_dashboard/', views.admin_dashboard, name="admin_dashboard"),
    path('stock_dashboard/', views.stock_dashboard, name="stock_dashboard"),
    path('cashier_dashboard/', views.cashier_dashboard, name="cashier_dashboard"),
    path('sales_dashboard/', views.sales_dashboard, name="sales_dashboard"),

    # Operations
    path('stock/', views.stock_list, name='stock_list'),
    path('stock/add/', views.add_stock, name='add_stock'),
    path('stock/edit/<int:item_id>/', views.edit_stock, name='edit_stock'),
    path('stock/delete/<int:item_id>/', views.delete_stock, name='delete_stock'),

    path('record_sale/', views.record_sale, name='record_sale'),
    path('sales_today/', views.sales_today, name='sales_today'),
    path('sale/<int:sale_id>/', views.sale_detail, name='sale_detail'),
    path('deposits/', views.credit_scheme, name='credit_scheme'),

    # Records
    # path('receipts/', views.receipts, name='receipts'),
    path('suppliers/', views.suppliers, name='suppliers'),
    path("scheme_enrollees/", views.scheme_enrollees, name="scheme_enrollees"),
    path("scheme_enrollees/edit/<int:pk>/", views.edit_enrollee, name="edit_enrollee"),
    path("scheme_enrollees/delete/<int:pk>/", views.delete_enrollee, name="delete_enrollee"),
    # path('reports/', views.reports, name='reports'),
    path('reports/', views.reports, name='reports'),

    # Admin tools
    # path('user_management/', views.user_management, name='user_management'),
    path('users/', views.user_management, name='user_management'),
    path('users/toggle/<int:user_id>/', views.toggle_user, name='toggle_user'),
]