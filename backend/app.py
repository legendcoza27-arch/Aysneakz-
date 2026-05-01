from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from database import init_db, get_db
import sqlite3

load_dotenv()

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-this')
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=30)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

jwt = JWTManager(app)
CORS(app)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialize database
init_db()

# ==================== ADMIN ROUTES ====================

@app.route('/api/admin/register', methods=['POST'])
def admin_register():
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Missing required fields'}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    # Check if admin already exists
    cursor.execute('SELECT id FROM admins WHERE email = ?', (data['email'],))
    if cursor.fetchone():
        return jsonify({'message': 'Admin already exists'}), 409
    
    hashed_password = generate_password_hash(data['password'])
    
    try:
        cursor.execute(
            'INSERT INTO admins (email, password, name) VALUES (?, ?, ?)',
            (data['email'], hashed_password, data.get('name', 'Admin'))
        )
        db.commit()
        return jsonify({'message': 'Admin registered successfully'}), 201
    except Exception as e:
        db.rollback()
        return jsonify({'message': str(e)}), 500

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Missing email or password'}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT id, email, password FROM admins WHERE email = ?', (data['email'],))
    admin = cursor.fetchone()
    
    if not admin or not check_password_hash(admin[2], data['password']):
        return jsonify({'message': 'Invalid credentials'}), 401
    
    access_token = create_access_token(identity=admin[0])
    return jsonify({'access_token': access_token, 'admin_id': admin[0]}), 200

# ==================== PRODUCT MANAGEMENT ====================

@app.route('/api/admin/products', methods=['POST'])
@jwt_required()
def create_product():
    admin_id = get_jwt_identity()
    
    # Check if product data is provided
    if 'name' not in request.form or 'price' not in request.form:
        return jsonify({'message': 'Missing required fields'}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    # Handle image upload
    image_filename = None
    if 'image' in request.files:
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Add timestamp to filename to make it unique
            filename = f"{datetime.now().timestamp()}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_filename = filename
    
    try:
        cursor.execute(
            '''INSERT INTO products (name, description, price, image_url, admin_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (
                request.form.get('name'),
                request.form.get('description', ''),
                float(request.form.get('price')),
                image_filename,
                admin_id,
                datetime.now().isoformat()
            )
        )
        db.commit()
        product_id = cursor.lastrowid
        return jsonify({'message': 'Product created', 'product_id': product_id}), 201
    except Exception as e:
        db.rollback()
        return jsonify({'message': str(e)}), 500

@app.route('/api/admin/products/<int:product_id>', methods=['PUT'])
@jwt_required()
def update_product(product_id):
    admin_id = get_jwt_identity()
    
    db = get_db()
    cursor = db.cursor()
    
    # Check if product exists and belongs to admin
    cursor.execute('SELECT * FROM products WHERE id = ? AND admin_id = ?', (product_id, admin_id))
    product = cursor.fetchone()
    
    if not product:
        return jsonify({'message': 'Product not found'}), 404
    
    # Handle image upload if provided
    image_filename = product[4]  # existing image
    if 'image' in request.files:
        file = request.files['image']
        if file and allowed_file(file.filename):
            # Delete old image if exists
            if image_filename and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], image_filename)):
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
            
            filename = secure_filename(file.filename)
            filename = f"{datetime.now().timestamp()}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_filename = filename
    
    try:
        cursor.execute(
            '''UPDATE products SET name = ?, description = ?, price = ?, image_url = ?
               WHERE id = ?''',
            (
                request.form.get('name', product[1]),
                request.form.get('description', product[2]),
                float(request.form.get('price', product[3])),
                image_filename,
                product_id
            )
        )
        db.commit()
        return jsonify({'message': 'Product updated'}), 200
    except Exception as e:
        db.rollback()
        return jsonify({'message': str(e)}), 500

@app.route('/api/admin/products/<int:product_id>', methods=['DELETE'])
@jwt_required()
def delete_product(product_id):
    admin_id = get_jwt_identity()
    
    db = get_db()
    cursor = db.cursor()
    
    # Check if product exists and belongs to admin
    cursor.execute('SELECT image_url FROM products WHERE id = ? AND admin_id = ?', (product_id, admin_id))
    product = cursor.fetchone()
    
    if not product:
        return jsonify({'message': 'Product not found'}), 404
    
    # Delete image file if exists
    if product[0] and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], product[0])):
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], product[0]))
    
    try:
        cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
        db.commit()
        return jsonify({'message': 'Product deleted'}), 200
    except Exception as e:
        db.rollback()
        return jsonify({'message': str(e)}), 500

@app.route('/api/admin/products', methods=['GET'])
@jwt_required()
def get_admin_products():
    admin_id = get_jwt_identity()
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute(
        '''SELECT id, name, description, price, image_url, created_at FROM products
           WHERE admin_id = ? ORDER BY created_at DESC''',
        (admin_id,)
    )
    products = cursor.fetchall()
    
    products_list = [
        {
            'id': p[0],
            'name': p[1],
            'description': p[2],
            'price': p[3],
            'image_url': p[4],
            'created_at': p[5]
        }
        for p in products
    ]
    
    return jsonify(products_list), 200

# ==================== PUBLIC ROUTES ====================

@app.route('/api/products', methods=['GET'])
def get_products():
    db = get_db()
    cursor = db.cursor()
    
    # Get search and filter parameters
    search = request.args.get('search', '')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    
    query = 'SELECT id, name, description, price, image_url FROM products WHERE 1=1'
    params = []
    
    if search:
        query += ' AND (name LIKE ? OR description LIKE ?)'
        search_term = f'%{search}%'
        params.extend([search_term, search_term])
    
    if min_price is not None:
        query += ' AND price >= ?'
        params.append(min_price)
    
    if max_price is not None:
        query += ' AND price <= ?'
        params.append(max_price)
    
    query += ' ORDER BY id DESC'
    
    cursor.execute(query, params)
    products = cursor.fetchall()
    
    products_list = [
        {
            'id': p[0],
            'name': p[1],
            'description': p[2],
            'price': p[3],
            'image_url': p[4]
        }
        for p in products
    ]
    
    return jsonify(products_list), 200

@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute(
        'SELECT id, name, description, price, image_url FROM products WHERE id = ?',
        (product_id,)
    )
    product = cursor.fetchone()
    
    if not product:
        return jsonify({'message': 'Product not found'}), 404
    
    return jsonify({
        'id': product[0],
        'name': product[1],
        'description': product[2],
        'price': product[3],
        'image_url': product[4]
    }), 200

# ==================== CART & ORDER ROUTES ====================

@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.get_json()
    
    if not data or not data.get('items') or not data.get('customer_email'):
        return jsonify({'message': 'Missing required fields'}), 400
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Calculate total
        total = 0
        for item in data['items']:
            cursor.execute('SELECT price FROM products WHERE id = ?', (item['product_id'],))
            product = cursor.fetchone()
            if product:
                total += product[0] * item['quantity']
        
        # Create order
        cursor.execute(
            '''INSERT INTO orders (customer_email, customer_name, total_amount, status, created_at)
               VALUES (?, ?, ?, ?, ?)''',
            (
                data['customer_email'],
                data.get('customer_name', 'Guest'),
                total,
                'pending',
                datetime.now().isoformat()
            )
        )
        db.commit()
        order_id = cursor.lastrowid
        
        # Add order items
        for item in data['items']:
            cursor.execute(
                'INSERT INTO order_items (order_id, product_id, quantity) VALUES (?, ?, ?)',
                (order_id, item['product_id'], item['quantity'])
            )
        db.commit()
        
        return jsonify({'message': 'Order created', 'order_id': order_id}), 201
    except Exception as e:
        db.rollback()
        return jsonify({'message': str(e)}), 500

@app.route('/api/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT id, customer_email, customer_name, total_amount, status, created_at FROM orders WHERE id = ?', (order_id,))
    order = cursor.fetchone()
    
    if not order:
        return jsonify({'message': 'Order not found'}), 404
    
    cursor.execute('SELECT product_id, quantity FROM order_items WHERE order_id = ?', (order_id,))
    items = cursor.fetchall()
    
    order_items = []
    for item in items:
        cursor.execute('SELECT name, price FROM products WHERE id = ?', (item[0],))
        product = cursor.fetchone()
        order_items.append({
            'product_id': item[0],
            'product_name': product[0] if product else 'Unknown',
            'quantity': item[1],
            'price': product[1] if product else 0
        })
    
    return jsonify({
        'id': order[0],
        'customer_email': order[1],
        'customer_name': order[2],
        'total_amount': order[3],
        'status': order[4],
        'created_at': order[5],
        'items': order_items
    }), 200

# ==================== IMAGE SERVING ====================

@app.route('/uploads/<filename>', methods=['GET'])
def serve_image(filename):
    from flask import send_from_directory
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except:
        return jsonify({'message': 'Image not found'}), 404

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
