from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Category, Deposit, Item, Supplier, StockItem, Sale, SalaryEarner

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('username', 'email')
    ordering = ('username',)

    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role',)}),  
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('role',)}),   
    )

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Category)
admin.site.register(Supplier)
admin.site.register(StockItem)
admin.site.register(Sale)
admin.site.register(SalaryEarner)
admin.site.register(Deposit)
admin.site.register(Item)
