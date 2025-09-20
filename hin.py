def hello():
    return render_template('index.html')
    app.run(debug=True)

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'ecommerce_secret_key'  # Needed for session
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///jiho.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

# Product model
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    desc = db.Column(db.String(300))
    img = db.Column(db.String(200))
    currency = db.Column(db.String(10), default='PKR')  # Default to PKR

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.before_request
def create_tables_and_seed():
    # DEVELOPMENT ONLY: Delete DB if schema mismatch (e.g., new columns added)
    db_path = os.path.join(os.path.dirname(__file__), 'jiho.db')
    if not hasattr(app, '_tables_created'):
        try:
            db.create_all()
            # Seed products if not present
            if Product.query.count() == 0:
                db.session.add_all([
                    Product(name='computer', price= 4999, desc='A powerful laptop for work and play. 16GB RAM, 512GB SSD, Intel i7.', img='img/laptop.jpeg', currency='PKR'),
                    Product(name='Smartphone', price= 14499, desc='A modern smartphone with a stunning display and long battery life.', img='img/smartphone.jpeg', currency='PKR'),
                    Product(name='Headphones', price= 1099, desc='Noise-cancelling headphones for immersive sound.', img='img/headphones.jpeg', currency='PKR'),
                    Product(name='Laptop', price= 5599, desc='Noise-cancelling headphones for immersive sound.', img='img/computer.jpeg', currency='PKR'),
                ])
                db.session.commit()
            app._tables_created = True
        except Exception as e:
            # If migration error, delete DB and recreate (DEV ONLY)
            if os.path.exists(db_path):
                os.remove(db_path)
            db.create_all()
            app._tables_created = True
            # You may want to log or print the error for debugging
            print("Database reset due to schema change:", e)


def get_cart():
    return session.setdefault('cart', {})


# Signup route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if not email.endswith('@gmail.com'):
            flash('Only Gmail addresses are allowed.')
            return redirect(url_for('signup'))
        if User.query.filter_by(email=email).first():
            flash('Email already exists.')
            return redirect(url_for('signup'))
        hashed_pw = generate_password_hash(password)
        # Make first user admin
        is_admin = User.query.count() == 0
        user = User(email=email, password=hashed_pw, is_admin=is_admin)
        db.session.add(user)
        db.session.commit()
        flash('Signup successful. Please log in.')
        return redirect(url_for('login'))
    return render_template('signup.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully.')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password.')
    return render_template('login.html')

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.')
    return redirect(url_for('login'))

@app.route('/')
def home():
    products = Product.query.all()  # Show all products on home
    return render_template('index.html', products=products)

@app.route('/products')
def product_list():
    products = Product.query.all()
    return render_template('products.html', products=products)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product_detail.html', product=product)

@app.route('/cart')
@login_required
def cart():
    cart = get_cart()
    items = []
    total = 0
    for pid, qty in cart.items():
        product = Product.query.get(int(pid))
        if product:
            items.append({'product': product, 'qty': qty})
            total += product.price * qty
    if not items:
        flash('Your cart is empty. Please add products first.')
        return redirect(url_for('product_list'))
    return render_template('cart.html', items=items, total=total)

@app.route('/add_to_cart/<int:product_id>')
@login_required
def add_to_cart(product_id):
    cart = get_cart()
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    session['cart'] = cart
    return redirect(url_for('cart'))

@app.route('/checkout')
@login_required
def checkout():
    session.pop('cart', None)
    return render_template('checkout.html')


# Admin add product route (must be after app, db, models)
@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if not current_user.is_admin:
        flash('Only admin can add products.')
        return redirect(url_for('home'))
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        desc = request.form['desc']
        img = request.form['img']
        currency = request.form.get('currency', 'USD')  # Get currency from form
        db.session.add(Product(name=name, price=price, desc=desc, img=img, currency=currency))
        db.session.commit()
        flash('Product added!')
        return redirect(url_for('product_list'))
    # Provide a list of currencies to the template
    currencies = ['USD', 'EUR', 'INR', 'GBP', 'JPY', 'CNY']
    return render_template('add_product.html', currencies=currencies)

@app.route('/delete_product/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    if not current_user.is_admin:
        flash('Only admin can delete products.')
        return redirect(url_for('home'))
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted.')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
