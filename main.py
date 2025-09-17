# import uvicorn
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from typing import Dict, List
from product_list import products
from db import ecommerce_collection
from bson.objectid import ObjectId




# Initialize the FastAPI app
app = FastAPI(
    title="Simple E-commerce Backend API",
    description="A basic backend for an e-commerce platform with product and order management."
)

# --- In-memory data storage (simulating a database) ---
# Dictionaries to store our data. In a real application, you would use a database.
# We'll use product IDs, order IDs, and user IDs as keys.
products_db: Dict[int, 'Product'] = {}
orders_db: Dict[int, 'Order'] = {}
carts_db: Dict[int, List['ProductInOrder']] = {}
users_db: Dict[int, 'User'] = {}

# Keep track of the next available ID for products, orders, and users
next_product_id = 1
next_order_id = 1
next_user_id = 1

# --- Pydantic Models for Data Validation ---
# These models define the structure and validation rules for our data.

class ProductBase(BaseModel):
    """Base model for a product."""
    name: str
    description: str
    price: float
    image: str
    stock: int

class Product(ProductBase):
    """Model for a product, including its ID."""
    id: int

class ProductCreate(ProductBase):
    """Model for creating a new product."""
    pass

class ProductInOrder(BaseModel):
    """Model representing a product and its quantity within an order."""
    product_id: int
    quantity: int

class Order(BaseModel):
    """Model for a complete order."""
    id: int
    products: List[ProductInOrder]
    total_price: float
    status: str = "pending"

class AddToCartRequest(BaseModel):
    """Model for the request body when adding to cart."""
    user_id: int
    product_id: int
    quantity: int

# Pydantic models for user management
class UserCreate(BaseModel):
    """Model for creating a new user."""
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    """Model for user login."""
    email: str
    password: str

class User(BaseModel):
    """Model for a user, including the ID."""
    id: int
    username: str
    email: str

# Model for the checkout summary response
class CheckoutSummary(BaseModel):
    """Model representing the summary of a checkout."""
    cart_items: List[ProductInOrder]
    total_price: float

# --- Populate with sample data ---
# This simulates having some initial data in a database.
products_db[1] = Product(id=1, name="Smartphone", description="A great phone with a fantastic camera.", price=699.99, image="https://example.com/smartphone.jpg", stock=15)
products_db[2] = Product(id=2, name="Laptop", description="Powerful laptop for work and gaming.", price=1200.00, image="https://example.com/laptop.jpg", stock=8)
products_db[3] = Product(id=3, name="Wireless Headphones", description="Noise-cancelling headphones with long battery life.", price=199.50, image="https://example.com/headphones.jpg", stock=30)
products_db[4] = Product(id=4, name= "bag", description= "Louis Vuitton - black", price= 500.00, image= "https://example.com/bag.jpg", stock=5)
products_db[5] = Product(id= 5, name= "lacoste", description= "Polo - Blue", price= 300.00, image= "https://example.com/lacoste.jpg", stock= 22)
products_db[6] = Product(id= 6, name= "jeans", description= "Baggy - Seablue", price= 250.00, image= "https://example.com/jeans.jpg", stock=1)



# --- API Endpoints ---

@app.get("/", tags=["Home"])
def read_root():
    return {"message": "Welcome to our E-commerce API"}

@app.get(
    "/products/",
    tags=["Products"],
    response_model=List[Product],
    summary="Get all products"
)
def get_products():
    return list(products_db.values())

@app.get(
    "/products/{product_id}",
    tags=["Products"],
    response_model=Product,
    summary="Get a product by ID"
)
def get_product(product_id: int):
    if product_id not in products_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return products_db[product_id]




@app.post(
    "/register",
    tags=["Users"],
    response_model=User,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user"
)
def register_user(user: UserCreate):
    global next_user_id
    
    # Check if username or email already exists
    for existing_user in users_db.values():
        if existing_user["username"] == user.username:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")
        if existing_user["email"] == user.email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
            
    # Create the new user and add to the database
    new_user = User(id=next_user_id, username=user.username, email=user.email)
    users_db[next_user_id] = {
        "id": next_user_id,
        "username": user.username,
        "email": user.email,
        "password": user.password  # Storing password in plain text for this simple example
    }
    next_user_id += 1
    return new_user

@app.post(
    "/login",
    tags=["Users"],
    summary="Log in a user"
)
def login_user(user: UserLogin):
    for existing_user in users_db.values():
        if existing_user["email"] == user.email and existing_user["password"] == user.password:
            return {"message": "Login successful"}
    
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

@app.post(
    "/cart/",
    tags=["Cart"],
    summary="Add an item to a user's cart"
)
def add_to_cart(add_request: AddToCartRequest):
    if add_request.user_id not in users_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    product = products_db.get(add_request.product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Product not found"
        )

    # Check for sufficient stock before adding to cart
    if add_request.quantity > product.stock:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough stock for product '{product.name}'."
        )

    if add_request.user_id not in carts_db:
        carts_db[add_request.user_id] = []

    cart_items = carts_db[add_request.user_id]
    
    # Check if the product is already in the cart
    found = False
    for item in cart_items:
        if item.product_id == add_request.product_id:
            item.quantity += add_request.quantity
            found = True
            break
    
    if not found:
        new_item = ProductInOrder(
            product_id=add_request.product_id, 
            quantity=add_request.quantity
        )
        cart_items.append(new_item)

    return {"message": f"Added {add_request.quantity} of product {add_request.product_id} to cart for user {add_request.user_id}"}


@app.get(
    "/cart/{user_id}",
    tags=["Cart"],
    response_model=List[ProductInOrder],
    summary="Get a user's cart"
)
def get_cart(user_id: int):
    cart = carts_db.get(user_id)
    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found for this user")
    return cart

@app.post(
    "/checkout/{user_id}",
    tags=["Orders"],
    response_model=CheckoutSummary,
    summary="Calculate checkout summary for a user's cart"
)
def checkout(user_id: int):
    if user_id not in users_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    cart_items = carts_db.get(user_id)
    if not cart_items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Cart not found for this user."
        )

    total_price = 0
    # Calculate the total price based on items in the cart
    for item in cart_items:
        product = products_db.get(item.product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {item.product_id} in cart not found."
            )
        
        # In a real app, you would also check for stock availability here before finalizing.
        total_price += product.price * item.quantity

    return CheckoutSummary(
        cart_items=cart_items, 
        total_price=total_price
    )
