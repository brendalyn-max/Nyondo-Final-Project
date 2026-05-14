from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
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

    return render(request, "index.html")

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
    return render(request, 'stock.html', {
        'items': items,
        'categories': categories
    })


@login_required(login_url='/')
def add_stock(request):
    if request.method == "POST":
        try:
            category_id = request.POST.get('category')
            category_obj = get_object_or_404(Category, id=category_id)
            
            StockItem.objects.create(
                name=request.POST['name'],
                category=category_obj,
                unit=request.POST['unit'],
                quantity=request.POST['quantity'],
                unit_cost=request.POST['unit_cost'],
                selling_price=request.POST['selling_price'],
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
    
    if request.method == "POST":
        category_id = request.POST.get('category')
        item.category = get_object_or_404(Category, id=category_id)
        
        item.name = request.POST['name']
        item.unit = request.POST['unit']
        item.quantity = request.POST['quantity']
        item.unit_cost = request.POST['unit_cost']
        item.selling_price = request.POST['selling_price']
        item.specifications = request.POST.get('specifications', '')
        item.save()
        
        messages.success(request, f"Updated {item.name} successfully!")
        return redirect('stock_list')
        
    return render(request, 'edit_stock.html', {'item': item, 'categories': categories})


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

        # Delivery fee calculation
        if delivery:
            fee = 0 if (distance <= 10 and subtotal >= 500000) else 30000
        else:
            fee = 0

        total = subtotal + fee

        # Check stock availability
        if product.quantity >= qty:
            product.quantity -= qty
            product.save()

            sale = Sale.objects.create(
                sale_type=sale_type,
                item=product,
                quantity=qty,
                total_price=total,
                delivery_fee=fee,
                customer_name=request.POST.get('customer', 'Walk-in'),
                member_nin=request.POST.get('member_nin', '')
            )

            messages.success(request, "Transaction Successful!")
            return redirect(f'/record_sale/?type={active_tab}&sale_id={sale.id}')

        else:
            messages.error(request, "Insufficient Stock!")
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
        if 'register_member' in request.POST:
            nin = request.POST.get('nin')
            if SalaryEarner.objects.filter(nin_number=nin).exists():
                messages.error(request, f"NIN {nin} is already registered.")
            else:
                SalaryEarner.objects.create(
                    national_id_name=request.POST.get('name'),
                    nin_number=nin,
                    phone_number=request.POST.get('phone'),
                    workplace=request.POST.get('workplace')
                )
                messages.success(request, "Member registered successfully!")
            
        elif 'record_deposit' in request.POST:
            earner = get_object_or_404(SalaryEarner, id=request.POST.get('earner_id'))
            product = get_object_or_404(StockItem, id=request.POST.get('product_id'))
            qty = int(request.POST.get('quantity', 1))

            Deposit.objects.create(
                salary_earner=earner,
                product=product,
                quantity=qty,
                amount=request.POST.get('amount')
            )
            messages.success(request, "Deposit recorded!")
            
        return redirect('credit_scheme')

    # Data Preparation
    earners = SalaryEarner.objects.all()
    stock_items = StockItem.objects.all()
    progress_data = []

    for earner in earners:
        products_saved = Deposit.objects.filter(salary_earner=earner).values_list('product', flat=True).distinct()
        for p_id in products_saved:
            if not p_id: continue
            
            product = StockItem.objects.get(id=p_id)
            total_saved = Deposit.objects.filter(salary_earner=earner, product_id=p_id).aggregate(Sum('amount'))['amount__sum'] or 0
            latest_dep = Deposit.objects.filter(salary_earner=earner, product_id=p_id).latest('id')
            qty_intended = latest_dep.quantity

            target_price = product.selling_price * qty_intended
            percent = (total_saved / target_price * 100) if target_price > 0 else 0
            
            progress_data.append({
                'earner': earner,
                'product': product,
                'qty': qty_intended,
                'target': target_price,
                'total': total_saved,
                'progress': min(round(percent, 1), 100)
            })

    return render(request, 'deposits.html', {
        'earners': earners,
        'stock_items': stock_items,
        'progress_data': progress_data
    })
# supplier page view

def suppliers(request):
    if request.method == "POST":
        # Handle supplier registration form
        name = request.POST.get("name")
        contact = request.POST.get("contact")
        address = request.POST.get("address")
        credit = request.POST.get("credit")

        Supplier.objects.create(
            name=name,
            contact=contact,
            address=address,
            credit=credit
        )
        return redirect("suppliers")  # reload page after saving

    suppliers = Supplier.objects.all()
    return render(request, "suppliers.html", {"suppliers": suppliers})

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

@login_required
def reports(request):
    today = timezone.now().date()

    # ---------------- SALES ----------------
    today_sales = Sale.objects.filter(date_sold__date=today)
    today_revenue = today_sales.aggregate(total=Sum('total_price'))['total'] or 0

    all_sales = Sale.objects.all()
    total_revenue = all_sales.aggregate(total=Sum('total_price'))['total'] or 0

    total_profit = sum(
        s.total_price - (s.item.unit_cost * s.quantity)
        for s in all_sales
    )

    # ---------------- STOCK ----------------
    low_stock = StockItem.objects.filter(quantity__lte=5, quantity__gt=0)
    out_stock = StockItem.objects.filter(quantity=0)

    stock_value = StockItem.objects.aggregate(
        total=Sum('selling_price')
    )['total'] or 0

    total_items = StockItem.objects.count()

    # ---------------- SUPPLIERS ----------------
    supplier_debt = Supplier.objects.aggregate(
        total=Sum('credit')
    )['total'] or 0

    # ---------------- SCHEME ----------------
    scheme_savings = Deposit.objects.aggregate(
        total=Sum('amount')
    )['total'] or 0

    scheme_members = SalaryEarner.objects.count()

    return render(request, "reports.html", {
        "today": today,

        # sales
        "today_revenue": today_revenue,
        "total_revenue": total_revenue,
        "total_profit": total_profit,

        # stock
        "low_stock_count": low_stock.count(),
        "out_of_stock_count": out_stock.count(),
        "stock_value": stock_value,
        "total_items": total_items,

        # suppliers
        "supplier_debt": supplier_debt,

        # scheme
        "scheme_savings": scheme_savings,
        "scheme_members": scheme_members,
    })

@login_required
def user_management(request):
    users = CustomUser.objects.all()

    return render(request, "users.html", {
        "users": users
    })

@login_required
def toggle_user(request, user_id):
    user = CustomUser.objects.get(id=user_id)
    user.is_active = not user.is_active
    user.save()
    return redirect('user_management')