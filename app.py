from flask import Flask, render_template, request, flash, redirect, url_for, session
from pymongo import MongoClient
from bson import ObjectId
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

client = MongoClient('mongodb+srv://rifqiabc9:rifqi123@cluster0.us7dlk3.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
db = client.heavenheart

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

products = {
    '1': {'_id': '1', 'name': 'Baju 1', 'image': '/static/pic1.png', 'price': 150000},
    '2': {'_id': '2', 'name': 'Baju 2', 'image': '/static/pic2.png', 'price': 250000},
}

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# Flask-Login
login_manager.login_view = 'login'

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, user_id, username):
        self.id = user_id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    user_data = db.useruser.find_one({"_id": ObjectId(user_id)})
    if user_data:
        return User(str(user_data['_id']), user_data['username'])
    return None

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        db.useruser.insert_one({'name': name, 'username': username, 'password': hashed_password})
        
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = db.useruser.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            user_obj = User(str(user['_id']), user['username'])
            login_user(user_obj)
            return redirect(url_for('home2')) 
        else:
            flash('Invalid username or password.')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('login'))

@app.route('/home')
@login_required
def home2():
    return render_template('home2.html')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cart')
def cart():
    user_id = current_user.get_id()
    cart_data = db.cart.find_one({'user_id': user_id})
    if cart_data:
        cart_items = cart_data['cart']
    else:
        cart_items = {}

    total_items = sum(int(item['quantity']) for item in cart_items.values())
    total_price = sum(float(item['product']['price']) * int(item['quantity']) for item in cart_items.values())

    return render_template('cart.html', cart=cart_items, total_items=total_items, total_price=total_price)


@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product_id = request.form.get('_id')
    product_name = request.form.get('name')
    product_price = float(request.form.get('price')) 
    product_image = request.form.get('image')
    quantity = int(request.form.get('quantity', 1))

    if 'cart' not in session:
        session['cart'] = {}

    if product_id in session['cart']:
        session['cart'][product_id]['quantity'] += quantity
    else:
        session['cart'][product_id] = {
            'product': {
                'name': product_name,
                'price': product_price,
                'image': product_image
            },
            'quantity': quantity
        }

    user_id = current_user.get_id()
    cart_data = {'user_id': user_id, 'cart': session['cart']}
    db.cart.update_one({'user_id': user_id}, {'$set': cart_data}, upsert=True)

    session.modified = True

    return redirect(url_for('cart'))

@app.route('/remove_from_cart/<string:product_id>', methods=['DELETE'])
def remove_from_cart(product_id):
    try:
        cart = session.get('cart', {})
        if product_id in cart:
            del cart[product_id]
            session['cart'] = cart
            flash('Item removed from cart.')
        else:
            flash('Item not found in cart.')
    except Exception as e:
        flash('Failed to remove item from cart.')

    return redirect(url_for('cart'))

@app.route('/product')
def product():
    products = db.produtcs.find()
    return render_template('product.html', products=products)

@app.route('/detail_product/<string:product_id>', methods=['GET', 'POST'])
def detail_product(product_id):
    try:
        obj_id = ObjectId(product_id)
        
        product = db.produtcs.find_one({"_id": obj_id})

        if product:
            if request.method == 'POST':
                quantity = int(request.form.get('quantity', 1))
                action = request.form.get('action')

                if action == 'add_to_cart':
                    if 'cart' not in db.list_collection_names():
                        db.create_collection('cart')

                    user_id = current_user.get_id()
                    if user_id:
                        db.cart.update_one(
                            {'user_id': user_id},
                            {'$set': {'cart': session['cart']}},
                            upsert=True
                        )

                    flash('Product added to cart!')
                    return redirect(url_for('cart'))

                elif action == 'buy':
                    return redirect(url_for('order'))

            return render_template('detail_product.html', product=product)
        else:
            flash('Product not found.')
            return redirect(url_for('home2'))

    except Exception as e:
        flash('Invalid product ID.')
        return redirect(url_for('home2'))
    
@app.route('/order', methods=['GET'])
def order():
    print(f"Current user authenticated: {current_user.is_authenticated}")
    if current_user.is_authenticated:
        print(f"Current user username: {current_user.username}")
    else:
        print("Current user is not authenticated")

    cart = session.get('cart', {})
    total_items = sum(item['quantity'] for item in cart.values())
    total_price = sum(float(item['product']['price']) * int(item['quantity']) for item in cart.values())

    username = current_user.username if current_user.is_authenticated else "Guest"

    return render_template('order.html', cart=cart, total_items=total_items, total_price=total_price, username=username)



@app.route('/place_order', methods=['POST'])
@login_required
def place_order():
    user_id = current_user.get_id()
    username = current_user.username 
    cart = session.get('cart', {})
    total_items = sum(item['quantity'] for item in cart.values())
    total_price = sum(float(item['product']['price']) * int(item['quantity']) for item in cart.values())

    # Dapatkan nama produk dari keranjang
    product_names = [item['product']['name'] for item in cart.values()]

    # Debugging log
    print(f"Product Names: {product_names}")
    
    # Simpan pesanan ke database
    order_data = {
        'user_id': user_id,
        'customer_name': username,  # Simpan nama pengguna
        'product_names': product_names,  # Simpan nama produk sebagai list
        'order_summary': f"Rp. {total_price}",
        'order_status': 'Waiting Confirmation'
    }
    db.orders.insert_one(order_data)

    # Kosongkan keranjang setelah berhasil dipesan
    session['cart'] = {}

    flash('Order placed successfully!')

    return redirect(url_for('my_order'))


@app.route('/my_order')
@login_required
def my_order():
    user_id = current_user.get_id()
    orders = db.orders.find({'user_id': user_id})

    return render_template('my_order.html', orders=orders)


@app.route('/accept_order/<string:order_id>', methods=['POST'])
@login_required
def accept_order(order_id):
    try:
        # Pastikan hanya admin atau pengguna yang memiliki akses ke pesanan ini yang dapat menerima pesanan
        order = db.orders.find_one({'_id': ObjectId(order_id), 'user_id': current_user.get_id()})
        if order:
            # Update status pesanan menjadi "Accepted"
            db.orders.update_one({'_id': ObjectId(order_id)}, {'$set': {'order_status': 'Accepted'}})
            flash('Order accepted successfully!')
        else:
            flash('You are not authorized to accept this order.')
    except Exception as e:
        flash('Failed to accept order.')

    return redirect(url_for('my_order'))


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
