from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import uuid
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Создаем папку для загрузок, если её нет
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Файлы для хранения данных
PRODUCTS_FILE = 'products_data.json'
USERS_FILE = 'users_data.json'
CARTS_FILE = 'carts_data.json'
ORDERS_FILE = 'orders_data.json'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_products():
    """Загружает данные о товарах из JSON файла"""
    if os.path.exists(PRODUCTS_FILE):
        with open(PRODUCTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "headphones": {
            "emoji": "🎧",
            "name": "НАУШНИКИ",
            "name_en": "HEADPHONES",
            "items": [
                {"name": "AirPods 4", "price": "3.290", "image": ""},
                {"name": "AirPods Pro 2", "price": "3.490", "image": ""},
                {"name": "AirPods Max", "price": "11.490", "image": ""},
                {"name": "Marshall Major V", "price": "5.490", "image": ""}
            ]
        },
        "watches": {
            "emoji": "⌚",
            "name": "ЧАСЫ",
            "name_en": "WATCHES",
            "items": [
                {"name": "Apple Watch Series 10 I Black Titanium", "price": "3.990", "image": ""},
                {"name": "Apple Watch Series 10 I Natural Titanium", "price": "3.990", "image": ""},
                {"name": "Apple Watch Ultra 2", "price": "3.990", "image": ""}
            ]
        },
        "charging": {
            "emoji": "⚡",
            "name": "ЗАРЯДНЫЕ УСТРОЙСТВА",
            "name_en": "CHARGING DEVICES",
            "items": [
                {"name": "Комплект зарядки Apple 25W I USB-C, Lightning", "price": "790", "image": ""}
            ]
        },
        "haircare": {
            "emoji": "💇‍♀️",
            "name": "УХОД ЗА ВОЛОСАМИ",
            "name_en": "HAIR CARE",
            "items": [
                {"name": "Dyson Supersonic HD-08 1:1", "price": "3.490", "image": ""}
            ]
        },
        "speakers": {
            "emoji": "🎵",
            "name": "КОЛОНКИ",
            "name_en": "SPEAKERS",
            "items": [
                {"name": "JBL Flip 6", "price": "2.190", "image": ""},
                {"name": "JBL Clip 5", "price": "2.190", "image": ""}
            ]
        }
    }

def save_products(products):
    """Сохраняет данные о товарах в JSON файл"""
    with open(PRODUCTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

def load_users():
    """Загружает данные о пользователях"""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    """Сохраняет данные о пользователях"""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def load_carts():
    """Загружает данные о корзинах"""
    if os.path.exists(CARTS_FILE):
        with open(CARTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_carts(carts):
    """Сохраняет данные о корзинах"""
    with open(CARTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(carts, f, ensure_ascii=False, indent=2)

def load_orders():
    """Загружает данные о заказах"""
    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_orders(orders):
    """Сохраняет данные о заказах"""
    with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)

def generate_order_number():
    """Генерирует уникальный номер заказа"""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_part = str(uuid.uuid4().hex[:6]).upper()
    return f"ORD-{timestamp}-{random_part}"

def get_cart_id():
    """Получает ID корзины: user_id для авторизованных, session_id для неавторизованных"""
    if 'user_id' in session:
        return session['user_id']
    else:
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        return f"session_{session['session_id']}"

def get_user_cart(cart_id=None):
    """Получает корзину пользователя или сессии"""
    if cart_id is None:
        cart_id = get_cart_id()
    carts = load_carts()
    if cart_id not in carts:
        carts[cart_id] = []
        save_carts(carts)
    return carts[cart_id]

def save_user_cart(cart, cart_id=None):
    """Сохраняет корзину пользователя или сессии"""
    if cart_id is None:
        cart_id = get_cart_id()
    carts = load_carts()
    carts[cart_id] = cart
    save_carts(carts)

def login_required(f):
    """Декоратор для проверки авторизации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Для оформления заказа необходимо войти в систему или зарегистрироваться', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Декоратор для проверки прав администратора"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Недостаточно прав для доступа к админ-панели', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

PRODUCTS = load_products()


@app.route("/")
def home():
    # Загружаем актуальные данные
    products = load_products()
    # Преобразуем словарь в список для удобной работы в шаблоне
    products_list = []
    for key, value in products.items():
        category = {
            "key": key,
            "emoji": value["emoji"],
            "name": value["name"],
            "name_en": value["name_en"],
            "products": value["items"]
        }
        products_list.append(category)
    
    # Получаем количество товаров в корзине
    cart_count = 0
    cart = get_user_cart()
    cart_count = sum(item['quantity'] for item in cart)
    
    return render_template("index.html", products=products_list, cart_count=cart_count, user=session.get('username'), is_admin=session.get('is_admin', False))


@app.route("/product/<category_key>/<int:product_index>")
def get_product(category_key, product_index):
    """Получение информации о товаре"""
    products = load_products()
    
    if category_key not in products:
        return jsonify({'error': 'Категория не найдена'}), 404
    
    if product_index >= len(products[category_key]['items']):
        return jsonify({'error': 'Товар не найден'}), 404
    
    product = products[category_key]['items'][product_index]
    category = products[category_key]
    
    return jsonify({
        'name': product['name'],
        'price': product['price'],
        'image': product.get('image', ''),
        'description': product.get('description', ''),
        'specs': product.get('specs', []),
        'category_name': category['name'],
        'category_name_en': category['name_en'],
        'category_emoji': category['emoji'],
        'category_key': category_key,
        'product_index': product_index
    })


@app.route("/admin")
@login_required
@admin_required
def admin():
    """Админ-панель для управления товарами и загрузки изображений"""
    products = load_products()
    products_list = []
    for key, value in products.items():
        category = {
            "key": key,
            "emoji": value["emoji"],
            "name": value["name"],
            "name_en": value["name_en"],
            "products": value["items"]
        }
        products_list.append(category)
    return render_template("admin.html", products=products_list)


@app.route("/add_product", methods=["POST"])
@login_required
@admin_required
def add_product():
    """Добавляет новый товар в выбранную категорию"""
    category_key = request.form.get('category')
    product_name = request.form.get('name', '').strip()
    product_price = request.form.get('price', '').strip()

    if not category_key:
        flash('Выберите категорию для нового товара', 'error')
        return redirect(url_for('admin'))

    products = load_products()

    if category_key not in products:
        flash('Выбранная категория не найдена', 'error')
        return redirect(url_for('admin'))

    if not product_name or not product_price:
        flash('Введите название и цену товара', 'error')
        return redirect(url_for('admin'))

    # Преобразуем цену в формат с разделением тысяч точкой (например, 3.490)
    digits_only = ''.join(ch for ch in product_price if ch.isdigit())
    if not digits_only:
        flash('Неверный формат цены', 'error')
        return redirect(url_for('admin'))

    if any(item['name'].strip().lower() == product_name.lower() for item in products[category_key]['items']):
        flash('Товар с таким названием уже существует в этой категории', 'error')
        return redirect(url_for('admin'))

    if len(digits_only) > 3:
        formatted_price = f"{digits_only[:-3]}.{digits_only[-3:]}"
    else:
        formatted_price = digits_only

    new_product = {
        "name": product_name,
        "price": formatted_price,
        "image": "",
        "description": "",
        "specs": []
    }
    products[category_key]['items'].append(new_product)
    save_products(products)
    flash('Товар успешно добавлен', 'success')
    return redirect(url_for('admin'))


@app.route("/upload", methods=["POST"])
@login_required
@admin_required
def upload_file():
    """Загружает изображение для товара"""
    if 'file' not in request.files:
        flash('Файл не выбран', 'error')
        return redirect(url_for('admin'))
    
    file = request.files['file']
    category_key = request.form.get('category')
    product_index = request.form.get('product_index')
    
    if file.filename == '':
        flash('Файл не выбран', 'error')
        return redirect(url_for('admin'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Создаем уникальное имя файла
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        # Обновляем данные товара
        products = load_products()
        if category_key in products and int(product_index) < len(products[category_key]["items"]):
            # Удаляем старое изображение, если оно есть
            old_image = products[category_key]["items"][int(product_index)].get("image", "")
            if old_image and os.path.exists(os.path.join('static', old_image)):
                try:
                    os.remove(os.path.join('static', old_image))
                except:
                    pass
            
            # Сохраняем путь к новому изображению
            products[category_key]["items"][int(product_index)]["image"] = f"uploads/{unique_filename}"
            save_products(products)
            flash('Изображение успешно загружено!', 'success')
        else:
            flash('Товар не найден', 'error')
    else:
        flash('Недопустимый формат файла. Разрешены: PNG, JPG, JPEG, GIF, WEBP', 'error')
    
    return redirect(url_for('admin'))


@app.route("/delete_image", methods=["POST"])
@login_required
@admin_required
def delete_image():
    """Удаляет изображение товара"""
    category_key = request.form.get('category')
    product_index = request.form.get('product_index')
    
    products = load_products()
    if category_key in products and int(product_index) < len(products[category_key]["items"]):
        image_path = products[category_key]["items"][int(product_index)].get("image", "")
        if image_path and os.path.exists(os.path.join('static', image_path)):
            try:
                os.remove(os.path.join('static', image_path))
            except:
                pass
        
        products[category_key]["items"][int(product_index)]["image"] = ""
        save_products(products)
        flash('Изображение удалено', 'success')
    else:
        flash('Товар не найден', 'error')
    
    return redirect(url_for('admin'))


@app.route("/update_product", methods=["POST"])
@login_required
@admin_required
def update_product():
    """Обновляет данные товара (описание, характеристики)"""
    category_key = request.form.get('category')
    product_index = int(request.form.get('product_index'))
    description = request.form.get('description', '').strip()
    specs_text = request.form.get('specs', '').strip()
    
    products = load_products()
    if category_key not in products or product_index >= len(products[category_key]["items"]):
        flash('Товар не найден', 'error')
        return redirect(url_for('admin'))
    
    # Парсим характеристики из текста (каждая строка - отдельная характеристика)
    specs = []
    if specs_text:
        specs = [spec.strip() for spec in specs_text.split('\n') if spec.strip()]
    
    # Обновляем данные товара
    products[category_key]["items"][product_index]["description"] = description
    products[category_key]["items"][product_index]["specs"] = specs
    
    save_products(products)
    flash('Данные товара успешно обновлены', 'success')
    return redirect(url_for('admin'))


@app.route("/register", methods=["GET", "POST"])
def register():
    """Регистрация нового пользователя"""
    if request.method == "POST":
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        if not username or not email or not password:
            flash('Все поля обязательны для заполнения', 'error')
            return render_template("register.html")
        
        if password != password_confirm:
            flash('Пароли не совпадают', 'error')
            return render_template("register.html")
        
        if len(password) < 6:
            flash('Пароль должен содержать минимум 6 символов', 'error')
            return render_template("register.html")
        
        users = load_users()
        if username in users:
            flash('Пользователь с таким именем уже существует', 'error')
            return render_template("register.html")
        
        if any(u['email'] == email for u in users.values()):
            flash('Пользователь с таким email уже существует', 'error')
            return render_template("register.html")
        
        # Создаем нового пользователя
        users[username] = {
            'email': email,
            'password': generate_password_hash(password),
            'id': str(uuid.uuid4()),
            'is_admin': username.lower() == 'admin'
        }
        save_users(users)
        
        # Автоматически входим пользователя после регистрации
        session['user_id'] = users[username]['id']
        session['username'] = username
        session['is_admin'] = users[username].get('is_admin', False)
        
        flash('Регистрация успешна! Добро пожаловать!', 'success')
        return redirect(url_for('home'))
    
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Вход в систему"""
    if request.method == "POST":
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Введите имя пользователя и пароль', 'error')
            return render_template("login.html")
        
        users = load_users()
        if username not in users:
            flash('Неверное имя пользователя или пароль', 'error')
            return render_template("login.html")
        
        if check_password_hash(users[username]['password'], password):
            session['user_id'] = users[username]['id']
            session['username'] = username
            session['is_admin'] = users[username].get('is_admin', username.lower() == 'admin')
            flash(f'Добро пожаловать, {username}!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')
            return render_template("login.html")
    
    return render_template("login.html")


@app.route("/logout")
def logout():
    """Выход из системы"""
    session.clear()
    flash('Вы вышли из системы', 'success')
    return redirect(url_for('home'))


@app.route("/cart")
def cart():
    """Просмотр корзины"""
    cart_id = get_cart_id()
    cart = get_user_cart(cart_id)
    products = load_products()
    
    # Получаем полную информацию о товарах в корзине
    cart_items = []
    total = 0
    
    for item in cart:
        # Находим товар в каталоге
        found = False
        for category_key, category_data in products.items():
            for idx, product in enumerate(category_data['items']):
                if product['name'] == item['name']:
                    price = int(product['price'].replace('.', ''))
                    item_total = price * item['quantity']
                    total += item_total
                    cart_items.append({
                        'name': product['name'],
                        'price': product['price'],
                        'quantity': item['quantity'],
                        'total': item_total,
                        'image': product.get('image', ''),
                        'category': category_key,
                        'index': idx
                    })
                    found = True
                    break
            if found:
                break
    
    return render_template("cart.html", cart_items=cart_items, total=total, cart_count=len(cart_items))


@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    """Добавление товара в корзину"""
    category_key = request.form.get('category')
    product_index = int(request.form.get('product_index'))
    quantity = int(request.form.get('quantity', 1))
    
    if quantity < 1:
        quantity = 1
    
    products = load_products()
    if category_key not in products or product_index >= len(products[category_key]['items']):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Товар не найден'}), 400
        flash('Товар не найден', 'error')
        return redirect(url_for('home'))
    
    product = products[category_key]['items'][product_index]
    cart_id = get_cart_id()
    cart = get_user_cart(cart_id)
    
    # Проверяем, есть ли уже такой товар в корзине
    found = False
    for item in cart:
        if item['name'] == product['name']:
            item['quantity'] += quantity
            found = True
            break
    
    if not found:
        cart.append({
            'name': product['name'],
            'quantity': quantity
        })
    
    save_user_cart(cart, cart_id)
    
    # Если это AJAX запрос, возвращаем JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        cart_count = sum(item['quantity'] for item in cart)
        return jsonify({
            'success': True,
            'message': f'{product["name"]} добавлен в корзину!',
            'cart_count': cart_count
        })
    
    # Иначе обычный редирект
    flash(f'{product["name"]} добавлен в корзину!', 'success')
    return redirect(url_for('home') + '#catalog')


@app.route("/update_cart", methods=["POST"])
def update_cart():
    """Обновление количества товара в корзине"""
    product_name = request.form.get('product_name')
    quantity = int(request.form.get('quantity', 1))
    
    if quantity < 1:
        return remove_from_cart()
    
    cart_id = get_cart_id()
    cart = get_user_cart(cart_id)
    
    for item in cart:
        if item['name'] == product_name:
            item['quantity'] = quantity
            break
    
    save_user_cart(cart, cart_id)
    flash('Корзина обновлена', 'success')
    return redirect(url_for('cart'))


@app.route("/remove_from_cart", methods=["POST"])
def remove_from_cart():
    """Удаление товара из корзины"""
    product_name = request.form.get('product_name')
    cart_id = get_cart_id()
    cart = get_user_cart(cart_id)
    
    cart = [item for item in cart if item['name'] != product_name]
    save_user_cart(cart, cart_id)
    
    flash('Товар удален из корзины', 'success')
    return redirect(url_for('cart'))


@app.route("/clear_cart", methods=["POST"])
def clear_cart():
    """Очистка корзины"""
    cart_id = get_cart_id()
    save_user_cart([], cart_id)
    flash('Корзина очищена', 'success')
    return redirect(url_for('cart'))


@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    """Оформление заказа с запросом контактных данных"""
    cart_id = get_cart_id()
    cart = get_user_cart(cart_id)
    
    if not cart:
        flash('Корзина пуста', 'error')
        return redirect(url_for('cart'))
    
    if request.method == "POST":
        # Получаем контактные данные
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '').strip()
        
        if not name or not phone:
            flash('Пожалуйста, заполните имя и телефон', 'error')
            return redirect(url_for('checkout'))
        
        # Загружаем товары для расчета итоговой суммы
        products = load_products()
        cart_items = []
        total = 0
        
        for item in cart:
            found = False
            for category_key, category_data in products.items():
                for product in category_data['items']:
                    if product['name'] == item['name']:
                        price = int(product['price'].replace('.', ''))
                        item_total = price * item['quantity']
                        total += item_total
                        cart_items.append({
                            'name': product['name'],
                            'price': product['price'],
                            'quantity': item['quantity'],
                            'total': item_total
                        })
                        found = True
                        break
                if found:
                    break
        
        # Сохраняем заказ
        from datetime import datetime
        order_number = generate_order_number()
        orders = load_orders()
        
        order_data = {
            'order_number': order_number,
            'status': 'Оформлен',
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'user_id': session.get('user_id'),  # Сохраняем ID пользователя
            'customer': {
                'name': name,
                'phone': phone,
                'email': email,
                'address': address
            },
            'items': cart_items,
            'total': total
        }
        
        orders[order_number] = order_data
        save_orders(orders)
        
        # Очищаем корзину
        save_user_cart([], cart_id)
        
        flash(f'Заказ оформлен! Номер заказа: {order_number}. Сумма: {total:,}₽'.replace(',', '.'), 'success')
        return redirect(url_for('track_order', order_number=order_number))
    
    # GET запрос - показываем форму
    products = load_products()
    cart_items = []
    total = 0
    
    for item in cart:
        found = False
        for category_key, category_data in products.items():
            for product in category_data['items']:
                if product['name'] == item['name']:
                    price = int(product['price'].replace('.', ''))
                    item_total = price * item['quantity']
                    total += item_total
                    cart_items.append({
                        'name': product['name'],
                        'price': product['price'],
                        'quantity': item['quantity'],
                        'total': item_total
                    })
                    found = True
                    break
            if found:
                break
    
    return render_template("checkout.html", cart_items=cart_items, total=total)


@app.route("/my_orders")
@login_required
def my_orders():
    """Страница с активными заказами пользователя"""
    user_id = session.get('user_id')
    orders = load_orders()
    
    # Фильтруем заказы текущего пользователя
    user_orders = {}
    for order_number, order in orders.items():
        if order.get('user_id') == user_id:
            user_orders[order_number] = order
    
    # Сортируем по дате (новые первые)
    sorted_orders = dict(sorted(user_orders.items(), key=lambda x: x[1]['created_at'], reverse=True))
    
    return render_template("my_orders.html", orders=sorted_orders)


@app.route("/track/<order_number>")
def track_order(order_number):
    """Страница отслеживания заказа"""
    orders = load_orders()
    
    if order_number not in orders:
        flash('Заказ не найден', 'error')
        return redirect(url_for('home'))
    
    order = orders[order_number]
    
    # Определяем прогресс заказа
    status_order_list = ['Оформлен', 'В обработке', 'Отправлен', 'Доставлен']
    current_status_index = status_order_list.index(order['status']) if order['status'] in status_order_list else 0
    
    return render_template("track_order.html", order=order, status_order=status_order_list, current_status_index=current_status_index)


@app.route("/orders")
@login_required
@admin_required
def orders_list():
    """Список всех заказов для администратора"""
    orders = load_orders()
    # Сортируем заказы по дате создания (новые первые)
    orders_list = sorted(orders.items(), key=lambda x: x[1].get('created_at', ''), reverse=True)
    return render_template("orders_list.html", orders=orders_list)


@app.route("/update_order_status", methods=["POST"])
@login_required
@admin_required
def update_order_status():
    """Обновление статуса заказа"""
    order_number = request.form.get('order_number')
    new_status = request.form.get('status')
    
    orders = load_orders()
    if order_number not in orders:
        flash('Заказ не найден', 'error')
        return redirect(url_for('orders_list'))
    
    orders[order_number]['status'] = new_status
    save_orders(orders)
    
    flash(f'Статус заказа {order_number} обновлен на "{new_status}"', 'success')
    return redirect(url_for('orders_list'))


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=4444)
