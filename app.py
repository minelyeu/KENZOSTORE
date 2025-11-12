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
                {"name": "AirPods Max 2", "price": "11.490", "image": ""},
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

def get_user_cart(user_id):
    """Получает корзину пользователя"""
    carts = load_carts()
    if user_id not in carts:
        carts[user_id] = []
        save_carts(carts)
    return carts[user_id]

def save_user_cart(user_id, cart):
    """Сохраняет корзину пользователя"""
    carts = load_carts()
    carts[user_id] = cart
    save_carts(carts)

def login_required(f):
    """Декоратор для проверки авторизации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'error')
            return redirect(url_for('login'))
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
    if 'user_id' in session:
        cart = get_user_cart(session['user_id'])
        cart_count = sum(item['quantity'] for item in cart)
    
    return render_template("index.html", products=products_list, cart_count=cart_count, user=session.get('username'))


@app.route("/admin")
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


@app.route("/upload", methods=["POST"])
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
            'id': str(uuid.uuid4())
        }
        save_users(users)
        
        flash('Регистрация успешна! Войдите в систему', 'success')
        return redirect(url_for('login'))
    
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
@login_required
def cart():
    """Просмотр корзины"""
    user_id = session['user_id']
    cart = get_user_cart(user_id)
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
@login_required
def add_to_cart():
    """Добавление товара в корзину"""
    category_key = request.form.get('category')
    product_index = int(request.form.get('product_index'))
    quantity = int(request.form.get('quantity', 1))
    
    if quantity < 1:
        quantity = 1
    
    products = load_products()
    if category_key not in products or product_index >= len(products[category_key]['items']):
        flash('Товар не найден', 'error')
        return redirect(url_for('home'))
    
    product = products[category_key]['items'][product_index]
    user_id = session['user_id']
    cart = get_user_cart(user_id)
    
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
    
    save_user_cart(user_id, cart)
    flash(f'{product["name"]} добавлен в корзину!', 'success')
    return redirect(url_for('home'))


@app.route("/update_cart", methods=["POST"])
@login_required
def update_cart():
    """Обновление количества товара в корзине"""
    product_name = request.form.get('product_name')
    quantity = int(request.form.get('quantity', 1))
    
    if quantity < 1:
        return remove_from_cart()
    
    user_id = session['user_id']
    cart = get_user_cart(user_id)
    
    for item in cart:
        if item['name'] == product_name:
            item['quantity'] = quantity
            break
    
    save_user_cart(user_id, cart)
    flash('Корзина обновлена', 'success')
    return redirect(url_for('cart'))


@app.route("/remove_from_cart", methods=["POST"])
@login_required
def remove_from_cart():
    """Удаление товара из корзины"""
    product_name = request.form.get('product_name')
    user_id = session['user_id']
    cart = get_user_cart(user_id)
    
    cart = [item for item in cart if item['name'] != product_name]
    save_user_cart(user_id, cart)
    
    flash('Товар удален из корзины', 'success')
    return redirect(url_for('cart'))


@app.route("/clear_cart", methods=["POST"])
@login_required
def clear_cart():
    """Очистка корзины"""
    user_id = session['user_id']
    save_user_cart(user_id, [])
    flash('Корзина очищена', 'success')
    return redirect(url_for('cart'))


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port='4114')
