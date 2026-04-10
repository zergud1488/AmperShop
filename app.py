import json
import os
import re
import sqlite3
import uuid
from collections import defaultdict
from decimal import Decimal
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

import phonenumbers
import requests
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from email_validator import EmailNotValidError, validate_email
from flask import (
    Flask,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from PIL import Image
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
INSTANCE_DIR = BASE_DIR / "instance"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
COUNTRY_PHONE_CODES = [
    {"code": "+380", "country": "Україна", "region": "UA"},
    {"code": "+48", "country": "Польща", "region": "PL"},
    {"code": "+49", "country": "Німеччина", "region": "DE"},
    {"code": "+44", "country": "Велика Британія", "region": "GB"},
    {"code": "+1", "country": "США / Канада", "region": "US"},
    {"code": "+373", "country": "Молдова", "region": "MD"},
    {"code": "+40", "country": "Румунія", "region": "RO"},
]


CONTENT_FIELDS = [
    {"key": "home_hero_eyebrow", "label": "Головна • надпис над заголовком", "default": "AmperShop Signature Store", "type": "text"},
    {"key": "home_hero_badge_1", "label": "Головна • badge 1", "default": "Преміальна вітрина", "type": "text"},
    {"key": "home_hero_badge_2", "label": "Головна • badge 2", "default": "Швидка доставка по Україні", "type": "text"},
    {"key": "home_hero_badge_3", "label": "Головна • badge 3", "default": "Вигідні пропозиції щодня", "type": "text"},
    {"key": "home_hero_title", "label": "Головна • головний заголовок", "default": "Товари для дому, техніки й щоденного комфорту — з професійною подачею, швидким вибором і зручним оформленням.", "type": "textarea"},
    {"key": "home_hero_subtitle", "label": "Головна • підзаголовок", "default": "AmperShop поєднує чистий преміальний дизайн, продуману навігацію та сучасний вибір товарів для дому, техніки, аксесуарів і щоденного комфорту.", "type": "textarea"},
    {"key": "home_primary_button_text", "label": "Головна • текст головної кнопки", "default": "Відкрити каталог", "type": "text"},
    {"key": "home_primary_button_url", "label": "Головна • посилання головної кнопки", "default": "/catalog", "type": "text"},
    {"key": "home_secondary_button_text", "label": "Головна • текст другої кнопки", "default": "Переглянути хіти продажу", "type": "text"},
    {"key": "home_secondary_button_url", "label": "Головна • посилання другої кнопки", "default": "/#featured-products", "type": "text"},
    {"key": "home_metric_1_value", "label": "Головна • метрика 1 значення", "default": "", "type": "text"},
    {"key": "home_metric_1_label", "label": "Головна • метрика 1 підпис", "default": "актуальних позицій", "type": "text"},
    {"key": "home_metric_2_value", "label": "Головна • метрика 2 значення", "default": "", "type": "text"},
    {"key": "home_metric_2_label", "label": "Головна • метрика 2 підпис", "default": "категорій", "type": "text"},
    {"key": "home_metric_3_value", "label": "Головна • метрика 3 значення", "default": "24/7", "type": "text"},
    {"key": "home_metric_3_label", "label": "Головна • метрика 3 підпис", "default": "онлайн-замовлення", "type": "text"},
    {"key": "home_side_kicker", "label": "Головна • правий блок заголовок", "default": "Сервіс, що працює на продаж", "type": "text"},
    {"key": "home_side_features", "label": "Головна • правий список переваг (кожен рядок з нового рядка)", "default": "Велика преміальна вітрина з чіткою логікою каталогу\nПомітні ТОП товари, знижки та вигідні добірки\nШвидкий пошук, фільтри й комфортний шлях до покупки\nЗручне оформлення замовлення з популярними службами доставки\nСтабільна мобільна версія для покупок з будь-якого пристрою\nКабінет покупця з історією замовлень та обраним", "type": "textarea"},
    {"key": "home_strip_1_eyebrow", "label": "Головна • картка 1 надпис", "default": "Преміальна подача", "type": "text"},
    {"key": "home_strip_1_title", "label": "Головна • картка 1 заголовок", "default": "Стильна головна сторінка, що продає з першого екрану", "type": "text"},
    {"key": "home_strip_1_text", "label": "Головна • картка 1 текст", "default": "Баланс повітря, типографіки та акцентів створює відчуття дорогого й надійного магазину.", "type": "textarea"},
    {"key": "home_strip_1_order", "label": "Головна • картка 1 позиція", "default": "1", "type": "text"},
    {"key": "home_strip_2_eyebrow", "label": "Головна • картка 2 надпис", "default": "Продуманий UX", "type": "text"},
    {"key": "home_strip_2_title", "label": "Головна • картка 2 заголовок", "default": "Покупець швидко знаходить потрібне й легко оформлює замовлення", "type": "text"},
    {"key": "home_strip_2_text", "label": "Головна • картка 2 текст", "default": "Фільтри, обране, акційні позначки та чисті сторінки товарів працюють на конверсію.", "type": "textarea"},
    {"key": "home_strip_2_order", "label": "Головна • картка 2 позиція", "default": "2", "type": "text"},
    {"key": "home_strip_3_eyebrow", "label": "Головна • картка 3 надпис", "default": "Рівень бренду", "type": "text"},
    {"key": "home_strip_3_title", "label": "Головна • картка 3 заголовок", "default": "Інтерфейс, який виглядає як готовий професійний e-commerce", "type": "text"},
    {"key": "home_strip_3_text", "label": "Головна • картка 3 текст", "default": "Кожен блок сайту підсилює довіру та допомагає перетворювати трафік на замовлення.", "type": "textarea"},
    {"key": "home_strip_3_order", "label": "Головна • картка 3 позиція", "default": "3", "type": "text"},
    {"key": "catalog_eyebrow", "label": "Каталог • надпис", "default": "Каталог", "type": "text"},
    {"key": "catalog_title", "label": "Каталог • заголовок", "default": "Каталог товарів AmperShop", "type": "text"},
    {"key": "catalog_subtitle", "label": "Каталог • підзаголовок", "default": "Сучасна вітрина з продуманими фільтрами, швидким пошуком і товарами, які приємно переглядати та легко замовляти.", "type": "textarea"},
    {"key": "checkout_eyebrow", "label": "Оформлення • надпис", "default": "Оформлення", "type": "text"},
    {"key": "checkout_title", "label": "Оформлення • заголовок", "default": "Дані для доставки", "type": "text"},
    {"key": "checkout_subtitle", "label": "Оформлення • підзаголовок", "default": "Заповніть контактні дані для швидкого підтвердження замовлення та комфортної доставки обраних товарів.", "type": "textarea"},
    {"key": "footer_title", "label": "Футер • заголовок", "default": "AmperShop", "type": "text"},
    {"key": "footer_text", "label": "Футер • опис", "default": "AmperShop — сучасний магазин із преміальною подачею, сильним візуальним стилем і зручним процесом покупки для клієнтів, які цінують комфорт та якість сервісу.", "type": "textarea"},
    {"key": "footer_help_title", "label": "Футер • заголовок форми", "default": "Потрібна допомога з вибором?", "type": "text"},
    {"key": "footer_help_button", "label": "Футер • кнопка форми", "default": "Отримати консультацію", "type": "text"},
    {"key": "home_trust_eyebrow", "label": "Головна • нижній блок надпис", "default": "AmperShop Experience", "type": "text"},
    {"key": "home_trust_title", "label": "Головна • нижній блок заголовок", "default": "Онлайн-магазин, де кожна деталь працює на довіру та продаж", "type": "text"},
    {"key": "home_trust_text", "label": "Головна • нижній блок текст", "default": "Чистий інтерфейс, сильна візуальна подача, зрозумілі ціни, акції та сучасний процес оформлення формують відчуття професійного магазину преміального рівня.", "type": "textarea"},
    {"key": "home_trust_button_text", "label": "Головна • нижній блок кнопка текст", "default": "Почати покупки", "type": "text"},
    {"key": "home_trust_button_url", "label": "Головна • нижній блок кнопка посилання", "default": "/catalog", "type": "text"},
]

load_dotenv(BASE_DIR / ".env")

INSTANCE_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

db = SQLAlchemy()
login_manager = LoginManager()
oauth = OAuth()
login_manager.login_view = "account_login"


class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(120), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(180), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    full_name = db.Column(db.String(180), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    google_id = db.Column(db.String(255), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    orders = db.relationship("Order", backref="user", lazy=True)
    reviews = db.relationship("ProductReview", backref="user", lazy=True)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str):
        return bool(self.password_hash) and check_password_hash(self.password_hash, password)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    products = db.relationship("Product", backref="category", lazy=True)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(220), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False)
    short_description = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, nullable=True)
    specifications = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    old_price = db.Column(db.Float, nullable=True)
    discount_enabled = db.Column(db.Boolean, default=False)
    is_top = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    stock_status = db.Column(db.String(50), default="В наявності")
    supplier_chat_id = db.Column(db.String(120), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    images = db.relationship("ProductImage", backref="product", lazy=True, cascade="all, delete-orphan")
    order_items = db.relationship("OrderItem", backref="product", lazy=True)
    reviews = db.relationship("ProductReview", backref="product", lazy=True, cascade="all, delete-orphan")

    @property
    def current_price(self):
        if self.discount_enabled and self.old_price and self.old_price > self.price:
            return self.price
        return self.price


class ProductImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_path = db.Column(db.String(255), nullable=False)
    alt_text = db.Column(db.String(255), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    customer_name = db.Column(db.String(180), nullable=False)
    customer_surname = db.Column(db.String(180), nullable=False)
    phone_country_code = db.Column(db.String(10), nullable=True)
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(180), nullable=True)
    city = db.Column(db.String(120), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    delivery_method = db.Column(db.String(120), nullable=False)
    payment_method = db.Column(db.String(120), nullable=False)
    carrier_service = db.Column(db.String(120), nullable=True)
    warehouse_number = db.Column(db.String(120), nullable=True)
    comment = db.Column(db.Text, nullable=True)
    promo_code = db.Column(db.String(50), nullable=True)
    discount_amount = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(80), default="Нове замовлення")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship("OrderItem", backref="order", lazy=True, cascade="all, delete-orphan")


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    title = db.Column(db.String(220), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, default=1)
    supplier_chat_id = db.Column(db.String(120), nullable=True)


class ProductReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    author_name = db.Column(db.String(180), nullable=False)
    email = db.Column(db.String(180), nullable=True)
    rating = db.Column(db.Integer, nullable=False, default=5)
    comment = db.Column(db.Text, nullable=False)
    is_approved = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SiteVisit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(255), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=True)
    ip_address = db.Column(db.String(100), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    referer = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(180), nullable=False)
    phone = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(180), nullable=True)
    message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class NotificationLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    channel = db.Column(db.String(50), nullable=False)
    target = db.Column(db.String(120), nullable=True)
    success = db.Column(db.Boolean, default=False)
    message = db.Column(db.Text, nullable=True)
    response_text = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PromoCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    discount_percent = db.Column(db.Float, nullable=True)
    discount_amount = db.Column(db.Float, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    usage_limit = db.Column(db.Integer, nullable=True)
    used_count = db.Column(db.Integer, default=0)
    min_order_amount = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def calculate_discount(self, total):
        if not self.is_active:
            return 0
        if self.usage_limit and self.used_count >= self.usage_limit:
            return 0
        if total < (self.min_order_amount or 0):
            return 0
        if self.discount_percent:
            return round(total * (self.discount_percent / 100.0), 2)
        if self.discount_amount:
            return min(total, self.discount_amount)
        return 0


class WishlistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{INSTANCE_DIR / 'ampershop.db'}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
    db.init_app(app)
    login_manager.init_app(app)
    oauth.init_app(app)

    google_client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    if google_client_id and google_client_secret:
        oauth.register(
            name="google",
            client_id=google_client_id,
            client_secret=google_client_secret,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )

    with app.app_context():
        db.create_all()
        ensure_columns()
        seed_admin()
        seed_defaults()

    @app.context_processor
    def inject_globals():
        wishlist_count = 0
        if current_user.is_authenticated and not current_user.is_admin:
            wishlist_count = WishlistItem.query.filter_by(user_id=current_user.id).count()
        return {
            "cart_count": sum(session.get("cart", {}).values()) if session.get("cart") else 0,
            "wishlist_count": wishlist_count,
            "site_name": "AmperShop",
            "domain_name": get_setting("domain_name", os.getenv("APP_DOMAIN", "localhost:5000")),
            "top_categories": Category.query.order_by(Category.name.asc()).all(),
            "current_year": datetime.utcnow().year,
            "phone_country_codes": COUNTRY_PHONE_CODES,
            "cms": get_setting,
            "cms_lines": cms_lines,
            "cms_int": cms_int,
        }

    @app.before_request
    def before_request_handler():
        g.now = datetime.utcnow()
        if request.endpoint and request.endpoint.startswith("static"):
            return
        if request.path.startswith("/admin/api"):
            return
        product_id = None
        if request.view_args and request.view_args.get("slug"):
            product = Product.query.filter_by(slug=request.view_args.get("slug")).first()
            if product:
                product_id = product.id
        visit = SiteVisit(
            path=request.path,
            product_id=product_id,
            ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
            user_agent=(request.user_agent.string or "")[:255],
            referer=(request.referrer or "")[:255],
        )
        db.session.add(visit)
        db.session.commit()

    @app.route("/")
    def home():
        top_products = Product.query.filter_by(is_active=True, is_top=True).order_by(Product.created_at.desc()).limit(8).all()
        fresh_products = Product.query.filter_by(is_active=True).order_by(Product.created_at.desc()).limit(12).all()
        categories = Category.query.order_by(Category.name.asc()).all()
        return render_template("home.html", top_products=top_products, fresh_products=fresh_products, categories=categories)

    @app.route("/manifest.json")
    def manifest():
        return jsonify({
            "name": "AmperShop",
            "short_name": "AmperShop",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#ffffff",
            "theme_color": "#111111",
            "icons": [],
        })

    @app.route("/catalog")
    def catalog():
        category_slug = request.args.get("category", "").strip()
        search = request.args.get("q", "").strip()
        sort = request.args.get("sort", "new")
        price_min = request.args.get("price_min", "").strip()
        price_max = request.args.get("price_max", "").strip()
        only_discount = request.args.get("discount") == "1"

        query = Product.query.filter_by(is_active=True)
        if category_slug:
            category = Category.query.filter_by(slug=category_slug).first_or_404()
            query = query.filter_by(category_id=category.id)
        if search:
            like = f"%{search}%"
            query = query.filter(db.or_(Product.title.ilike(like), Product.short_description.ilike(like), Product.description.ilike(like)))
        if price_min:
            try:
                query = query.filter(Product.price >= float(price_min))
            except ValueError:
                pass
        if price_max:
            try:
                query = query.filter(Product.price <= float(price_max))
            except ValueError:
                pass
        if only_discount:
            query = query.filter(Product.discount_enabled == True, Product.old_price.isnot(None), Product.old_price > Product.price)

        sort_map = {
            "price_asc": Product.price.asc(),
            "price_desc": Product.price.desc(),
            "name": Product.title.asc(),
            "popular": Product.is_top.desc(),
            "new": Product.created_at.desc(),
        }
        products = query.order_by(sort_map.get(sort, Product.created_at.desc())).all()
        return render_template("catalog.html", products=products, selected_category=category_slug, search=search, sort=sort, price_min=price_min, price_max=price_max, only_discount=only_discount)

    @app.route("/product/<slug>")
    def product_detail(slug):
        product = Product.query.filter_by(slug=slug, is_active=True).first_or_404()
        related = Product.query.filter(
            Product.category_id == product.category_id,
            Product.id != product.id,
            Product.is_active == True,
        ).limit(4).all()
        reviews = ProductReview.query.filter_by(product_id=product.id, is_approved=True).order_by(ProductReview.created_at.desc()).all()
        rating_avg = None
        if reviews:
            rating_avg = round(sum(review.rating for review in reviews) / len(reviews), 1)
        return render_template(
            "product_detail.html",
            product=product,
            related=related,
            reviews=reviews,
            rating_avg=rating_avg,
        )

    @app.post("/cart/add/<int:product_id>")
    def cart_add(product_id):
        product = Product.query.get_or_404(product_id)
        cart = session.get("cart", {})
        pid = str(product_id)
        cart[pid] = cart.get(pid, 0) + 1
        session["cart"] = cart
        flash(f"{product.title} додано до кошика", "success")
        return redirect(request.referrer or url_for("catalog"))

    @app.post("/product/<slug>/review")
    def product_review_submit(slug):
        product = Product.query.filter_by(slug=slug, is_active=True).first_or_404()
        author_name = request.form.get("author_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        comment = request.form.get("comment", "").strip()
        try:
            rating = int(request.form.get("rating", "5"))
        except ValueError:
            rating = 5
        rating = min(5, max(1, rating))
        if len(author_name) < 2:
            flash("Вкажіть ім'я для відгуку", "danger")
            return redirect(url_for("product_detail", slug=slug) + "#reviews")
        if email and not validate_email_address(email):
            flash("Вкажіть коректний email", "danger")
            return redirect(url_for("product_detail", slug=slug) + "#reviews")
        if len(comment) < 8:
            flash("Відгук має містити хоча б 8 символів", "danger")
            return redirect(url_for("product_detail", slug=slug) + "#reviews")
        review = ProductReview(
            product_id=product.id,
            user_id=current_user.id if current_user.is_authenticated and not current_user.is_admin else None,
            author_name=author_name,
            email=email or None,
            rating=rating,
            comment=comment,
            is_approved=True,
        )
        db.session.add(review)
        db.session.commit()
        flash("Дякуємо! Ваш відгук додано.", "success")
        return redirect(url_for("product_detail", slug=slug) + "#reviews")

    @app.route("/cart")
    def cart_view():
        items, total, promo, discount, final_total = load_cart_items()
        return render_template("cart.html", items=items, total=total, promo=promo, discount=discount, final_total=final_total)

    @app.post("/cart/update")
    def cart_update():
        cart = session.get("cart", {})
        for key, value in request.form.items():
            if key.startswith("qty_"):
                product_id = key.replace("qty_", "")
                try:
                    qty = max(0, int(value))
                except ValueError:
                    qty = 1
                if qty == 0:
                    cart.pop(product_id, None)
                else:
                    cart[product_id] = qty
        session["cart"] = cart
        promo_code = request.form.get("promo_code", "").strip().upper()
        if promo_code:
            promo = PromoCode.query.filter_by(code=promo_code, is_active=True).first()
            items, total, _, _, _ = load_cart_items(ignore_promo=True)
            if not promo:
                flash("Промокод не знайдено", "warning")
                session.pop("promo_code", None)
            elif promo.calculate_discount(total) <= 0:
                flash("Промокод не підходить для цього кошика", "warning")
                session.pop("promo_code", None)
            else:
                session["promo_code"] = promo_code
                flash(f"Промокод {promo_code} застосовано", "success")
        elif request.form.get("clear_promo"):
            session.pop("promo_code", None)
            flash("Промокод видалено", "info")
        else:
            flash("Кошик оновлено", "success")
        return redirect(url_for("cart_view"))

    @app.route("/checkout", methods=["GET", "POST"])
    def checkout():
        items, total, promo, discount, final_total = load_cart_items()
        if not items:
            flash("Ваш кошик порожній", "warning")
            return redirect(url_for("catalog"))

        if request.method == "POST":
            country_code = request.form.get("phone_country_code", "+380").strip()
            raw_phone = request.form.get("phone", "").strip()
            email = request.form.get("email", "").strip()
            if not validate_phone(raw_phone, country_code):
                flash("Вкажіть коректний номер телефону", "danger")
                return render_template("checkout.html", items=items, total=total, promo=promo, discount=discount, final_total=final_total)
            if email and not validate_email_address(email):
                flash("Вкажіть коректний email", "danger")
                return render_template("checkout.html", items=items, total=total, promo=promo, discount=discount, final_total=final_total)

            order = Order(
                user_id=current_user.id if current_user.is_authenticated and not current_user.is_admin else None,
                customer_name=request.form.get("customer_name", "").strip(),
                customer_surname=request.form.get("customer_surname", "").strip(),
                phone_country_code=country_code,
                phone=format_phone(raw_phone, country_code),
                email=email,
                city=request.form.get("city", "").strip(),
                address=request.form.get("address", "").strip(),
                delivery_method=request.form.get("delivery_method", "").strip(),
                payment_method=request.form.get("payment_method", "").strip(),
                carrier_service=request.form.get("carrier_service", "").strip(),
                warehouse_number=request.form.get("warehouse_number", "").strip(),
                comment=request.form.get("comment", "").strip(),
                total_amount=final_total,
            )
            order.discount_amount = discount
            order.promo_code = promo.code if promo else None
            db.session.add(order)
            db.session.flush()
            for item in items:
                db.session.add(
                    OrderItem(
                        order_id=order.id,
                        product_id=item["product"].id,
                        title=item["product"].title,
                        description=item["product"].description,
                        price=item["product"].current_price,
                        quantity=item["quantity"],
                        supplier_chat_id=item["product"].supplier_chat_id,
                    )
                )
            if promo:
                promo.used_count = (promo.used_count or 0) + 1
            db.session.commit()
            notify_order(order)
            session["cart"] = {}
            session.pop("promo_code", None)
            flash("Замовлення успішно оформлене", "success")
            return redirect(url_for("thank_you", order_id=order.id))

        return render_template("checkout.html", items=items, total=total, promo=promo, discount=discount, final_total=final_total)

    @app.route("/thank-you/<int:order_id>")
    def thank_you(order_id):
        order = Order.query.get_or_404(order_id)
        return render_template("thank_you.html", order=order)

    @app.route("/lead", methods=["POST"])
    def create_lead():
        email = request.form.get("email", "").strip()
        if email and not validate_email_address(email):
            flash("Вкажіть коректний email", "danger")
            return redirect(request.referrer or url_for("home"))
        lead = Lead(
            name=request.form.get("name", "").strip() or "Без імені",
            phone=request.form.get("phone", "").strip(),
            email=email,
            message=request.form.get("message", "").strip(),
        )
        db.session.add(lead)
        db.session.commit()
        flash("Дякуємо! Ми скоро з вами зв'яжемося.", "success")
        return redirect(request.referrer or url_for("home"))

    @app.post("/wishlist/add/<int:product_id>")
    @login_required
    def wishlist_add(product_id):
        if current_user.is_admin:
            return redirect(url_for("admin_dashboard"))
        Product.query.get_or_404(product_id)
        exists = WishlistItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
        if not exists:
            db.session.add(WishlistItem(user_id=current_user.id, product_id=product_id))
            db.session.commit()
            flash("Товар додано в обране", "success")
        else:
            flash("Товар вже в обраному", "info")
        return redirect(request.referrer or url_for("catalog"))

    @app.post("/wishlist/remove/<int:product_id>")
    @login_required
    def wishlist_remove(product_id):
        item = WishlistItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
        if item:
            db.session.delete(item)
            db.session.commit()
            flash("Товар видалено з обраного", "info")
        return redirect(request.referrer or url_for("wishlist_view"))

    @app.route("/wishlist")
    @login_required
    def wishlist_view():
        items = WishlistItem.query.filter_by(user_id=current_user.id).order_by(WishlistItem.created_at.desc()).all()
        products = [Product.query.get(item.product_id) for item in items if Product.query.get(item.product_id)]
        return render_template("account/wishlist.html", products=products)

    @app.route("/account/register", methods=["GET", "POST"])
    def account_register():
        if current_user.is_authenticated and not current_user.is_admin:
            return redirect(url_for("account_dashboard"))
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            full_name = request.form.get("full_name", "").strip()
            if not validate_email_address(email):
                flash("Некоректний email", "danger")
            elif len(password) < 6:
                flash("Пароль має містити мінімум 6 символів", "danger")
            elif User.query.filter_by(email=email).first():
                flash("Користувач з таким email вже існує", "warning")
            else:
                user = User(email=email, full_name=full_name or email.split("@")[0], is_admin=False)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                login_user(user)
                flash("Акаунт створено", "success")
                return redirect(url_for("account_dashboard"))
        return render_template("account/register.html")

    @app.route("/account/login", methods=["GET", "POST"])
    def account_login():
        if current_user.is_authenticated and not current_user.is_admin:
            return redirect(url_for("account_dashboard"))
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = User.query.filter_by(email=email, is_admin=False).first()
            if user and user.check_password(password):
                login_user(user)
                flash("Ви увійшли в кабінет", "success")
                return redirect(url_for("account_dashboard"))
            flash("Невірний email або пароль", "danger")
        return render_template("account/login.html")

    @app.route("/account/google")
    def account_google_login():
        if "google" not in oauth._registry:
            flash("Google авторизація ще не налаштована. Додай GOOGLE_CLIENT_ID і GOOGLE_CLIENT_SECRET у .env", "warning")
            return redirect(url_for("account_login"))
        redirect_uri = url_for("account_google_callback", _external=True)
        return oauth.google.authorize_redirect(redirect_uri)

    @app.route("/account/google/callback")
    def account_google_callback():
        if "google" not in oauth._registry:
            return redirect(url_for("account_login"))
        token = oauth.google.authorize_access_token()
        userinfo = token.get("userinfo") or oauth.google.userinfo()
        email = (userinfo.get("email") or "").lower()
        google_id = userinfo.get("sub")
        name = userinfo.get("name") or email
        if not email:
            flash("Google не повернув email", "danger")
            return redirect(url_for("account_login"))
        user = User.query.filter((User.email == email) | (User.google_id == google_id)).first()
        if not user:
            user = User(email=email, full_name=name, google_id=google_id, is_admin=False)
            db.session.add(user)
        else:
            user.google_id = google_id
            if not user.full_name:
                user.full_name = name
        db.session.commit()
        login_user(user)
        flash("Вхід через Google виконано", "success")
        return redirect(url_for("account_dashboard"))

    @app.route("/account")
    @login_required
    def account_dashboard():
        if current_user.is_admin:
            return redirect(url_for("admin_dashboard"))
        orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
        wishlist_items = WishlistItem.query.filter_by(user_id=current_user.id).count()
        return render_template("account/dashboard.html", orders=orders, wishlist_items=wishlist_items)

    @app.route("/account/logout")
    @login_required
    def account_logout():
        logout_user()
        flash("Ви вийшли з кабінету", "info")
        return redirect(url_for("home"))

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login():
        if current_user.is_authenticated and current_user.is_admin:
            return redirect(url_for("admin_dashboard"))
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = User.query.filter_by(email=email, is_admin=True).first()
            if user and user.check_password(password):
                login_user(user)
                flash("Вхід виконано", "success")
                return redirect(url_for("admin_dashboard"))
            flash("Невірні дані для входу", "danger")
        return render_template("admin/login.html")

    @app.route("/admin/logout")
    @login_required
    def admin_logout():
        logout_user()
        flash("Ви вийшли з адмінки", "info")
        return redirect(url_for("admin_login"))

    def admin_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.is_admin:
                return redirect(url_for("admin_login"))
            return f(*args, **kwargs)
        return decorated

    @app.route("/admin")
    @admin_required
    def admin_dashboard():
        total_products = Product.query.count()
        total_orders = Order.query.count()
        total_leads = Lead.query.count()
        total_visits = SiteVisit.query.count()
        last_orders = Order.query.order_by(Order.created_at.desc()).limit(8).all()
        last_products = Product.query.order_by(Product.created_at.desc()).limit(8).all()
        analytics = build_analytics()
        notif_logs = NotificationLog.query.order_by(NotificationLog.created_at.desc()).limit(8).all()
        return render_template("admin/dashboard.html", total_products=total_products, total_orders=total_orders, total_leads=total_leads, total_visits=total_visits, last_orders=last_orders, last_products=last_products, analytics=analytics, notif_logs=notif_logs)

    @app.route("/admin/products")
    @admin_required
    def admin_products():
        products = Product.query.order_by(Product.created_at.desc()).all()
        return render_template("admin/products.html", products=products)

    @app.route("/admin/products/new", methods=["GET", "POST"])
    @admin_required
    def admin_product_new():
        categories = Category.query.order_by(Category.name.asc()).all()
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            product = Product(
                title=title,
                slug=make_slug(title),
                short_description=request.form.get("short_description", "").strip(),
                description=request.form.get("description", "").strip(),
                specifications=request.form.get("specifications", "").strip(),
                price=float(request.form.get("price", 0) or 0),
                old_price=float(request.form.get("old_price", 0) or 0) if request.form.get("old_price") else None,
                discount_enabled=bool(request.form.get("discount_enabled")),
                is_top=bool(request.form.get("is_top")),
                is_active=bool(request.form.get("is_active")),
                stock_status=request.form.get("stock_status", "В наявності").strip(),
                supplier_chat_id=request.form.get("supplier_chat_id", "").strip(),
                category_id=int(request.form.get("category_id")),
            )
            db.session.add(product)
            db.session.flush()
            save_product_images(product, request.files.getlist("images"))
            db.session.commit()
            flash("Товар створено", "success")
            return redirect(url_for("admin_products"))
        return render_template("admin/product_form.html", categories=categories, product=None)

    @app.route("/admin/products/<int:product_id>/edit", methods=["GET", "POST"])
    @admin_required
    def admin_product_edit(product_id):
        product = Product.query.get_or_404(product_id)
        categories = Category.query.order_by(Category.name.asc()).all()
        if request.method == "POST":
            product.title = request.form.get("title", "").strip()
            product.slug = make_slug(product.title, product.id)
            product.short_description = request.form.get("short_description", "").strip()
            product.description = request.form.get("description", "").strip()
            product.specifications = request.form.get("specifications", "").strip()
            product.price = float(request.form.get("price", 0) or 0)
            product.old_price = float(request.form.get("old_price", 0) or 0) if request.form.get("old_price") else None
            product.discount_enabled = bool(request.form.get("discount_enabled"))
            product.is_top = bool(request.form.get("is_top"))
            product.is_active = bool(request.form.get("is_active"))
            product.stock_status = request.form.get("stock_status", "В наявності").strip()
            product.supplier_chat_id = request.form.get("supplier_chat_id", "").strip()
            product.category_id = int(request.form.get("category_id"))
            if request.form.getlist("delete_image"):
                for image_id in request.form.getlist("delete_image"):
                    image = ProductImage.query.get(int(image_id))
                    if image:
                        try:
                            os.remove(BASE_DIR / image.image_path)
                        except OSError:
                            pass
                        db.session.delete(image)
            save_product_images(product, request.files.getlist("images"))
            db.session.commit()
            flash("Товар оновлено", "success")
            return redirect(url_for("admin_products"))
        return render_template("admin/product_form.html", categories=categories, product=product)

    @app.post("/admin/products/<int:product_id>/delete")
    @admin_required
    def admin_product_delete(product_id):
        product = Product.query.get_or_404(product_id)
        db.session.delete(product)
        db.session.commit()
        flash("Товар видалено", "info")
        return redirect(url_for("admin_products"))

    @app.route("/admin/categories", methods=["GET", "POST"])
    @admin_required
    def admin_categories():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            category = Category(name=name, slug=make_slug(name), description=request.form.get("description", "").strip())
            db.session.add(category)
            db.session.commit()
            flash("Категорію додано", "success")
            return redirect(url_for("admin_categories"))
        categories = Category.query.order_by(Category.name.asc()).all()
        return render_template("admin/categories.html", categories=categories)

    @app.post("/admin/categories/<int:category_id>/delete")
    @admin_required
    def admin_category_delete(category_id):
        category = Category.query.get_or_404(category_id)
        if category.products:
            flash("Спочатку перемістіть або видаліть товари з цієї категорії", "warning")
            return redirect(url_for("admin_categories"))
        db.session.delete(category)
        db.session.commit()
        flash("Категорію видалено", "info")
        return redirect(url_for("admin_categories"))

    @app.route("/admin/orders")
    @admin_required
    def admin_orders():
        orders = Order.query.order_by(Order.created_at.desc()).all()
        return render_template("admin/orders.html", orders=orders)

    @app.route("/admin/orders/<int:order_id>", methods=["GET", "POST"])
    @admin_required
    def admin_order_detail(order_id):
        order = Order.query.get_or_404(order_id)
        if request.method == "POST":
            order.status = request.form.get("status", order.status)
            db.session.commit()
            flash("Статус замовлення змінено", "success")
            return redirect(url_for("admin_order_detail", order_id=order.id))
        return render_template("admin/order_detail.html", order=order)

    @app.route("/admin/leads")
    @admin_required
    def admin_leads():
        leads = Lead.query.order_by(Lead.created_at.desc()).all()
        return render_template("admin/leads.html", leads=leads)

    @app.route("/admin/analytics")
    @admin_required
    def admin_analytics():
        analytics = build_analytics(full=True)
        return render_template("admin/analytics.html", analytics=analytics)

    @app.route("/admin/promocodes", methods=["GET", "POST"])
    @admin_required
    def admin_promocodes():
        if request.method == "POST":
            code = request.form.get("code", "").strip().upper()
            if code:
                promo = PromoCode(
                    code=code,
                    discount_percent=float(request.form.get("discount_percent") or 0) or None,
                    discount_amount=float(request.form.get("discount_amount") or 0) or None,
                    min_order_amount=float(request.form.get("min_order_amount") or 0) or 0,
                    usage_limit=int(request.form.get("usage_limit") or 0) or None,
                    is_active=bool(request.form.get("is_active")),
                )
                db.session.add(promo)
                db.session.commit()
                flash("Промокод створено", "success")
            return redirect(url_for("admin_promocodes"))
        promos = PromoCode.query.order_by(PromoCode.created_at.desc()).all()
        return render_template("admin/promocodes.html", promos=promos)

    @app.post("/admin/promocodes/<int:promo_id>/toggle")
    @admin_required
    def admin_promocode_toggle(promo_id):
        promo = PromoCode.query.get_or_404(promo_id)
        promo.is_active = not promo.is_active
        db.session.commit()
        flash("Статус промокоду змінено", "success")
        return redirect(url_for("admin_promocodes"))

    @app.post("/admin/promocodes/<int:promo_id>/delete")
    @admin_required
    def admin_promocode_delete(promo_id):
        promo = PromoCode.query.get_or_404(promo_id)
        db.session.delete(promo)
        db.session.commit()
        flash("Промокод видалено", "info")
        return redirect(url_for("admin_promocodes"))

    @app.route("/admin/reviews")
    @admin_required
    def admin_reviews():
        reviews = ProductReview.query.order_by(ProductReview.created_at.desc()).all()
        return render_template("admin/reviews.html", reviews=reviews)

    @app.post("/admin/reviews/<int:review_id>/toggle")
    @admin_required
    def admin_review_toggle(review_id):
        review = ProductReview.query.get_or_404(review_id)
        review.is_approved = not review.is_approved
        db.session.commit()
        flash("Статус відгуку оновлено", "success")
        return redirect(url_for("admin_reviews"))

    @app.post("/admin/reviews/<int:review_id>/delete")
    @admin_required
    def admin_review_delete(review_id):
        review = ProductReview.query.get_or_404(review_id)
        db.session.delete(review)
        db.session.commit()
        flash("Відгук видалено", "info")
        return redirect(url_for("admin_reviews"))


    @app.route("/admin/content", methods=["GET", "POST"])
    @admin_required
    def admin_content():
        if request.method == "POST":
            for field in CONTENT_FIELDS:
                set_setting(field["key"], request.form.get(field["key"], "").strip())
            db.session.commit()
            flash("Тексти, кнопки та порядок блоків оновлено", "success")
            return redirect(url_for("admin_content"))
        grouped_fields = defaultdict(list)
        for field in CONTENT_FIELDS:
            section = field["label"].split("•")[0].strip()
            current_value = get_setting(field["key"], field.get("default", ""))
            field_payload = dict(field)
            field_payload["value"] = current_value
            grouped_fields[section].append(field_payload)
        return render_template("admin/content.html", grouped_fields=dict(grouped_fields))

    @app.route("/admin/import", methods=["GET", "POST"])
    @admin_required
    def admin_import():
        if request.method == "POST":
            file = request.files.get("import_file")
            if not file or not file.filename:
                flash("Оберіть файл бази для імпорту", "warning")
                return redirect(url_for("admin_import"))
            ext = Path(file.filename).suffix.lower()
            if ext not in {".db", ".sqlite", ".sqlite3"}:
                flash("Підтримуються SQLite файли: .db, .sqlite, .sqlite3", "danger")
                return redirect(url_for("admin_import"))
            temp_name = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
            temp_path = INSTANCE_DIR / temp_name
            file.save(temp_path)
            try:
                result = import_products_from_uploaded_db(temp_path)
                flash(
                    f"Імпорт завершено: нових товарів — {result['imported_products']}, оновлено — {result['updated_products']}, нових категорій — {result['imported_categories']}.",
                    "success",
                )
            except Exception as exc:
                flash(f"Не вдалося імпортувати файл: {exc}", "danger")
            finally:
                if temp_path.exists():
                    temp_path.unlink()
            return redirect(url_for("admin_import"))
        return render_template("admin/import.html")

    @app.route("/admin/settings", methods=["GET", "POST"])
    @admin_required
    def admin_settings():
        if request.method == "POST":
            for key in [
                "telegram_bot_token", "telegram_owner_chat_id", "domain_name", "google_client_id", "google_client_secret",
                "novaposhta_api_key", "meest_api_key", "meest_login", "meest_password", "meest_public_api_base"
            ]:
                set_setting(key, request.form.get(key, "").strip())
            db.session.commit()
            flash("Налаштування збережено", "success")
            return redirect(url_for("admin_settings"))
        settings = {key: get_setting(key, os.getenv(key.upper(), "")) for key in [
            "telegram_bot_token", "telegram_owner_chat_id", "domain_name", "google_client_id", "google_client_secret",
            "novaposhta_api_key", "meest_api_key", "meest_login", "meest_password", "meest_public_api_base"
        ]}
        settings["domain_name"] = settings["domain_name"] or os.getenv("APP_DOMAIN", "localhost:5000")
        nginx_example = build_nginx_example(settings["domain_name"])
        logs = NotificationLog.query.order_by(NotificationLog.created_at.desc()).limit(15).all()
        return render_template("admin/settings.html", settings=settings, nginx_example=nginx_example, logs=logs)

    @app.post("/admin/settings/test-telegram")
    @admin_required
    def admin_test_telegram():
        token = get_setting("telegram_bot_token", "")
        owner_chat_id = get_setting("telegram_owner_chat_id", "")
        ok, text = send_telegram_message(owner_chat_id, "✅ Тестове повідомлення з AmperShop", token)
        flash("Telegram працює" if ok else f"Telegram не надіслав повідомлення: {text}", "success" if ok else "danger")
        return redirect(url_for("admin_settings"))

    @app.route("/admin/api/analytics-chart")
    @admin_required
    def analytics_chart():
        days = int(request.args.get("days", 14))
        start = datetime.utcnow() - timedelta(days=days)
        rows = (
            db.session.query(func.date(SiteVisit.created_at), func.count(SiteVisit.id))
            .filter(SiteVisit.created_at >= start)
            .group_by(func.date(SiteVisit.created_at))
            .all()
        )
        return jsonify({"labels": [str(r[0]) for r in rows], "values": [r[1] for r in rows]})

    @app.route("/admin/api/validate-phone")
    @admin_required
    def admin_validate_phone_api():
        phone = request.args.get("phone", "")
        code = request.args.get("code", "+380")
        return jsonify({"valid": validate_phone(phone, code), "normalized": format_phone(phone, code) if validate_phone(phone, code) else ""})

    @app.get("/api/validate-contact")
    def validate_contact_api():
        phone = request.args.get("phone", "")
        code = request.args.get("code", "+380")
        email = request.args.get("email", "")
        return jsonify({
            "phone_valid": validate_phone(phone, code) if phone else None,
            "phone_normalized": format_phone(phone, code) if phone and validate_phone(phone, code) else "",
            "email_valid": validate_email_address(email) if email else None,
        })

    @app.get("/api/shipping/cities")
    def shipping_cities_api():
        provider = request.args.get("provider", "np")
        q = request.args.get("q", "").strip()
        if len(q) < 2:
            return jsonify([])
        return jsonify(fetch_shipping_cities(provider, q))

    @app.get("/api/shipping/branches")
    def shipping_branches_api():
        provider = request.args.get("provider", "np")
        city_ref = request.args.get("city_ref", "")
        q = request.args.get("q", "").strip()
        return jsonify(fetch_shipping_branches(provider, city_ref, q))

    return app


def ensure_columns():
    inspector = db.inspect(db.engine)
    tables = {t: [c["name"] for c in inspector.get_columns(t)] for t in inspector.get_table_names()}
    statements = []
    if "user" in tables:
        if "google_id" not in tables["user"]:
            statements.append("ALTER TABLE user ADD COLUMN google_id VARCHAR(255)")
    if "order" in tables:
        for column, ddl in {
            "user_id": "INTEGER",
            "phone_country_code": "VARCHAR(10)",
            "carrier_service": "VARCHAR(120)",
            "warehouse_number": "VARCHAR(120)",
            "promo_code": "VARCHAR(50)",
            "discount_amount": "FLOAT",
        }.items():
            if column not in tables["order"]:
                statements.append(f'ALTER TABLE "order" ADD COLUMN {column} {ddl}')
    if "notification_log" not in tables:
        NotificationLog.__table__.create(db.engine)
    if "promo_code" not in tables:
        PromoCode.__table__.create(db.engine)
    if "wishlist_item" not in tables:
        WishlistItem.__table__.create(db.engine)
    for stmt in statements:
        db.session.execute(db.text(stmt))
    db.session.commit()


def load_cart_items(ignore_promo=False):
    cart = session.get("cart", {})
    items = []
    total = 0
    for pid, qty in cart.items():
        product = Product.query.get(int(pid))
        if not product:
            continue
        subtotal = product.current_price * qty
        total += subtotal
        items.append({"product": product, "quantity": qty, "subtotal": subtotal})
    promo = None
    discount = 0
    if not ignore_promo and session.get("promo_code"):
        promo = PromoCode.query.filter_by(code=session.get("promo_code"), is_active=True).first()
        if promo:
            discount = promo.calculate_discount(total)
        else:
            session.pop("promo_code", None)
    final_total = max(total - discount, 0)
    return items, total, promo, discount, final_total


def seed_admin():
    admin_email = os.getenv("ADMIN_EMAIL", "admin@ampershop.local").lower()
    admin_password = os.getenv("ADMIN_PASSWORD", "admin12345")
    admin = User.query.filter_by(email=admin_email).first()
    if not admin:
        admin = User(email=admin_email, full_name="Адміністратор", is_admin=True)
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()


def seed_defaults():
    if not Category.query.first():
        db.session.add_all([
            Category(name="Електроніка", slug="elektronika", description="Сучасні гаджети та техніка"),
            Category(name="Аксесуари", slug="aksesuary", description="Корисні дрібниці та стильні доповнення"),
        ])
        db.session.commit()
    if not Product.query.first():
        category = Category.query.first()
        product = Product(
            title="Бездротова швидка зарядка Volt X",
            slug="bezdrotova-shvydka-zaryadka-volt-x",
            short_description="Преміальна зарядка з ефектним мінімалістичним дизайном.",
            description="Стильна бездротова зарядка для смартфонів з підтримкою швидкої зарядки та захистом від перегріву.",
            specifications="Потужність: 15W\nІнтерфейс: USB-C\nКолір: чорний\nМатеріал: алюміній + скло",
            price=1299,
            old_price=1599,
            discount_enabled=True,
            is_top=True,
            is_active=True,
            stock_status="В наявності",
            supplier_chat_id="",
            category_id=category.id,
        )
        db.session.add(product)
        db.session.commit()
    defaults = {
        "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
        "telegram_owner_chat_id": os.getenv("TELEGRAM_OWNER_CHAT_ID", ""),
        "domain_name": os.getenv("APP_DOMAIN", "localhost:5000"),
        "google_client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        "google_client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
        "novaposhta_api_key": os.getenv("NOVAPOSHTA_API_KEY", ""),
        "meest_api_key": os.getenv("MEEST_API_KEY", ""),
        "meest_login": os.getenv("MEEST_LOGIN", ""),
        "meest_password": os.getenv("MEEST_PASSWORD", ""),
        "meest_public_api_base": os.getenv("MEEST_PUBLIC_API_BASE", "https://publicapi.meest.com"),
    }
    for key, value in defaults.items():
        if not Setting.query.filter_by(key=key).first():
            db.session.add(Setting(key=key, value=value))
    for field in CONTENT_FIELDS:
        if not Setting.query.filter_by(key=field["key"]).first():
            db.session.add(Setting(key=field["key"], value=field.get("default", "")))
    if not PromoCode.query.first():
        db.session.add(PromoCode(code="WELCOME10", discount_percent=10, is_active=True, min_order_amount=1000))
    db.session.commit()


def build_analytics(full=False):
    today = datetime.utcnow()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    top_products = (
        db.session.query(Product.title, func.count(SiteVisit.id).label("views"))
        .join(SiteVisit, SiteVisit.product_id == Product.id)
        .group_by(Product.id)
        .order_by(func.count(SiteVisit.id).desc())
        .limit(10)
        .all()
    )
    recent_orders_amount = db.session.query(func.sum(Order.total_amount)).filter(Order.created_at >= month_ago).scalar() or 0
    visits_30 = SiteVisit.query.filter(SiteVisit.created_at >= month_ago).count()
    orders_30 = Order.query.filter(Order.created_at >= month_ago).count()
    conversion = round((orders_30 / visits_30) * 100, 2) if visits_30 else 0
    data = {
        "visits_7": SiteVisit.query.filter(SiteVisit.created_at >= week_ago).count(),
        "visits_30": visits_30,
        "orders_30": orders_30,
        "leads_30": Lead.query.filter(Lead.created_at >= month_ago).count(),
        "revenue_30": recent_orders_amount,
        "conversion": conversion,
        "top_products": top_products,
    }
    if full:
        data["popular_pages"] = (
            db.session.query(SiteVisit.path, func.count(SiteVisit.id).label("cnt"))
            .group_by(SiteVisit.path)
            .order_by(func.count(SiteVisit.id).desc())
            .limit(10)
            .all()
        )
        data["recent_leads"] = Lead.query.order_by(Lead.created_at.desc()).limit(10).all()
        carrier_counts = db.session.query(Order.delivery_method, func.count(Order.id)).group_by(Order.delivery_method).all()
        data["carrier_counts"] = carrier_counts
    return data


def get_setting(key, default=""):
    item = Setting.query.filter_by(key=key).first()
    return item.value if item and item.value is not None else default


def set_setting(key, value):
    item = Setting.query.filter_by(key=key).first()
    if not item:
        item = Setting(key=key, value=value)
        db.session.add(item)
    else:
        item.value = value




def cms_lines(key, default=""):
    value = get_setting(key, default) or ""
    return [line.strip() for line in value.splitlines() if line.strip()]


def cms_int(key, default=0):
    value = get_setting(key, str(default))
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def import_products_from_uploaded_db(file_path):
    imported_products = 0
    imported_categories = 0
    updated_products = 0
    source_dir = Path(file_path).resolve().parent
    conn = sqlite3.connect(file_path)
    conn.row_factory = sqlite3.Row
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

    def pick_table(options):
        for name in options:
            if name in tables:
                return name
        return None

    def columns(table_name):
        return [row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]

    category_table = pick_table(["category", "categories"])
    product_table = pick_table(["product", "products", "catalog_products", "items"])
    image_table = pick_table(["product_image", "product_images", "images"])

    category_map = {}
    if category_table:
        for row in conn.execute(f"SELECT * FROM {category_table}").fetchall():
            data = dict(row)
            name = (data.get("name") or data.get("title") or "").strip()
            if not name:
                continue
            slug = (data.get("slug") or make_slug(name)).strip()
            category = Category.query.filter((Category.slug == slug) | (Category.name == name)).first()
            if not category:
                category = Category(name=name, slug=make_slug(slug), description=(data.get("description") or "").strip() or None)
                db.session.add(category)
                db.session.flush()
                imported_categories += 1
            else:
                category.description = (data.get("description") or category.description or "").strip() or None
                db.session.flush()
            source_id = data.get("id")
            if source_id is not None:
                category_map[source_id] = category.id

    if not product_table:
        conn.close()
        raise ValueError("У файлі не знайдено таблицю products/product/items")

    product_rows = conn.execute(f"SELECT * FROM {product_table}").fetchall()
    image_rows = []
    if image_table:
        image_rows = conn.execute(f"SELECT * FROM {image_table}").fetchall()
    images_by_product = {}
    for row in image_rows:
        data = dict(row)
        product_id = data.get("product_id") or data.get("item_id")
        if product_id is None:
            continue
        images_by_product.setdefault(product_id, []).append(data)

    for row in product_rows:
        data = dict(row)
        title = (data.get("title") or data.get("name") or "").strip()
        if not title:
            continue
        slug = (data.get("slug") or make_slug(title)).strip()
        category_id = data.get("category_id")
        if category_id in category_map:
            target_category_id = category_map[category_id]
        else:
            fallback_category = Category.query.first()
            if not fallback_category:
                fallback_category = Category(name="Інше", slug="inshe")
                db.session.add(fallback_category)
                db.session.flush()
            target_category_id = fallback_category.id

        product = Product.query.filter((Product.slug == slug) | (Product.title == title)).first()
        is_new = product is None
        if is_new:
            product = Product(
                title=title,
                slug=make_slug(slug),
                category_id=target_category_id,
                price=0,
            )
            db.session.add(product)
            db.session.flush()

        product.title = title
        product.slug = make_slug(slug, product.id) if not is_new else product.slug
        product.short_description = (data.get("short_description") or data.get("summary") or data.get("excerpt") or product.short_description or "").strip() or None
        product.description = (data.get("description") or data.get("body") or product.description or "").strip() or None
        product.specifications = (data.get("specifications") or data.get("характеристики") or product.specifications or "").strip() or None
        product.price = float(data.get("price") or data.get("current_price") or product.price or 0)
        old_price_raw = data.get("old_price") or data.get("compare_price") or data.get("discount_from")
        product.old_price = float(old_price_raw) if old_price_raw not in (None, "", 0, "0") else None
        product.discount_enabled = bool(product.old_price and product.old_price > product.price)
        product.is_top = bool(data.get("is_top") or data.get("top") or False)
        product.is_active = bool(data.get("is_active") if data.get("is_active") is not None else True)
        product.stock_status = (data.get("stock_status") or data.get("availability") or product.stock_status or "В наявності").strip()
        product.supplier_chat_id = (str(data.get("supplier_chat_id") or product.supplier_chat_id or "")).strip() or None
        product.category_id = target_category_id

        db.session.flush()

        if is_new:
            imported_products += 1
        else:
            updated_products += 1

        if product.id and not ProductImage.query.filter_by(product_id=product.id).first():
            # Try to import image file paths if present
            possible_images = []
            single_image = data.get("image_path") or data.get("image") or data.get("main_image")
            if single_image:
                possible_images.append({"image_path": single_image, "alt_text": title})
            possible_images.extend(images_by_product.get(data.get("id"), []))
            for image_data in possible_images:
                image_path = str(image_data.get("image_path") or image_data.get("path") or image_data.get("file") or "").strip()
                if not image_path:
                    continue
                src = Path(image_path)
                if not src.is_absolute():
                    src = source_dir / image_path
                if src.exists() and src.is_file() and allowed_file(src.name):
                    unique_name = f"{uuid.uuid4().hex}_{secure_filename(src.name)}"
                    dest = UPLOAD_DIR / unique_name
                    shutil.copy2(src, dest)
                    db.session.add(ProductImage(image_path=f"static/uploads/{unique_name}", alt_text=image_data.get("alt_text") or title, product_id=product.id))

    db.session.commit()
    conn.close()
    return {"imported_products": imported_products, "updated_products": updated_products, "imported_categories": imported_categories}

def make_slug(text, object_id=None):
    slug = text.lower().replace("'", "").replace('"', "").replace(" ", "-").replace("_", "-")
    translit_map = {"а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d", "е": "e", "є": "ye", "ж": "zh", "з": "z", "и": "y", "і": "i", "ї": "yi", "й": "i", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch", "ю": "yu", "я": "ya"}
    for src, dst in translit_map.items():
        slug = slug.replace(src, dst)
    slug = "".join(ch for ch in slug if ch.isalnum() or ch == "-").strip("-")
    base = slug or f"item-{uuid.uuid4().hex[:6]}"
    candidate = base
    idx = 1
    while True:
        query = Product.query.filter_by(slug=candidate)
        if object_id:
            query = query.filter(Product.id != object_id)
        exists = query.first() or Category.query.filter_by(slug=candidate).first()
        if not exists:
            return candidate
        candidate = f"{base}-{idx}"
        idx += 1


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_product_images(product, files):
    for file in files:
        if not file or not file.filename or not allowed_file(file.filename):
            continue
        filename = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        path = UPLOAD_DIR / unique_name
        file.save(path)
        try:
            img = Image.open(path)
            img.thumbnail((1800, 1800))
            img.save(path)
        except Exception:
            pass
        db.session.add(ProductImage(image_path=f"static/uploads/{unique_name}", product_id=product.id))


def validate_email_address(email):
    try:
        validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


def infer_region(country_code):
    for item in COUNTRY_PHONE_CODES:
        if item["code"] == country_code:
            return item["region"]
    return "UA"


def validate_phone(phone, country_code="+380"):
    digits = re.sub(r"[^\d]", "", phone)
    if not digits:
        return False
    parsed = None
    try:
        parsed = phonenumbers.parse(f"{country_code}{digits}", infer_region(country_code))
    except phonenumbers.NumberParseException:
        try:
            parsed = phonenumbers.parse(phone, infer_region(country_code))
        except phonenumbers.NumberParseException:
            return False
    return phonenumbers.is_possible_number(parsed) and phonenumbers.is_valid_number(parsed)


def format_phone(phone, country_code="+380"):
    digits = re.sub(r"[^\d]", "", phone)
    try:
        parsed = phonenumbers.parse(f"{country_code}{digits}", infer_region(country_code))
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        return f"{country_code}{digits}"


def log_notification(channel, target, success, message, response_text=""):
    db.session.add(NotificationLog(channel=channel, target=target, success=success, message=message[:2000] if message else "", response_text=(response_text or "")[:4000]))
    db.session.commit()


def send_telegram_message(chat_id, message, token):
    if not token:
        return False, "Не заданий токен Telegram бота"
    if not chat_id:
        return False, "Не заданий chat_id"
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": str(chat_id).strip(), "text": message},
            timeout=15,
        )
        ok = response.ok and response.json().get("ok", False)
        response_text = response.text
        log_notification("telegram", str(chat_id), ok, message, response_text)
        if ok:
            return True, "ok"
        return False, response_text
    except requests.RequestException as exc:
        log_notification("telegram", str(chat_id), False, message, str(exc))
        return False, str(exc)


def notify_order(order):
    token = get_setting("telegram_bot_token", os.getenv("TELEGRAM_BOT_TOKEN", ""))
    owner_chat_id = get_setting("telegram_owner_chat_id", os.getenv("TELEGRAM_OWNER_CHAT_ID", ""))
    item_lines = [f"• {item.title} × {item.quantity} — {item.price:.0f} грн" for item in order.items]
    common = (
        f"Нове замовлення #{order.id}\n"
        f"Клієнт: {order.customer_name} {order.customer_surname}\n"
        f"Телефон: {order.phone_country_code or ''} {order.phone}\n"
        f"Email: {order.email or '-'}\n"
        f"Місто: {order.city or '-'}\n"
        f"Адреса: {order.address or '-'}\n"
        f"Доставка: {order.delivery_method}\n"
        f"Сервіс: {order.carrier_service or '-'}\n"
        f"Відділення/індекс: {order.warehouse_number or '-'}\n"
        f"Оплата: {order.payment_method}\n"
        f"Коментар: {order.comment or '-'}\n"
        f"Промокод: {order.promo_code or '-'}\nЗнижка: {(order.discount_amount or 0):.0f} грн\nСума: {order.total_amount:.0f} грн\n\n"
        f"Товари:\n" + "\n".join(item_lines)
    )
    send_telegram_message(owner_chat_id, common, token)
    grouped = defaultdict(list)
    for item in order.items:
        if item.supplier_chat_id:
            grouped[item.supplier_chat_id].append(item)
    for supplier_chat_id, supplier_items in grouped.items():
        item_lines = [f"• {item.title} × {item.quantity} — {item.price:.0f} грн" for item in supplier_items]
        supplier_message = (
            f"Нове замовлення на ваші товари\n"
            f"Замовлення #{order.id}\n"
            f"Клієнт: {order.customer_name} {order.customer_surname}\n"
            f"Телефон: {order.phone_country_code or ''} {order.phone}\n"
            f"Email: {order.email or '-'}\n"
            f"Місто: {order.city or '-'}\n"
            f"Адреса: {order.address or '-'}\n"
            f"Доставка: {order.delivery_method}\n"
            f"Сервіс: {order.carrier_service or '-'}\n"
            f"Відділення/індекс: {order.warehouse_number or '-'}\n"
            f"Оплата: {order.payment_method}\n"
            f"Коментар: {order.comment or '-'}\n\n"
            f"Позиції:\n' + '\n".join(item_lines)
        )
        send_telegram_message(supplier_chat_id, supplier_message, token)



def nova_poshta_request(model_name, called_method, properties=None):
    api_key = get_setting("novaposhta_api_key", os.getenv("NOVAPOSHTA_API_KEY", ""))
    if not api_key:
        return []
    payload = {
        "apiKey": api_key,
        "modelName": model_name,
        "calledMethod": called_method,
        "methodProperties": properties or {},
    }
    try:
        r = requests.post("https://api.novaposhta.ua/v2.0/json/", json=payload, timeout=20)
        data = r.json()
        return data.get("data", []) if data.get("success") else []
    except Exception:
        return []


def fetch_shipping_cities(provider, query):
    provider = (provider or "np").lower()
    results = []
    if provider == "np":
        data = nova_poshta_request("Address", "searchSettlements", {"CityName": query, "Limit": 15})
        for item in data:
            for addr in item.get("Addresses", []):
                results.append({
                    "ref": addr.get("Ref") or addr.get("DeliveryCity"),
                    "label": addr.get("Present") or addr.get("MainDescription") or addr.get("SettlementTypeDescription", "") + " " + addr.get("CityDescription", ""),
                })
        if not results:
            data = nova_poshta_request("Address", "getCities", {"FindByString": query, "Limit": 15})
            for item in data:
                results.append({"ref": item.get("Ref"), "label": item.get("Description")})
    elif provider == "meest":
        results = meest_public_lookup("cities", query)
    return results[:15]


def fetch_shipping_branches(provider, city_ref, query=""):
    provider = (provider or "np").lower()
    results = []
    if provider == "np":
        props = {"Limit": 50}
        if city_ref:
            props["CityRef"] = city_ref
        if query:
            props["FindByString"] = query
        data = nova_poshta_request("AddressGeneral", "getWarehouses", props)
        if not data:
            data = nova_poshta_request("Address", "getWarehouses", props)
        for item in data:
            label = item.get("Description") or item.get("ShortAddress") or item.get("SiteKey")
            results.append({"ref": item.get("Ref") or item.get("SiteKey"), "label": label})
    elif provider == "meest":
        results = meest_public_lookup("branches", query, city_ref=city_ref)
    return results[:50]


def meest_public_lookup(kind, query, city_ref=""):
    base = get_setting("meest_public_api_base", os.getenv("MEEST_PUBLIC_API_BASE", "https://publicapi.meest.com")).rstrip("/")
    candidates = []
    if kind == "cities":
        candidates = [
            (f"{base}/api/v1/cities", {"search": query}),
            (f"{base}/cities", {"search": query}),
            (f"{base}/api/cities", {"q": query}),
        ]
    else:
        candidates = [
            (f"{base}/api/v1/branches", {"search": query, "city_ref": city_ref}),
            (f"{base}/branches", {"search": query, "city_ref": city_ref}),
            (f"{base}/api/branches", {"q": query, "city_ref": city_ref}),
        ]
    for url, params in candidates:
        try:
            r = requests.get(url, params=params, timeout=15)
            if not r.ok:
                continue
            data = r.json()
            items = data if isinstance(data, list) else data.get("data") or data.get("items") or []
            norm = []
            for item in items:
                label = item.get("label") or item.get("name") or item.get("title") or item.get("branch") or item.get("city")
                ref = item.get("ref") or item.get("id") or item.get("uuid") or label
                if label:
                    norm.append({"ref": str(ref), "label": str(label)})
            if norm:
                return norm
        except Exception:
            continue
    return []


def build_nginx_example(domain):
    domain = domain or "example.com"
    return f'''server {{
    listen 80;
    server_name {domain} www.{domain};

    location /static/ {{
        alias /path/to/ampershop/static/;
    }}

    location / {{
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}'''


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
