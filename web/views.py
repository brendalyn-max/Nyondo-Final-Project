from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.core.exceptions import PermissionDenied
import decimal
from django.utils.timezone import now
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
# from django.contrib import messages

from django.db.models import Sum, Count, F, ExpressionWrapper, DecimalField
from django.contrib.auth.decorators import login_required
from .models import *


# 1. authentication views
def index(request):
    if request.user.is_authenticated:
        # send user to correct dashboard automatically
        if hasattr(request.user, "role"):
            if request.user.role == "CASHIER":
                return redirect("cashier_dashboard")
            elif request.user.role == "STOCK":
                return redirect("stock_dashboard")
            elif request.user.role == "SALES":
                return redirect("sales_dashboard")

        return redirect("admin_dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # 🔥 ROLE REDIRECT HERE
            if hasattr(user, "role"):
                if user.role == "CASHIER":
                    return redirect("cashier_dashboard")
                elif user.role == "STOCK":
                    return redirect("stock_dashboard")
                elif user.role == "SALES":
                    return redirect("sales_dashboard")

            return redirect("admin_dashboard")

        messages.error(request, "Invalid username or password")
        return redirect("index")

    return render(request, "landing.html")

def logout_view(request):
    """ Logout functionality """
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("index")

# 2. main dashboard views

@login_required(login_url='/')
def home(request):
    items = StockItem.objects.all()
    
    context = {
        'total_lines': items.count(),
        'low_stock_count': sum(1 for item in items if item.status_label == "Low stock"),
        'out_of_stock_count': items.filter(quantity__lte=0).count(),
        'recent_items': items.order_by('-id')[:5],
    }
    
    user_role = getattr(request.user, 'role', 'ADMIN')

    if user_role == 'STOCK':
        return render(request, "stock_dashboard.html", context)
    elif user_role == 'CASHIER':
        return render(request, "cashier_dashboard.html", context)
    elif user_role == 'SALES':
        return render(request, "sales_dashboard.html", context)
        
    return render(request, "home.html", context)
@login_required
def admin_dashboard(request):

    today = timezone.now().date()

    # TODAY REVENUE (DB optimized)
    todays_revenue = Sale.objects.filter(
        date_sold__date=today
    ).aggregate(
        total=Sum('total_price')
    )['total'] or 0

    # TOTAL PROFIT (optimized in DB instead of Python loop)
    total_profit = Sale.objects.aggregate(
        profit=Sum(
            ExpressionWrapper(
                F('total_price') - (F('item__unit_cost') * F('quantity')),
                output_field=DecimalField()
            )
        )
    )['profit'] or 0

    # STOCK ALERTS
    low_stock_items = StockItem.objects.filter(quantity__lte=5, quantity__gt=0)
    out_of_stock_items = StockItem.objects.filter(quantity=0)

    # SUPPLIER DEBT
    supplier_debt = Supplier.objects.aggregate(
        total=Sum('credit')
    )['total'] or 0

    # SCHEME DATA
    scheme_members = SalaryEarner.objects.count()
    scheme_savings = Deposit.objects.aggregate(
        total=Sum('amount')
    )['total'] or 0

    context = {
        'todays_revenue': todays_revenue,
        'total_profit': total_profit,

        'low_stock_count': low_stock_items.count(),
        'out_of_stock_count': out_of_stock_items.count(),

        'supplier_debt': supplier_debt,

        'stock_lines': StockItem.objects.count(),
        'scheme_members': scheme_members,
        'scheme_savings': scheme_savings,

        'all_time_sales': Sale.objects.count(),

        'recent_sales': Sale.objects.select_related('item')
                                   .order_by('-date_sold')[:5],

        'today': today
    }

    return render(request, 'admin_dashboard.html', context)

@login_required
def stock_dashboard(request):
    today = timezone.now().date()

    items = StockItem.objects.all()

    low_stock_items = items.filter(quantity__lte=5, quantity__gt=0)
    out_of_stock_items = items.filter(quantity=0)

    suppliers = Supplier.objects.all()  # ✅ ADD THIS

    context = {
        'total_lines': items.count(),
        'in_stock': items.filter(quantity__gt=5).count(),
        'low_stock_count': low_stock_items.count(),
        'out_of_stock_count': out_of_stock_items.count(),

        'stock_value': items.aggregate(total=Sum('unit_cost'))['total'] or 0,
        'total_units': items.aggregate(total=Sum('quantity'))['total'] or 0,

        'low_stock_items': low_stock_items,

        # ✅ ADD SUPPLIERS
        'suppliers': suppliers,

        'today': today
    }

    return render(request, 'stock_dashboard.html', context)


@login_required
def sales_dashboard(request):
    today = timezone.now().date()
    my_sales_today = Sale.objects.filter(user=request.user, date_sold__date=today)
    store_sales_today = Sale.objects.filter(date_sold__date=today)

    context = {
        'my_sales_today': my_sales_today.count(),
        'my_revenue_today': my_sales_today.aggregate(total=Sum('total_price'))['total'] or 0,
        'store_total_today': store_sales_today.aggregate(total=Sum('total_price'))['total'] or 0,
        'my_all_time_sales': Sale.objects.filter(user=request.user).count(),
        'my_sales': my_sales_today,
        'recent_sales': Sale.objects.filter(user=request.user).order_by('-date_sold')[:5],
        'today': today,
    }
    return render(request, 'sales_dashboard.html', context)


@login_required
def cashier_dashboard(request):
    today = timezone.now().date()
    all_sales = Sale.objects.all()

    total_revenue = all_sales.aggregate(total=Sum('total_price'))['total'] or 0
    total_profit = sum(
        sale.total_price - (sale.item.unit_cost * sale.quantity)
        for sale in all_sales
    )
    supplier_credit = Supplier.objects.aggregate(total=Sum('credit'))['total'] or 0

    context = {
        'total_revenue': total_revenue,
        'total_profit': total_profit,
        'supplier_credit': supplier_credit,
        'sales_log': all_sales.order_by('-date_sold')[:10],
        'scheme_summary': Deposit.objects.values('salary_earner__national_id_name').annotate(total=Sum('amount')),
        'today': today
    }
    return render(request, 'cashier_dashboard.html', context)
# 3. stock management (add, edit, delete)
@login_required(login_url='/')
def stock_list(request):
    items = StockItem.objects.all()
    categories = Category.objects.all()
    suppliers = Supplier.objects.all()  #  Added this line to fetch suppliers
    
    return render(request, 'stock.html', {
        'items': items,
        'categories': categories,
        'suppliers': suppliers          # Added this key to share it with your HTML template
    })


@login_required(login_url='/')
def add_stock(request):
    if request.method == "POST":
        try:
            category_obj = get_object_or_404(Category, id=request.POST.get('category'))
            supplier_obj = get_object_or_404(Supplier, id=request.POST.get('supplier')) # Added supplier lookup
            
            unit_cost = float(request.POST['unit_cost'])
            selling_price = float(request.POST['selling_price'])
            
            if selling_price <= unit_cost: # Mandatory validation rule #6 guard
                messages.error(request, "Validation Error: Selling price must be greater than unit cost.")
                return redirect('stock_list')
            
            StockItem.objects.create(
                name=request.POST['name'],
                category=category_obj,
                supplier=supplier_obj, # Bound mandatory model foreign key
                unit=request.POST['unit'],
                quantity=request.POST['quantity'],
                unit_cost=unit_cost,
                selling_price=selling_price,
                specifications=request.POST.get('specifications', '')
            )
            messages.success(request, f"Successfully added {request.POST['name']} to stock.")
        except Exception as e:
            messages.error(request, f"Error adding stock: {e}")
            
    return redirect('stock_list')


@login_required(login_url='/')
def edit_stock(request, item_id):
    item = get_object_or_404(StockItem, id=item_id)
    categories = Category.objects.all()
    suppliers = Supplier.objects.all()
    
    if request.method == "POST":
        category_id = request.POST.get('category')
        supplier_id = request.POST.get('supplier') # Added supplier extraction
        
        # Enforce validation safeguards
        if float(request.POST['selling_price']) <= float(request.POST['unit_cost']):
            messages.error(request, "Validation Error: Selling price must be greater than unit cost.")
            return render(request, 'edit_stock.html', {'item': item, 'categories': categories, 'suppliers': suppliers})

        item.category = get_object_or_404(Category, id=category_id)
        item.supplier = get_object_or_404(Supplier, id=supplier_id) # Bound updated model foreign key
        
        item.name = request.POST['name']
        item.unit = request.POST['unit']
        item.quantity = request.POST['quantity']
        item.unit_cost = request.POST['unit_cost']
        item.selling_price = request.POST['selling_price']
        item.specifications = request.POST.get('specifications', '')
        item.save()
        
        messages.success(request, f"Updated {item.name} successfully!")
        return redirect('stock_list')
        
    return render(request, 'edit_stock.html', {'item': item, 'categories': categories, 'suppliers': suppliers})


@login_required(login_url='/')
def delete_stock(request, item_id):
    item = get_object_or_404(StockItem, id=item_id)
    name = item.name
    item.delete()
    messages.warning(request, f"{name} has been removed from inventory.")
    return redirect('stock_list')

# 4. recording sales (walk-in and deliveries)

@login_required(login_url='/')
def record_sale(request):
    items = StockItem.objects.all()
    active_tab = request.GET.get('type', 'WALK_IN')
    sale_id = request.GET.get('sale_id')

    if request.method == "POST":
        item_id = request.POST.get('item')
        qty_raw = request.POST.get('quantity')
        sale_type = request.POST.get('sale_type')
        delivery = request.POST.get('delivery') == 'yes'

        # Validate required fields
        if not item_id or not qty_raw or not sale_type:
            messages.error(request, "Please fill in all required fields.")
            return redirect(f'/record_sale/?type={active_tab}')

        # Validate quantity
        try:
            qty = int(qty_raw)
            if qty <= 0:
                messages.error(request, "Quantity must be greater than 0.")
                return redirect(f'/record_sale/?type={active_tab}')
        except ValueError:
            messages.error(request, "Quantity must be a valid number.")
            return redirect(f'/record_sale/?type={active_tab}')

        product = get_object_or_404(StockItem, id=item_id)
        subtotal = product.selling_price * qty

        # Handle distance safely
        distance_raw = request.POST.get('distance')
        try:
            distance = float(distance_raw) if distance_raw else 0
        except (ValueError, TypeError):
            distance = 0

        # Delivery fee calculation rules
        if delivery:
            fee = 0 if (distance <= 10 and subtotal >= 500000) else 30000
        else:
            fee = 0

        total = subtotal + fee

        # 🛠️ EXTRA MODULE SCHEME AUDIT: Protects salary-earner ledger balances
        member_nin = request.POST.get('member_nin', '').strip().upper()
        if sale_type == 'SCHEME':
            if not member_nin:
                messages.error(request, "Validation Error: Member NIN is strictly required for Credit Scheme pickups.")
                return redirect(f'/record_sale/?type={active_tab}')
            try:
                earner = SalaryEarner.objects.get(nin_number=member_nin)
                if earner.credit_balance < total:
                    messages.error(request, f"Credit Deficit: Insufficient scheme balance allocation. Available: UGX {earner.credit_balance:,.0f}")
                    return redirect(f'/record_sale/?type={active_tab}')
                
                # Commit ledger deduction on verification
                earner.credit_balance -= total
                earner.save()
            except SalaryEarner.DoesNotExist:
                messages.error(request, "Authorization Failure: No registered salary earner matches this NIN format layout.")
                return redirect(f'/record_sale/?type={active_tab}')

        # Check stock availability
        if product.quantity >= qty:
            product.quantity -= qty
            product.save()

            # 🛠️ FIXED: Added missing user tracking and distance parameter logging inputs
            sale = Sale.objects.create(
                sale_type=sale_type,
                item=product,
                quantity=qty,
                total_price=total,
                delivery_fee=fee,
                distance=distance, # Log data metric properly
                customer_name=request.POST.get('customer', 'Walk-in'),
                member_nin=member_nin if sale_type == 'SCHEME' else '',
                user=request.user # Ties back user instance cleanly to clear dashboard crashes!
            )

            messages.success(request, "Transaction Completed Successfully!")
            return redirect(f'/record_sale/?type={active_tab}&sale_id={sale.id}')

        else:
            messages.error(request, "Insufficient Stock Level Volumes Available!")
            return redirect(f'/record_sale/?type={active_tab}')

    last_sale = get_object_or_404(Sale, id=sale_id) if sale_id else None

    return render(request, 'record_sale.html', {
        'items': items,
        'active_tab': active_tab,
        'last_sale': last_sale
    })

# 5. credit scheme management views
@login_required(login_url='/')
def credit_scheme(request):
    if request.method == "POST":
        # ACTION 1: REGISTER MEMBER WITH TARGET AT ENROLLMENT
        if 'register_member' in request.POST:
            nin = request.POST.get('nin', '').strip().upper()
            if SalaryEarner.objects.filter(nin_number=nin).exists():
                messages.error(request, f"Validation Error: NIN {nin} is already registered.")
            else:
                try:
                    product_id = request.POST.get('target_product')
                    product_obj = get_object_or_404(Item, id=product_id)
                    quantity = int(request.POST.get('target_quantity', 1))
                    
                    # Auto-calculate and store the static target cost baseline threshold
                    calculated_amount = product_obj.price * quantity

                    SalaryEarner.objects.create(
                        national_id_name=request.POST.get('name'),
                        nin_number=nin,
                        phone_number=request.POST.get('phone'),
                        workplace=request.POST.get('workplace'),
                        target_product=product_obj,
                        target_quantity=quantity,
                        target_amount=calculated_amount
                    )
                    messages.success(request, "New salary earner account initialized successfully!")
                except Exception as e:
                    messages.error(request, f"Registration failed: {e}")
            return redirect('/deposits/#register')
            
        # ACTION 2: RECORD SIMPLE CASH SAVINGS DEPOSIT ONLY
        elif 'record_deposit' in request.POST:
            try:
                earner_id = request.POST.get('salary_earner')
                amount_raw = request.POST.get('amount')

                earner = get_object_or_404(SalaryEarner, id=earner_id)

                # Commit simple deposit transaction history voucher log
                Deposit.objects.create(
                    salary_earner=earner,
                    amount=decimal.Decimal(amount_raw)
                )
                
                # Update member persistence profile wallet balance immediately
                earner.credit_balance += decimal.Decimal(amount_raw)
                earner.save()

                messages.success(request, f"Ledger updated! Deposited UGX {float(amount_raw):,.0f} successfully.")
            except Exception as e:
                messages.error(request, f"Transaction failed to record: {e}")
            return redirect('/deposits/#deposit')
            
        return redirect('credit_scheme')

    # Data Retrieval Blocks (Queries specific Item instead of general StockItem)
    earners = SalaryEarner.objects.select_related('target_product').all()
    scheme_items = Item.objects.all() 

    return render(request, 'deposits.html', {
        'earners': earners,
        'scheme_items': scheme_items
    })


    
# supplier page view
@login_required(login_url='/')
def suppliers(request):
    if request.method == "POST":
        try:
            name = request.POST.get("name", "").strip()
            contact = request.POST.get("contact", "").strip()
            address = request.POST.get("address", "").strip()
            credit_raw = request.POST.get("credit") or "0"

            Supplier.objects.create(
                name=name,
                contact=contact,
                address=address,
                credit=decimal.Decimal(credit_raw) # Explicit cast for math safety
            )
            messages.success(request, f"Supplier entry '{name}' registered successfully!")
        except Exception as e:
            messages.error(request, f"Registry Error: Failed to add supplier vendor: {e}")
        return redirect("suppliers")  

    # GET Request: Renders the humanized, button-driven data grid table
    suppliers_list = Supplier.objects.all().order_by('name')
    return render(request, "suppliers.html", {"suppliers": suppliers_list})


# 2. UPDATE EXISTING VENDOR METRICS
@login_required(login_url='/')
def edit_supplier(request, supplier_id):
    supplier_obj = get_object_or_404(Supplier, id=supplier_id)
    
    if request.method == "POST":
        try:
            supplier_obj.name = request.POST.get('name', '').strip()
            supplier_obj.contact = request.POST.get('contact', '').strip()
            supplier_obj.address = request.POST.get('address', '').strip()
            supplier_obj.credit = decimal.Decimal(request.POST.get('credit') or '0')
            supplier_obj.save()
            
            messages.success(request, f"Supplier profile for '{supplier_obj.name}' updated successfully.")
        except Exception as e:
            messages.error(request, f"Database Write Error: Failed to save changes: {e}")
            
    return redirect('suppliers')


# 3. DELETE VENDOR REGISTRY RECORD
@login_required(login_url='/')
def delete_supplier(request, supplier_id):
    supplier_obj = get_object_or_404(Supplier, id=supplier_id)
    name = supplier_obj.name
    
    # Financial Safeguard Rule: Prevents dropping vendors if open arrears persist
    if supplier_obj.credit > 0:
        messages.error(request, f"Accounting Security Lock: Cannot delete '{name}' because an outstanding debt of UGX {supplier_obj.credit:,.0f} must be cleared first.")
        return redirect('suppliers')
        
    supplier_obj.delete()
    messages.warning(request, f"Supplier registry for '{name}' has been wiped from indices.")
    return redirect('suppliers')

# customers under the credit scheme
@login_required
def scheme_enrollees(request):
    customers = SalaryEarner.objects.all()
    products = Item.objects.all()

    # Handle registration
    if request.method == "POST" and "register_customer" in request.POST:
        name = request.POST.get("name")
        nin = request.POST.get("nin")
        phone = request.POST.get("phone")
        workplace = request.POST.get("workplace")
        product_id = request.POST.get("product")
        quantity = int(request.POST.get("quantity"))

        product_obj = get_object_or_404(Item, id=product_id)
        target_amount = product_obj.price * quantity

        SalaryEarner.objects.create(
            national_id_name=name,
            nin_number=nin,
            phone_number=phone,
            workplace=workplace,
            target_product=product_obj,
            target_quantity=quantity,
            target_amount=target_amount
        )
        messages.success(request, "Customer registered successfully.")
        return redirect("scheme_enrollees")

    return render(request, "scheme_enrollees.html", {"customers": customers, "products": products})


@login_required
def edit_enrollee(request, pk):
    customer = get_object_or_404(SalaryEarner, pk=pk)
    products = Item.objects.all()

    if request.method == "POST":
        customer.national_id_name = request.POST.get("name")
        customer.nin_number = request.POST.get("nin")
        customer.phone_number = request.POST.get("phone")
        customer.workplace = request.POST.get("workplace")
        product_id = request.POST.get("product")
        customer.target_product = get_object_or_404(Item, id=product_id)
        customer.target_quantity = int(request.POST.get("quantity"))
        customer.target_amount = customer.target_product.price * customer.target_quantity
        customer.save()
        messages.success(request, "Customer updated successfully.")
        return redirect("scheme_enrollees")

    return render(request, "edit_enrollee.html", {"customer": customer, "products": products})


@login_required
def delete_enrollee(request, pk):
    customer = get_object_or_404(SalaryEarner, pk=pk)
    customer.delete()
    messages.warning(request, "Customer deleted successfully.")
    return redirect("scheme_enrollees")

def sales_today(request):
    today = now().date()
    sales = Sale.objects.filter(date_sold__date=today).order_by('-date_sold')

    return render(request, 'sales_today.html', {
        'sales': sales
    })


def sale_detail(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id)

    return render(request, 'sale_detail.html', {
        'sale': sale
    })

@login_required(login_url='/')
def reports(request):
    today = timezone.now().date()

    # ---------------- 1. SALES & PROFIT CALCULATIONS ----------------
    today_sales = Sale.objects.filter(date_sold__date=today)
    today_revenue = today_sales.aggregate(total=Sum('total_price'))['total'] or 0

    all_sales = Sale.objects.all()
    total_revenue = all_sales.aggregate(total=Sum('total_price'))['total'] or 0

    # 💡 CODE QUALITY OPTIMIZATION: Database-level calculation loop bypass (Revenue - (Cost * Qty))
    total_profit = Sale.objects.aggregate(
        profit=Sum(
            ExpressionWrapper(
                F('total_price') - (F('item__unit_cost') * F('quantity')),
                output_field=DecimalField(max_digits=12, decimal_places=0)
            )
        )
    )['profit'] or 0

    # ---------------- 2. REAL ACCURATE STOCK METRICS ----------------
    low_stock = StockItem.objects.filter(quantity__lte=5, quantity__gt=0)
    out_stock = StockItem.objects.filter(quantity=0)

    # 💡 FORMULA REPAIR: Multiplies unit prices against actual stored stock volumes
    stock_value = StockItem.objects.aggregate(
        total=Sum(
            ExpressionWrapper(
                F('selling_price') * F('quantity'),
                output_field=DecimalField(max_digits=12, decimal_places=0)
            )
        )
    )['total'] or 0

    total_items = StockItem.objects.count()

    # ---------------- 3. EXTRA MODULES SUMMARY DATA ----------------
    supplier_debt = Supplier.objects.aggregate(total=Sum('credit'))['total'] or 0
    scheme_savings = Deposit.objects.aggregate(total=Sum('amount'))['total'] or 0
    scheme_members = SalaryEarner.objects.count()

    return render(request, "reports.html", {
        "today": today,
        "today_revenue": today_revenue,
        "total_revenue": total_revenue,
        "total_profit": total_profit,
        "low_stock_count": low_stock.count(),
        "out_of_stock_count": out_stock.count(),
        "stock_value": stock_value,
        "total_items": total_items,
        "supplier_debt": supplier_debt,
        "scheme_savings": scheme_savings,
        "scheme_members": scheme_members,
    })

@login_required(login_url='/')
def user_management(request):
    """ Renders the active personnel ledger list and handling tab frames """
    # AUTHENTICATION GUARD: Restrict access strictly to ADMIN role profiles
    if getattr(request.user, 'role', '') != 'ADMIN':
        raise PermissionDenied  # Redirects to HTTP 403 Forbidden page

    users = CustomUser.objects.all().order_by('-is_active', 'username')
    return render(request, "users.html", {
        "users": users
    })


@login_required(login_url='/')
def toggle_user(request, user_id):
    """ Safely activates or deactivates an employee's system node credentials """
    # AUTHENTICATION GUARD: Protect backend administrative action endpoints
    if getattr(request.user, 'role', '') != 'ADMIN':
        raise PermissionDenied

    # SAFETY GUARD: Prevent logged-in admin session lockout crashes
    if request.user.id == int(user_id):
        messages.error(request, "Security Guard: You cannot deactivate your own active administrator session account.")
        return redirect('user_management')

    user = get_object_or_404(CustomUser, id=user_id)
    user.is_active = not user.is_active
    user.save()

    status_str = "re-authorized" if user.is_active else "deactivated"
    messages.warning(request, f"Workspace access profile for user @{user.username} has been {status_str}.")
    return redirect('user_management')


@login_required(login_url='/')
def add_user(request):
    """ Securely initializes a new staff profile into database tables """
    # AUTHENTICATION GUARD: Prevent malicious data submissions
    if getattr(request.user, 'role', '') != 'ADMIN':
        raise PermissionDenied

    if request.method == "POST":
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password')
        role = request.POST.get('role')
        phone = request.POST.get('phone', '').strip()

        # DUPLICATE DATA SAFEGUARD: Validate username uniqueness criteria
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, f"Creation Failure: Username @{username} is already taken inside the system ledger.")
            return redirect('/users/#register_user')

        try:
            # Django Cryptographic Security Pattern: Automatically encrypts the raw password [1]
            CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                role=role,
                phone=phone
            )
            messages.success(request, f"Staff credential portfolio for @{username} has been initialized successfully!")
        except Exception as e:
            messages.error(request, f"System Registry Error: Failed to generate account: {e}")

    return redirect('user_management')

def landing(request):
    return render(request, "index.html")  