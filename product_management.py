import mysql.connector

# ---------- DATABASE CONNECTION ----------
def connect():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="baha1528",  #Replace with your MySQL password
        database="product_db"
    )

# ---------- REGISTER NEW USER ----------
def register_user(cursor, conn):
    print("\nRegister New User")
    username = input("Enter new username: ").strip()
    password = input("Enter password: ").strip()
    role = ""

    while role not in ['user', 'admin']:
        role = input("Enter role ('user' or 'admin'): ").strip().lower()
        if role not in ['user', 'admin']:
            print("Role must be 'user' or 'admin'.")

    # Check if username exists
    cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
    if cursor.fetchone():
        print("Username already exists. Try a different one.")
        return

    cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (username, password, role))
    conn.commit()
    print(f"User '{username}' registered successfully with role '{role}'!")

# ---------- LOGIN ----------
def login(cursor):
    print("\nLogin")
    username = input("Username: ").strip()
    password = input("Password: ").strip()

    cursor.execute("SELECT user_id, role FROM users WHERE username = %s AND password = %s", (username, password))
    user = cursor.fetchone()

    if user:
        user_id, role = user
        print(f"Login successful! Welcome, {username} ({role}).")
        return user_id, role
    else:
        print("Invalid username or password.")
        return None, None


# ---------- ADD NEW PRODUCT (ADMIN ONLY) ----------
def add_product(cursor, conn):
    try:
        name = input("Enter product name: ").strip()
        if not name:
            print("Product name cannot be empty.")
            return

        description = input("Enter product description: ")
        category = input("Enter product category: ")

        price_input = input("Enter product price: ").strip()
        if not price_input:
            print("Product price cannot be empty.")
            return

        price = float(price_input)
        if price < 0:
            print("Price must be a non-negative number.")
            return

        query = """
        INSERT INTO products (name, description, category, price)
        VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (name, description, category, price))
        conn.commit()
        print("Product added successfully!")

    except ValueError:
        print("Invalid price. Please enter a numeric value.")
    except Exception as e:
        print(f"An error occurred: {e}")

# ---------- LIST ALL PRODUCTS ----------
def list_products(cursor):
    cursor.execute("SELECT * FROM products")
    rows = cursor.fetchall()

    if rows:
        print("\nProduct List:")
        print("-" * 80)
        for row in rows:
            print(f"ID: {row[0]}, Name: {row[1]}, Category: {row[3]}, Price: ₹{row[4]}, Discount: {row[5]}%, Added: {row[6]}")
        print("-" * 80)
    else:
        print("No products found.")

# ---------- UPDATE PRODUCT PRICE (ADMIN ONLY) ----------
def update_price(cursor, conn):
    pid = int(input("Enter Product ID to update price: "))
    new_price = float(input("Enter new price: "))

    cursor.execute("UPDATE products SET price = %s WHERE product_id = %s", (new_price, pid))
    conn.commit()

    if cursor.rowcount == 0:
        print("Product not found.")
    else:
        print("Price updated successfully!")

# ---------- APPLY DISCOUNT TO ALL PRODUCTS (ADMIN ONLY) ----------
def apply_discount(cursor, conn):
    percent = float(input("Enter discount percentage (e.g., 10 for 10%): "))

    cursor.execute("""
    UPDATE products
    SET discount = %s,
        price = price - (price * %s / 100)
    """, (percent, percent))
    conn.commit()

    print(f"Discount of {percent}% applied to all products!")

# ---------- DELETE PRODUCT (ADMIN ONLY) ----------
def delete_product(cursor, conn):
    pid = int(input("Enter Product ID to delete: "))

    # Delete from cart first to avoid foreign key constraint error
    cursor.execute("DELETE FROM cart WHERE product_id = %s", (pid,))

    # Then delete from products
    cursor.execute("DELETE FROM products WHERE product_id = %s", (pid,))
    conn.commit()

    if cursor.rowcount == 0:
        print("Product not found.")
    else:
        print("Product deleted successfully!")

# ---------- USER: ADD TO CART ----------
def add_to_cart(cursor, conn, user_id):
    product_id = int(input("Enter Product ID to add to cart: "))
    quantity = int(input("Enter quantity: "))

    # Check if product exists
    cursor.execute("SELECT price FROM products WHERE product_id = %s", (product_id,))
    product = cursor.fetchone()
    if not product:
        print("Product not found.")
        return

    # Check if product already in cart, update quantity
    cursor.execute("SELECT quantity FROM cart WHERE user_id = %s AND product_id = %s", (user_id, product_id))
    existing = cursor.fetchone()

    if existing:
        new_qty = existing[0] + quantity
        cursor.execute("UPDATE cart SET quantity = %s WHERE user_id = %s AND product_id = %s", (new_qty, user_id, product_id))
    else:
        cursor.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (%s, %s, %s)", (user_id, product_id, quantity))

    conn.commit()
    print("Added to cart!")

# ---------- USER: VIEW CART ----------
def view_cart(cursor, user_id):
    cursor.execute("""
        SELECT p.name, p.price, c.quantity, (p.price * c.quantity) AS total
        FROM cart c
        JOIN products p ON c.product_id = p.product_id
        WHERE c.user_id = %s
    """, (user_id,))
    items = cursor.fetchall()

    if not items:
        print("Your cart is empty.")
        return

    print("\nYour Cart:")
    print("-" * 40)
    total = 0
    for name, price, qty, total_item in items:
        print(f"{name} — ₹{price} × {qty} = ₹{total_item}")
        total += total_item
    print("-" * 40)
    print(f"Total: ₹{total}")

# ---------- USER: CHECKOUT CART ----------
def checkout_cart(cursor, conn, user_id):
    cursor.execute("""
        SELECT p.name, p.price, c.quantity, (p.price * c.quantity) AS total
        FROM cart c
        JOIN products p ON c.product_id = p.product_id
        WHERE c.user_id = %s
    """, (user_id,))
    items = cursor.fetchall()

    if not items:
        print("Your cart is empty. Nothing to checkout.")
        return

    total = sum(item[3] for item in items)
    print("\nCheckout Summary:")
    for name, price, qty, total_item in items:
        print(f"{name} — ₹{price} × {qty} = ₹{total_item}")
    print(f"Total amount payable: ₹{total}")

    confirm = input("Confirm purchase? (yes/no): ").strip().lower()
    if confirm == "yes":
        cursor.execute("DELETE FROM cart WHERE user_id = %s", (user_id,))
        conn.commit()
        print("Purchase confirmed! Your cart is now empty.")
    else:
        print("Checkout cancelled.")

# ---------- USER: EXPORT CART TO FILE ----------
def export_cart_to_file(cursor, user_id):
    cursor.execute("""
    SELECT p.name, p.price, c.quantity
    FROM cart c
    JOIN products p ON c.product_id = p.product_id
    WHERE c.user_id = %s
    """, (user_id,))
    rows = cursor.fetchall()

    if not rows:
        print("Your cart is empty, nothing to export.")
        return

    filename = f"user_{user_id}_cart.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("Your Cart:\n")
        total = 0
        for name, price, qty in rows:
            total_item = price * qty
            total += total_item
            f.write(f"{name} — ₹{price} × {qty} = ₹{total_item}\n")
        f.write(f"\nTotal Cart Value: ₹{total}\n")
    print(f"Cart exported successfully to '{filename}'!")


# ---------- ADMIN: VIEW ALL USERS AND THEIR CARTS ----------
def view_all_users_and_carts(cursor):
    cursor.execute("SELECT user_id, username, role FROM users")
    users = cursor.fetchall()

    for user_id, username, role in users:
        print(f"\nUser: {username} (Role: {role})")
        cursor.execute("""
            SELECT p.name, p.price, c.quantity, (p.price * c.quantity) AS total
            FROM cart c
            JOIN products p ON c.product_id = p.product_id
            WHERE c.user_id = %s
        """, (user_id,))
        items = cursor.fetchall()
        if not items:
            print("  Cart is empty.")
        else:
            for name, price, qty, total_item in items:
                print(f"  {name} — ₹{price} × {qty} = ₹{total_item}")

# ---------- USER MENU ----------
def user_menu(cursor, conn, user_id):
    while True:
        print("\nUser Menu")
        print("1. View Products")
        print("2. Add to Cart")
        print("3. View Cart")
        print("4. Checkout Cart")
        print("5. Export Cart to File")
        print("6. Logout")

        choice = input("Choose option: ")
        if choice == '1':
            list_products(cursor)
        elif choice == '2':
            add_to_cart(cursor, conn, user_id)
        elif choice == '3':
            view_cart(cursor, user_id)
        elif choice == '4':
            checkout_cart(cursor, conn, user_id)
        elif choice == '5':
            export_cart_to_file(cursor, user_id)
        elif choice == '6':
            print("Logging out...")
            break
        else:
            print("Invalid option.")

# ---------- ADMIN MENU ----------
def admin_menu(cursor, conn):
    while True:
        print("\n  Admin Menu")
        print("1. Add Product")
        print("2. List Products")
        print("3. Update Product Price")
        print("4. Apply Discount to All")
        print("5. Delete Product")
        print("6. View All Users and Carts")
        print("7. Logout")

        choice = input("Choose option: ")
        if choice == '1':
            add_product(cursor, conn)
        elif choice == '2':
            list_products(cursor)
        elif choice == '3':
            update_price(cursor, conn)
        elif choice == '4':
            apply_discount(cursor, conn)
        elif choice == '5':
            delete_product(cursor, conn)
        elif choice == '6':
            view_all_users_and_carts(cursor)
        elif choice == '7':
            print("👋 Logging out...")
            break
        else:
            print("Invalid option.")

# ---------- START MENU ----------
def start_menu():
    conn = connect()
    cursor = conn.cursor()

    while True:
        print("\n=== Welcome to the Product Management App ===")
        print("1. Register")
        print("2. Login")
        print("3. Exit")

        choice = input("Choose an option: ")

        if choice == '1':
            register_user(cursor, conn)
        elif choice == '2':
            user_id, role = login(cursor)
            if user_id:
                if role == 'admin':
                    admin_menu(cursor, conn)
                else:
                    user_menu(cursor, conn, user_id)
        elif choice == '3':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please select 1, 2, or 3.")

    cursor.close()
    conn.close()

# ---------- RUN THE APP ----------
if __name__ == "__main__":
    start_menu()
