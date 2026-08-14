# app.py
# This is the main Flask application file.
# It sets up routes, handles user login/logout,
# and connects everything together.

import os
import qrcode                              # For generating QR code images
from flask import (Flask, render_template, redirect,
                   url_for, request, flash, abort)
from flask_login import (LoginManager, login_user, logout_user,
                          login_required, current_user)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Import our database models
from models import db, User, Item, ItemLocation, FoundMessage

# ─────────────────────────────────────────
#  APP CONFIGURATION
# ─────────────────────────────────────────
app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key-before-deploying"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"  # local SQLite file
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Connect SQLAlchemy to the Flask app
db.init_app(app)

# Set up Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = "login"         # redirect here if not logged in
login_manager.login_message_category = "info"

# Folder where QR code images are saved
QR_FOLDER = os.path.join("static", "qr_codes")
os.makedirs(QR_FOLDER, exist_ok=True)      # create folder if it doesn't exist


# ─────────────────────────────────────────
#  USER LOADER  (required by Flask-Login)
# ─────────────────────────────────────────
@login_manager.user_loader
def load_user(user_id):
    """Tell Flask-Login how to find a user by their ID (stored in session)."""
    return User.query.get(int(user_id))


# ─────────────────────────────────────────
#  QR CODE GENERATION FUNCTION
# ─────────────────────────────────────────
def generate_qr_code(qr_id: str) -> str:
    """
    Generate a QR code image for the given qr_id string.

    Args:
        qr_id: The unique identifier string, e.g. "ITEM001"

    Returns:
        The file path to the saved QR code image.
    """
    filename   = f"{qr_id.lower()}.png"         # e.g. "item001.png"
    filepath   = os.path.join(QR_FOLDER, filename)

    # Create a QR code object with some styling
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_id)   # The QR code encodes the item's qr_id
    qr.make(fit=True)

    # Generate the image and save it
    img = qr.make_image(fill_color="#1a1a2e", back_color="white")
    img.save(filepath)

    return filepath


# ─────────────────────────────────────────
#  HELPER: Auto-generate the next QR ID
# ─────────────────────────────────────────
def next_qr_id() -> str:
    """
    Look at the highest existing item ID and produce the next QR ID.
    Example: if 3 items exist → returns "ITEM004"
    """
    last_item = Item.query.order_by(Item.id.desc()).first()
    next_num  = (last_item.id + 1) if last_item else 1
    return f"ITEM{next_num:03d}"    # zero-padded to 3 digits


# ─────────────────────────────────────────
#  ROUTE: Home → redirect to dashboard
# ─────────────────────────────────────────
@app.route("/")
def index():
    return redirect(url_for("dashboard"))


# ─────────────────────────────────────────
#  ROUTE: Register
# ─────────────────────────────────────────
@app.route("/register", methods=["GET", "POST"])
def register():
    """Allow a new user to create an account."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        # Basic validation
        if not username or not password:
            flash("Username and password are required.", "danger")
            return render_template("register.html")

        # Check if username is already taken
        existing = User.query.filter_by(username=username).first()
        if existing:
            flash("Username already taken. Please choose another.", "warning")
            return render_template("register.html")

        # Hash the password before storing (never store plain text!)
        hashed_pw = generate_password_hash(password)
        new_user  = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()

        flash("Account created! You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


# ─────────────────────────────────────────
#  ROUTE: Login
# ─────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    """Let existing users log in."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(username=username).first()

        # Check username + password
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash(f"Welcome back, {user.username}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html")


# ─────────────────────────────────────────
#  ROUTE: Logout
# ─────────────────────────────────────────
@app.route("/logout")
@login_required
def logout():
    """Log the current user out and redirect to login."""
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ─────────────────────────────────────────
#  ROUTE: Dashboard
# ─────────────────────────────────────────
@app.route("/dashboard")
@login_required
def dashboard():
    """
    Show all items belonging to the logged-in user.
    For each item, also fetch the most recent location.
    """
    items = Item.query.filter_by(user_id=current_user.id).all()

    # Build a dict: item.id → latest ItemLocation (or None)
    latest_locations = {}
    for item in items:
        last_loc = (ItemLocation.query
                    .filter_by(item_id=item.id)
                    .order_by(ItemLocation.time.desc())
                    .first())
        latest_locations[item.id] = last_loc

    return render_template("dashboard.html",
                           items=items,
                           latest_locations=latest_locations)


# ─────────────────────────────────────────
#  ROUTE: Add Item
# ─────────────────────────────────────────
@app.route("/add_item", methods=["GET", "POST"])
@login_required
def add_item():
    """Let the user register a new item and auto-generate its QR code."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Item name cannot be empty.", "danger")
            return render_template("add_item.html")

        qr_id    = next_qr_id()          # e.g. "ITEM004"
        new_item = Item(name=name, qr_id=qr_id, user_id=current_user.id)
        db.session.add(new_item)
        db.session.commit()

        # Generate and save the QR code image
        generate_qr_code(qr_id)

        flash(f'Item "{name}" added with QR ID: {qr_id}', "success")
        return redirect(url_for("dashboard"))

    return render_template("add_item.html")


# ─────────────────────────────────────────
#  ROUTE: Delete Item
# ─────────────────────────────────────────
@app.route("/delete_item/<int:item_id>", methods=["POST"])
@login_required
def delete_item(item_id):
    """Delete an item (only if it belongs to the current user)."""
    item = Item.query.get_or_404(item_id)

    # Security check: make sure the item belongs to the logged-in user
    if item.user_id != current_user.id:
        abort(403)

    # Remove QR code image file if it exists
    img_path = os.path.join(QR_FOLDER, f"{item.qr_id.lower()}.png")
    if os.path.exists(img_path):
        os.remove(img_path)

    db.session.delete(item)
    db.session.commit()
    flash(f'Item "{item.name}" deleted.', "info")
    return redirect(url_for("dashboard"))


# ─────────────────────────────────────────
#  ROUTE: Update Location
# ─────────────────────────────────────────
@app.route("/update_location/<int:item_id>", methods=["POST"])
@login_required
def update_location(item_id):
    """Record a new location for the specified item."""
    item = Item.query.get_or_404(item_id)

    if item.user_id != current_user.id:
        abort(403)

    location_text = request.form.get("location", "").strip()
    if not location_text:
        flash("Location cannot be empty.", "danger")
        return redirect(url_for("item_history", item_id=item_id))

    new_loc = ItemLocation(item_id=item.id, location=location_text)
    db.session.add(new_loc)
    db.session.commit()

    flash(f"Location updated to: {location_text}", "success")
    return redirect(url_for("item_history", item_id=item_id))


# ─────────────────────────────────────────
#  ROUTE: Item History
# ─────────────────────────────────────────
@app.route("/item/<int:item_id>")
@login_required
def item_history(item_id):
    """Show the full location history for one item."""
    item = Item.query.get_or_404(item_id)

    if item.user_id != current_user.id:
        abort(403)

    # Get all locations for this item, newest first
    locations = (ItemLocation.query
                 .filter_by(item_id=item.id)
                 .order_by(ItemLocation.time.desc())
                 .all())

    # Check if there are any "found" messages for this item
    found_messages = (FoundMessage.query
                      .filter_by(qr_id=item.qr_id)
                      .order_by(FoundMessage.time.desc())
                      .all())

    return render_template("item_history.html",
                           item=item,
                           locations=locations,
                           found_messages=found_messages)


# ─────────────────────────────────────────
#  ROUTE: Found Item (public — no login)
# ─────────────────────────────────────────
@app.route("/found/<qr_id>", methods=["GET", "POST"])
def found_item(qr_id):
    """
    Public page shown when someone scans a QR code.
    They can send a message to the owner.
    """
    item = Item.query.filter_by(qr_id=qr_id.upper()).first_or_404()

    if request.method == "POST":
        msg_text = request.form.get("message", "").strip()
        if msg_text:
            new_msg = FoundMessage(qr_id=item.qr_id, message=msg_text)
            db.session.add(new_msg)
            db.session.commit()
            flash("Your message has been sent to the owner!", "success")
        else:
            flash("Please write a message before sending.", "warning")

    return render_template("found_item.html", item=item)


# ─────────────────────────────────────────
#  DATABASE INITIALIZATION
# ─────────────────────────────────────────
def init_db():
    """Create all database tables if they don't already exist."""
    with app.app_context():
        db.create_all()
        print("✅ Database tables created successfully.")


# ─────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────
if __name__ == "__main__":
    init_db()          # Create tables on first run
    app.run(debug=True)
