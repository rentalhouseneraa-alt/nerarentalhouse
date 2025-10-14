from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    full_name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship('Order', backref='staff', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    address = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship('Order', backref='customer', lazy=True)

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(200), nullable=False)
    product_details = db.Column(db.Text)
    price = db.Column(db.Float, default=0.0)
    quantity = db.Column(db.Integer, default=1)
    photos_json = db.Column(db.Text)  # store JSON list of filenames
    delivery_datetime = db.Column(db.DateTime)
    return_datetime = db.Column(db.DateTime)
    amount_advance = db.Column(db.Float, default=0.0)
    amount_pending = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(30), default='pending')  # pending, approved, rejected, completed, canceled
    staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def set_photos(self, filenames):
        self.photos_json = json.dumps(filenames)

    def get_photos(self):
        try:
            return json.loads(self.photos_json) if self.photos_json else []
        except:
            return []
