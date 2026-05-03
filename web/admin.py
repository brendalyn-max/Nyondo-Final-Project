from django.contrib import admin
from .models import Category, Supplier, StockItem, Sale
# Register your models here.
admin.site.register(Category)
admin.site.register(Supplier)
admin.site.register(StockItem)
admin.site.register(Sale)
