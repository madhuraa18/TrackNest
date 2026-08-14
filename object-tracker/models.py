# models.py
# This file defines the database structure (tables) for our app.
# We use SQLAlchemy to map Python classes to database tables.

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# Create the SQLAlchemy database object.
# This will be imported and used in app.py
db = SQLAlchemy()


# ─────────────────────────────────────────
#  TABLE 1: User
#  Stores login credentials for each user.
# ─────────────────────────────────────────
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)   # hashed password

    # One user can have many items (one-to-many relationship)
    items = db.relationship("Item", backref="owner", lazy=True)

    def __repr__(self):
        return f"<User {self.username}>"


# ─────────────────────────────────────────
#  TABLE 2: Item
#  Stores each object the user wants to track.
# ─────────────────────────────────────────
class Item(db.Model):
    __tablename__ = "items"

    id      = db.Column(db.Integer, primary_key=True)
    name    = db.Column(db.String(100), nullable=False)
    qr_id   = db.Column(db.String(20), unique=True, nullable=False)  # e.g. "ITEM001"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # One item can have many location records
    locations = db.relationship("ItemLocation", backref="item", lazy=True,
                                cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Item {self.name} ({self.qr_id})>"


# ─────────────────────────────────────────
#  TABLE 3: ItemLocation
#  Every time the user records where an item is,
#  a new row is added here with a timestamp.
# ─────────────────────────────────────────
class ItemLocation(db.Model):
    __tablename__ = "item_locations"

    id       = db.Column(db.Integer, primary_key=True)
    item_id  = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False)
    location = db.Column(db.String(200), nullable=False)  # e.g. "Study Table"
    time     = db.Column(db.DateTime, default=datetime.utcnow)  # auto timestamp

    def __repr__(self):
        return f"<Location {self.location} @ {self.time}>"


# ─────────────────────────────────────────
#  TABLE 4: FoundMessage
#  When someone scans a lost item's QR code,
#  they can leave a message for the owner.
# ─────────────────────────────────────────
class FoundMessage(db.Model):
    __tablename__ = "found_messages"

    id      = db.Column(db.Integer, primary_key=True)
    qr_id   = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    time    = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<FoundMessage for {self.qr_id}>"
