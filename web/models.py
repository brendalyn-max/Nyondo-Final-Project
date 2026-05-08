from django.db import models
from django.contrib.auth.models import AbstractUser

class Category(models.Model):
    name = models.CharField(max_length=200)
    def __str__(self):
        return self.name

class Supplier(models.Model):
    name = models.CharField(max_length=100)              
    contact = models.CharField(max_length=100, blank=True, null=True) 
    address = models.CharField(max_length=200, blank=True, null=True)  
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0) 
    def __str__(self):
        return self.name

class StockItem(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    unit = models.CharField(max_length=20)
    quantity = models.IntegerField(default=0)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=0)
    selling_price = models.DecimalField(max_digits=12, decimal_places=0)
    reorder_level = models.IntegerField(default=5)
    specifications = models.TextField(blank=True, null=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="items")

    def __str__(self):
        return f"{self.name} ({self.category.name})"

    @property
    def status_label(self):
        """Logic for your color-coded status badges"""
        if self.quantity <= 0:
            return "Out of stock"
        elif self.quantity <= self.reorder_level:
            return "Low stock"
        return "In stock"


from django.conf import settings

class Sale(models.Model):
    SALE_TYPES = (
        ('WALK_IN', 'Walk-In'),
        ('WHOLESALE', 'Wholesale'),
        ('SCHEME', 'Scheme Pickup'),
    )
    
    sale_type = models.CharField(max_length=20, choices=SALE_TYPES, default='WALK_IN')
    item = models.ForeignKey(StockItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=12, decimal_places=0)
    customer_name = models.CharField(max_length=100, default="Walk-in")
    member_nin = models.CharField(max_length=14, blank=True, null=True)  
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    date_sold = models.DateTimeField(auto_now_add=True)
    distance = models.FloatField(default=0.0)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.sale_type} - {self.item.name}"


class SalaryEarner(models.Model):
    national_id_name = models.CharField(max_length=100)
    nin_number = models.CharField(max_length=20, unique=True)
    phone_number = models.CharField(max_length=15)
    workplace = models.CharField(max_length=100, blank=True, null=True) # e.g. KCCA

    def __str__(self):
        return self.national_id_name

class Deposit(models.Model):
    salary_earner = models.ForeignKey(SalaryEarner, on_delete=models.CASCADE)
    product = models.ForeignKey('StockItem', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1) 
    amount = models.DecimalField(max_digits=12, decimal_places=0)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.salary_earner.national_id_name} - {self.amount}"

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('STOCK', 'Stock'),
        ('CASHIER', 'Cashier'),
        ('SALES', 'Sales'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='ADMIN')

    def __str__(self):
        return self.username