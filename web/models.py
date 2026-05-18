from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator

ugandan_phone_rule = RegexValidator(
    regex=r'^(?:\+256|256|0)?(7\d{8})$',
    message="Validation Error: Provide a valid Ugandan phone line (e.g., 0772000000 or +256752000000)."
)

ugandan_nin_rule = RegexValidator(
    regex=r'^[A-Z]{2}\d{2}[A-Z\d]{2}\d{7}[A-Z\d]{1}$',
    message="Validation Error: NIN must contain exactly 14 characters following the official NIRA layout framework."
)

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

class Item(models.Model):
    name = models.CharField(max_length=50, unique=True)  # Cement, Iron Sheets, Iron Bars
    price = models.DecimalField(max_digits=12, decimal_places=0)

    def __str__(self):
        return self.name
    
class SalaryEarner(models.Model):
    national_id_name = models.CharField(max_length=100)
    # 🛠️ MODIFIED: Enforced exact 14 character NIRA limit with the validation guard rule
    nin_number = models.CharField(max_length=14, unique=True, validators=[ugandan_nin_rule])
    # 🛠️ MODIFIED: Added phone number formatting protection
    phone_number = models.CharField(max_length=15, validators=[ugandan_phone_rule])
    workplace = models.CharField(max_length=100, blank=True, null=True)

    # Scheme fields
    target_product = models.ForeignKey(Item, on_delete=models.CASCADE, null=True, blank=True)
    target_quantity = models.PositiveIntegerField(default=1)
    
    # 🛠️ MODIFIED: Changed max decimals to 0 for standard Ugandan Shilling currency tracking
    target_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    credit_balance = models.DecimalField(max_digits=12, decimal_places=0, default=0)

    @property
    def progress(self):
        if self.target_amount > 0:
            # 🛠️ MODIFIED: Added a min/round clamp so the bar neatly caps at 100.0% max on screen
            percent = (self.credit_balance / self.target_amount) * 100
            return min(round(percent, 1), 100.0)
        return 0

    def __str__(self):
        return self.national_id_name

class Deposit(models.Model):
    salary_earner = models.ForeignKey(SalaryEarner, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=0)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.salary_earner.national_id_name} - UGX {self.amount}"
class CustomUser(AbstractUser):

    ROLE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('STOCK', 'Stock Manager'),
        ('CASHIER', 'Cashier'),
        ('SALES', 'Sales Person'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='CASHIER'
    )

    phone = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.username} ({self.role})"

    
