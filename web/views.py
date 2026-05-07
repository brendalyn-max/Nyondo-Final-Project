from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Sum, Count
from django.contrib.auth.decorators import login_required
from .models import *

# ==========================================
# 1. AUTHENTICATION VIEWS
# ==========================================

def index(request):
    """ Login Page View """
    if request.user.is_authenticated:
        return redirect("admin_dashboard")
        
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("admin_dashboard")
        else:
            messages.error(request, "Invalid username or password")
            return redirect("index")
    return render(request, "index.html")


def logout_view(request):
    """ Logout functionality """
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("index")


# ==========================================
# 2. DASHBOARD / HOME VIEW
# ==========================================

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
    # Revenue and profit
    today = timezone.now().date()
    todays_sales = Sale.objects.filter(date_sold__date=today)
    todays_revenue = todays_sales.aggregate(total=Sum('total_price'))['total'] or 0
    # total_profit = Sale.objects.aggregate(profit=Sum('profit'))['profit'] or 0
    all_sales = Sale.objects.all()
    total_profit = sum(
        sale.total_price - (sale.item.unit_cost * sale.quantity)
        for sale in all_sales
    )

    # Stock alerts
    low_stock_items = StockItem.objects.filter(quantity__lte=5, quantity__gt=0)
    out_of_stock_items = StockItem.objects.filter(quantity=0)

    # Supplier debt
    supplier_debt = Supplier.objects.aggregate(total=Sum('credit'))['total'] or 0

    # Scheme
    scheme_members = SalaryEarner.objects.count()
    scheme_savings = Deposit.objects.aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'todays_revenue': todays_revenue,
        'total_profit': total_profit,
        'low_stock_count': low_stock_items.count(),
        'supplier_debt': supplier_debt,
        'stock_lines': StockItem.objects.count(),
        'scheme_members': scheme_members,
        'scheme_savings': scheme_savings,
        'all_time_sales': Sale.objects.count(),
        'recent_sales': Sale.objects.order_by('-date_sold')[:5],
        'today': today
    }
    return render(request, 'admin_dashboard.html', context)


@login_required
def stock_dashboard(request):
    today = timezone.now().date()
    items = StockItem.objects.all()
    low_stock_items = items.filter(quantity__lte=5, quantity__gt=0)
    out_of_stock_items = items.filter(quantity=0)

    context = {
        'total_lines': items.count(),
        'in_stock': items.filter(quantity__gt=5).count(),
        'low_stock_count': low_stock_items.count(),
        'out_of_stock_count': out_of_stock_items.count(),
        'stock_value': items.aggregate(total=Sum('unit_cost'))['total'] or 0,
        'total_units': items.aggregate(total=Sum('quantity'))['total'] or 0,
        'low_stock_items': low_stock_items,
        'today': today
    }
    return render(request, 'stock_dashboard.html', context)


@login_required
def sales_dashboard(request):
    today = timezone.now().date()

    # Sales recorded by the logged-in user today
    my_sales_today = Sale.objects.filter(user=request.user, date_sold__date=today)

    # All store sales today
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
        # ✅ FIX: use salary_earner instead of earner
        'scheme_summary': Deposit.objects.values('salary_earner__national_id_name').annotate(total=Sum('amount')),
        'today': today
    }
    return render(request, 'cashier_dashboard.html', context)


# ==========================================
# 3. STOCK / INVENTORY VIEWS
# ==========================================

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


# ==========================================
# 4. SALES VIEW
# ==========================================

@login_required(login_url='/')
def record_sale(request):
    items = StockItem.objects.all()
    active_tab = request.GET.get('type', 'WALK_IN')
    sale_id = request.GET.get('sale_id')

    if request.method == "POST":
        item_id = request.POST.get('item')
        qty = int(request.POST.get('quantity'))
        sale_type = request.POST.get('sale_type')
        delivery = request.POST.get('delivery') == 'yes'

        product = get_object_or_404(StockItem, id=item_id)
        subtotal = product.selling_price * qty

        distance_raw = request.POST.get('distance')
        try:
            distance = float(distance_raw) if distance_raw else 0
        except (ValueError, TypeError):
            distance = 0

        if delivery:
            fee = 0 if (distance <= 10 and subtotal >= 500000) else 30000
        else:
            fee = 0

        total = subtotal + fee

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
    return render(request, 'record_sale.html', {'items': items, 'active_tab': active_tab, 'last_sale': last_sale})


# ==========================================
# 5. CREDIT SCHEME (DEPOSITS)
# ==========================================

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
            
            # Get quantity from the most recent deposit for this item
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
