from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from .models import *

# ==========================================
# 1. AUTHENTICATION VIEWS
# ==========================================

def index(request):
    """ Login Page View """
    if request.user.is_authenticated:
        return redirect("home")
        
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("home")
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
