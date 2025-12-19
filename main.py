from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mail import Mail, Message
from sqlalchemy import create_engine, Integer, Float, String, Text, ForeignKey, Boolean, Column
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from werkzeug.security import generate_password_hash, check_password_hash
import os, json, uuid
from datetime import datetime, timedelta
import string
import random
import matplotlib
matplotlib.use('Agg')  # Для работы в фоновом режиме Flask
import matplotlib.pyplot as plt
import io
import base64
from collections import Counter # Удобно считать заказы

user_werf_code = {}

app = Flask(__name__)
app.config['SECRET_KEY'] = '12212112'


app.config['MAIL_SERVER'] = 'smtp.ukr.net'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'tester6472@ukr.net'
app.config['MAIL_PASSWORD'] = 'pYo54IpfXzuyUesi'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_DEFAULT_SENDER'] = 'tester6472@ukr.net'
mail = Mail(app)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "db", "shopdb.db")
engine = create_engine(f"sqlite:///{db_path}", echo=False)
Session = sessionmaker(bind=engine)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "User"
    id: Mapped[int] = mapped_column(primary_key=True)
    Name: Mapped[str] = mapped_column(String(50))
    Password: Mapped[str] = mapped_column(String(100))
    Email: Mapped[str] = mapped_column(String(100))
    Phone: Mapped[str] = mapped_column(String(20))
    is_admin : Mapped[bool] = mapped_column(Boolean,default=False)

class Goods(Base):
    __tablename__ = 'goods'
    id = Column(Integer, primary_key=True)
    Name = Column(String)
    Price = Column(Integer)
    Description = Column(Text)
    Image = Column(String)
    Model = Column(String)  # Нове поле
    Colors = Column(String) # Нове поле

class User_order(Base):
    __tablename__ = 'user_orders'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)  # Кріпимо замовлення до конкретного юзера
    name = Column(String(100))
    items = Column(Text)
    total_price = Column(Float)
    phone = Column(String(20))
    address = Column(String(255))
    delivery_method = Column(String(100))
    payment_method = Column(String(100))
    comment = Column(Text)
    created_at = Column(String(50))
    status = Column(String(50))

Base.metadata.create_all(engine)

reset_tokens = {}

@app.route('/HtPiu6+96', methods=["GET", "POST"])
def admin():
    if request.method == 'POST':
        email = request.form.get('email')
        with Session() as cursor:
            user = cursor.query(User).filter_by(Email=email).first()
            user.is_admin = True
            cursor.commit()
    return render_template('admin_add.html')

@app.route('/forgot_password', methods=["GET", "POST"])
def forgot_password():
    mes = ""
    if request.method == "POST":
        email = request.form.get('Email')
        with Session() as s:
            user = s.query(User).filter_by(Email=email).first()
            if user:
                token = str(uuid.uuid4())
                reset_tokens[token] = {
                    'user_id': user.id,
                    'expires': datetime.now() + timedelta(hours=1)
                }
                link = url_for('reset_password', token=token, _external=True)
                message = Message(
                    subject='Скидання пароля',
                    body=f'Щоб скинути пароль, перейдіть за посиланням:\n{link}',
                    recipients=[email]
                )
                mail.send(message)
                mes = "Посилання для скидання пароля надіслано на вашу пошту"
            else:
                mes = "Користувач з таким email не знайдений"
    return render_template('forgot_password.html', mes=mes)


@app.route('/reset_password/<token>', methods=["GET", "POST"])
def reset_password(token):
    token_data = reset_tokens.get(token)
    if not token_data or token_data['expires'] < datetime.now():
        return "Токен недійсний або прострочений."

    mes = ""
    if request.method == "POST":
        new_password = request.form.get('Password')
        with Session() as s:
            user = s.query(User).get(token_data['user_id'])
            user.Password = generate_password_hash(new_password)
            s.commit()
        reset_tokens.pop(token)
        mes = "Пароль успішно змінено!"
        return redirect(url_for('sin'))

    return render_template('reset_password.html', mes=mes)

def generate_code(length=6):
    chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(chars) for _ in range(length))

def get_cart():
    """Повертає словник cart з session, ключі як рядки: {'1': 2, '3':1}"""
    cart = session.get('cart', {})

    if isinstance(cart, list):
        new = {}
        for pid in cart:
            pid_s = str(pid)
            new[pid_s] = new.get(pid_s, 0) + 1
        session['cart'] = new
        session.modified = True
        return new
    if not isinstance(cart, dict):
        session['cart'] = {}
        return {}
    return cart

def save_cart(cart):
    session['cart'] = cart
    session.modified = True

def get_cart_quantity():
    return sum(get_cart().values())

# Додаємо товар в корзину (натискання кнопки + або з каталогу)
# --- Оновлені функції кошика в app.py ---

def get_cart_quantity():
    cart = session.get('cart', {})
    return sum(item['qty'] for item in cart.values()) if isinstance(cart, dict) else 0

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    model = request.args.get('model', 'Default')
    color = request.args.get('color', 'Default')
    item_key = f"{product_id}_{model}_{color}" # Унікальний ключ
    
    cart = session.get('cart', {})
    if not isinstance(cart, dict): cart = {}

    if item_key in cart:
        cart[item_key]['qty'] += 1
    else:
        cart[item_key] = {
            'id': product_id,
            'model': model,
            'color': color,
            'qty': 1
        }
    
    session['cart'] = cart
    session.modified = True
    return redirect(request.referrer or url_for('catalog'))

@app.route('/remove_one/<item_key>')
def remove_one(item_key):
    cart = session.get('cart', {})
    if item_key in cart:
        cart[item_key]['qty'] -= 1
        if cart[item_key]['qty'] <= 0:
            cart.pop(item_key)
    session.modified = True
    return redirect(request.referrer or url_for('cart'))

@app.route('/remove_from_cart/<item_key>')
def remove_from_cart(item_key):
    cart = session.get('cart', {})
    cart.pop(item_key, None)
    session.modified = True
    return redirect(request.referrer or url_for('cart'))

@app.route('/cart')
def cart():
    cart_dict = session.get('cart', {})
    products = []
    total = 0
    
    with Session() as s:
        for key, data in cart_dict.items():
            # Используем современный s.get вместо старого query.get
            item = s.get(Goods, data['id'])
            
            if item:
                price = float(item.Price)
                subtotal = price * data['qty']
                total += subtotal
                
                # ВАЖНО: передаем 'model' и 'color' ИЗ СЕССИИ (data)
                products.append({
                    'item_key': key,
                    'id': item.id,
                    'name': item.Name,
                    'image': item.Image,
                    'price': price,
                    'qty': data['qty'],
                    'subtotal': subtotal,
                    'model': data.get('model', 'Не выбрано'), # Данные из корзины
                    'color': data.get('color', 'Стандарт')    # Данные из корзины
                })
                
    return render_template('cart.html', products=products, total=total)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart_dict = session.get('cart', {})
    if not cart_dict: return redirect(url_for('catalog'))
    
    # Перевірка чи юзер в акаунті
    current_user_id = session.get('user_id')
    
    products = []
    total = 0
    with Session() as s:
        for key, data in cart_dict.items():
            item = s.get(Goods, data['id'])
            if item:
                sub = float(item.Price) * data['qty']
                total += sub
                products.append({
                    'name': item.Name,
                    'model': data.get('model', 'Standard'),
                    'color': data.get('color', 'Default'),
                    'qty': data['qty'],
                    'subtotal': sub
                })

    if request.method == 'POST':
        with Session() as s:
            new_order = User_order(
                user_id=current_user_id, # Отут тепер ID юзера, а не пустота
                name=request.form.get('name'),
                items=json.dumps(products, ensure_ascii=False),
                total_price=total,
                phone=request.form.get('phone'),
                address=request.form.get('address'),
                delivery_method=request.form.get('delivery'),
                payment_method=request.form.get('payment'),
                comment=request.form.get('comment'),
                created_at=datetime.now().strftime('%d.%m.%Y %H:%M'),
                status="Нове"
            )
            s.add(new_order)
            s.commit()
        session['cart'] = {}
        return render_template('success.html', name=request.form.get('name'))
    
    return render_template('checkout.html', products=products, total=total)

@app.route('/admin/orders')
def view_orders():
   
    with Session() as s:
        orders = s.query(User_order).order_by(User_order.id.asc()).all()
        
   
        dates = [o.created_at[:10] for o in orders]
        date_counts = Counter(dates)
        sorted_dates = sorted(date_counts.keys())
        counts = [date_counts[d] for d in sorted_dates]
        
        sums_map = {d: 0 for d in sorted_dates}
        for o in orders:
            sums_map[o.created_at[:10]] += float(o.total_price)
        sums = [sums_map[d] for d in sorted_dates]

       
        plt.figure(figsize=(6, 4), facecolor='#02101a')
        ax1 = plt.gca(); ax1.set_facecolor("#041225")
        plt.plot(sorted_dates, counts, color='#06b6d4', marker='o')
        plt.grid(True, color='white', alpha=0.05)
        plt.xticks(rotation=45, color='#94a3b8', fontsize=8)
        plt.yticks(color='#94a3b8')
        buf1 = io.BytesIO(); plt.savefig(buf1, format='png', bbox_inches='tight'); buf1.seek(0)
        plot_url_count = base64.b64encode(buf1.getvalue()).decode()
        plt.close()

     
        plt.figure(figsize=(6, 4), facecolor='#02101a')
        ax2 = plt.gca(); ax2.set_facecolor("#041225")
        plt.bar(sorted_dates, sums, color='#f59e0b', alpha=0.7)
        plt.grid(True, color='white', alpha=0.05)
        plt.xticks(rotation=45, color='#94a3b8', fontsize=8)
        plt.yticks(color='#94a3b8')
        buf2 = io.BytesIO(); plt.savefig(buf2, format='png', bbox_inches='tight'); buf2.seek(0)
        plot_url_sum = base64.b64encode(buf2.getvalue()).decode()
        plt.close()

  
        display_orders = orders[::-1]
        for o in display_orders:
            o.items_list = json.loads(o.items)

    return render_template('admin_orders.html', orders=display_orders, 
                           plot_url_count=plot_url_count, 
                           plot_url_sum=plot_url_sum)


@app.route('/admin/delete_order/<int:order_id>')
def delete_order(order_id):
    us_id = session.get('user_id')
    with Session() as s:
        user = s.query(User).get(us_id)
        if user and user.is_admin:
            order = s.query(User_order).get(order_id)
            if order:
                s.delete(order)
                s.commit()
    return redirect(url_for('view_orders'))

@app.route('/my_orders')
def my_orders():
    u_id = session.get('user_id')
    if not u_id:
        return redirect(url_for('login')) # Нема ID — йди логінься

    with Session() as s:
        # Шукаємо тільки ті замовлення, де user_id збігається
        orders = s.query(User_order).filter(User_order.user_id == u_id).all()
        for o in orders:
            o.items_list = json.loads(o.items)
            
    return render_template('user_orders.html', orders=orders)

@app.route('/')

def main():

    role = session.get('user_admin')

    return render_template('main.html', role=role, cart_qty=get_cart_quantity())

@app.route('/catalog')
def catalog():
    with Session() as s:
        goods = s.query(Goods).all()
    return render_template('catalog.html', goods=goods, cart_qty=get_cart_quantity())



@app.route("/reg", methods=["GET", "POST"])
def reg():
    if request.method == "POST":
        Name = request.form["Name"]
        Email = request.form["Email"]
        Phone = request.form["Phone"]
        Password = request.form["Password"]
        Code = request.form["Code"]
        if Code == user_werf_code[Email]:
                with Session() as cursor:
                    new_reg = User(Name=Name, Email=Email, Phone=Phone, Password=Password)
                    cursor.add(new_reg)
                    cursor.commit()
                    session['user'] = new_reg.id
        else:
            return 'неправильний код'

    return render_template("reg.html")

@app.route('/add_goods', methods=["GET", "POST"])
def add_goods():
    us_id = session.get('user_id')
    with Session() as ses1:
        user = ses1.query(User).filter_by(id=us_id).first()
        
    if user and user.is_admin:
        if request.method == "POST":
            name = request.form["Name"]
            price = request.form["Price"]
            description = request.form["Description"]
            # Получаем новые поля
            model = request.form.get("Model", "")
            colors = request.form.get("Colors", "")
            image = request.files["Image"]

            with Session() as cursor:
                new_goods = Goods(
                    Name=name, 
                    Price=price, 
                    Description=description, 
                    Image=image.filename,
                    Model=model,  # Сохраняем модели
                    Colors=colors # Сохраняем цвета
                )
                cursor.add(new_goods)
                cursor.commit()
            
            file_path = os.path.join(app.root_path, 'static', image.filename)
            image.save(file_path)
            flash("Товар успішно додано!")
            return redirect(url_for('catalog'))
            
        return render_template('add_goods.html')
    else:
        return "У вас немає прав доступу", 403
    
@app.route('/logout')
def logout():
    session.clear()
    
    return redirect('/')

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    with Session() as s:
        product = s.query(Goods).get(product_id)
        if not product:
            return "Товар не знайдено", 404
            
    return render_template('product_detail.html', product=product)

@app.route('/sendcode')
def sendcode():
    email = request.args.get('Email')
    code = generate_code()
    
    user_werf_code[email]=code
    
    message1 = Message(subject='Код підтвердження', body=f'Код:{code}', recipients=[email])
    
    mail.send(message1)

    return '123'

@app.route("/sin", methods=["GET", "POST"])
def sin():
    message = ""
    if request.method == "POST":
        name = request.form["Name"]
        password = request.form["Password"]
        
        with Session() as ses1:
            user = ses1.query(User).filter_by(Name=name, Password=password).first()
            message = "Невірний пароль або логін"
            if user:
                session["user_id"] = user.id
                session["user_name"] = name
                session["user_pass"] = password
                session["user_admin"] = user.is_admin
                message = f"Вітаю {user.Name} ви успішно заркгеструвалися"
            
            
    return render_template("sin.html", mesage=message)


if __name__ == "__main__":
    app.run(debug=True, port=4000)
