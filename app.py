from flask import Flask, render_template, request, redirect, session, url_for, flash, Response
from pymongo import MongoClient
from bson.objectid import ObjectId



app = Flask(__name__)
app.secret_key = 'your_secret_key'

client = MongoClient("mongodb://localhost:27017/")
db = client['product_db']
users = db['users']
products = db['products']
cart = db['cart']

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        role = request.form['role']

        if users.find_one({'username': username}):
            flash('Username already exists.')
            return redirect(url_for('register'))

        users.insert_one({'username': username, 'password': password, 'role': role})
        flash('Registered successfully! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = users.find_one({
            'username': request.form['username'],
            'password': request.form['password']
        })
        if user:
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        flash('Invalid credentials.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    all_products = list(products.find())
    if session['role'] == 'admin':
        return render_template('admin_dashboard.html', products=all_products)
    else:
        return render_template('user_dashboard.html', products=all_products)

@app.route('/add_product', methods=['POST'])
def add_product():
    if session.get('role') != 'admin':
        return redirect(url_for('dashboard'))
    
    name = request.form['name']
    category = request.form['category']
    price = float(request.form['price'])
    discount = float(request.form.get('discount', 0))  # Discount % field
    description = request.form['description']
    
    products.insert_one({
        'name': name,
        'category': category,
        'price': price,
        'discount': discount,
        'description': description
    })
    flash('Product added successfully.')
    return redirect(url_for('dashboard'))

@app.route('/update_discount/<product_id>', methods=['POST'])
def update_discount(product_id):
    if session.get('role') != 'admin':
        return redirect(url_for('dashboard'))

    discount = float(request.form['discount'])
    products.update_one({'_id': ObjectId(product_id)}, {'$set': {'discount': discount}})
    flash('Discount updated successfully.')
    return redirect(url_for('dashboard'))

@app.route('/delete_product/<product_id>')
def delete_product(product_id):
    if session.get('role') != 'admin':
        return redirect(url_for('dashboard'))
    
    products.delete_one({'_id': ObjectId(product_id)})
    flash('Product deleted successfully.')
    return redirect(url_for('dashboard'))

@app.route('/add_to_cart/<product_id>')
def add_to_cart(product_id):
    if 'user_id' not in session or session.get('role') == 'admin':
        flash('Only users can add to cart.')
        return redirect(url_for('dashboard'))

    user_id = session['user_id']
    existing = cart.find_one({'user_id': user_id, 'product_id': product_id})
    
    if existing:
        cart.update_one({'_id': existing['_id']}, {'$inc': {'quantity': 1}})
    else:
        cart.insert_one({'user_id': user_id, 'product_id': product_id, 'quantity': 1})
    flash('Product added to cart.')
    return redirect(url_for('dashboard'))

@app.route('/cart')
def view_cart():
    # Check user logged in and role
    if 'user_id' not in session or session.get('role') == 'admin':
        flash('Only users can view the cart.')
        return redirect(url_for('dashboard'))

    user_id = session['user_id']

    # Get cart items for this user
    user_cart = cart.find({'user_id': user_id})

    cart_items = []
    total = 0
    for item in user_cart:
        # Fetch product details by ObjectId
        product = products.find_one({'_id': ObjectId(item['product_id'])})
        if product:
            # Calculate price after discount if any
            discount = product.get('discount', 0)
            price_after_discount = product['price'] * (1 - discount / 100)

            subtotal = price_after_discount * item['quantity']
            total += subtotal

            cart_items.append({
                'cart_item_id': str(item['_id']),
                'product_id': str(product['_id']),
                'name': product['name'],
                'price': round(price_after_discount, 2),
                'quantity': item['quantity'],
                'subtotal': round(subtotal, 2),
            })

    return render_template('cart.html', cart_items=cart_items, total=round(total, 2))


@app.route('/update_cart/<cart_item_id>', methods=['POST'])
def update_cart(cart_item_id):
    if 'user_id' not in session or session.get('role') == 'admin':
        flash('Unauthorized action.')
        return redirect(url_for('dashboard'))

    quantity = int(request.form['quantity'])
    if quantity <= 0:
        cart.delete_one({'_id': ObjectId(cart_item_id)})
    else:
        cart.update_one({'_id': ObjectId(cart_item_id)}, {'$set': {'quantity': quantity}})
    flash('Cart updated successfully.')
    return redirect(url_for('view_cart'))

@app.route('/remove_from_cart/<cart_item_id>')
def remove_from_cart(cart_item_id):
    if 'user_id' not in session or session.get('role') == 'admin':
        flash('Unauthorized action.')
        return redirect(url_for('dashboard'))

    cart.delete_one({'_id': ObjectId(cart_item_id)})
    flash('Item removed from cart.')
    return redirect(url_for('view_cart'))

@app.route('/checkout')
def checkout():
    if 'user_id' not in session or session.get('role') == 'admin':
        flash('Only users can checkout.')
        return redirect(url_for('dashboard'))

    user_id = session['user_id']
    cart.delete_many({'user_id': user_id})
    flash("Checkout complete! Thank you for your purchase.")
    return redirect(url_for('dashboard'))

@app.route('/view_users')
def view_users():
    if session.get('role') != 'admin':
        flash('Unauthorized')
        return redirect(url_for('dashboard'))

    all_users = users.find()
    # Convert cursor to list of dicts and convert ObjectId to string for template
    user_list = []
    for user in all_users:
        user_list.append({
            'id': str(user['_id']),
            'username': user.get('username', 'N/A'),  # make sure field name is 'username'
            'email': user.get('email', 'N/A'),        # add other fields you want to show
            'role': user.get('role', 'N/A')
        })

    return render_template('view_users.html', users=user_list)

@app.route('/view_carts')
def view_carts():
    if session.get('role') != 'admin':
        flash('Unauthorized')
        return redirect(url_for('dashboard'))

    all_carts = cart.find()
    carts_data = []
    total_value = 0
    for c in all_carts:
        product = products.find_one({'_id': ObjectId(c['product_id'])})
        user = users.find_one({'_id': ObjectId(c['user_id'])})
        if product and user:
            subtotal = product['price'] * c['quantity']
            total_value += subtotal
            carts_data.append({
                'username': user['username'],
                'product_name': product['name'],
                'quantity': c['quantity'],
                'price': product['price'],
                'subtotal': subtotal,
            })

    return render_template('view_carts.html', carts=carts_data, total=total_value)


@app.route('/export_users_txt')
def export_users_txt():
    if session.get('role') != 'admin':
        flash("Unauthorized")
        return redirect(url_for('dashboard'))

    all_users = users.find()
    lines = ["List of Registered Users:\n", "="*30 + "\n"]
    for u in all_users:
        lines.append(f"Username: {u['username']}, Role: {u['role']}")
    txt_content = "\n".join(lines)

    return Response(
        txt_content,
        mimetype='text/plain',
        headers={'Content-Disposition': 'attachment;filename=users_list.txt'}
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)



