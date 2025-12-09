from flask import Flask, jsonify
from faker import Faker
import random
from datetime import datetime

app = Flask(__name__)
fake = Faker()

# Menu Config
MENU = [
    {"item": "Double Cheeseburger", "category": "Burgers", "price_range": (8, 12)},
    {"item": "Spicy Chicken Wrap", "category": "Wraps", "price_range": (6, 9)},
    {"item": "Caesar Salad", "category": "Salads", "price_range": (10, 14)},
    {"item": "Large Fries", "category": "Sides", "price_range": (3, 5)},
    {"item": "Vanilla Shake", "category": "Drinks", "price_range": (4, 7)}
]

@app.route('/order', methods=['GET'])
def generate_order():
    """Returns a single realistic random order."""
    choice = random.choice(MENU)
    
    order = {
        "order_id": fake.uuid4(),
        "customer_id": fake.bothify(text='CUST-####'),
        "name": fake.name(),
        "item": choice["item"],
        "category": choice["category"],
        "amount": round(random.uniform(*choice["price_range"]), 2),
        "city": random.choice(["New York", "Chicago", "San Francisco", "Austin", "Seattle"]),
        "payment_method": random.choice(["Credit Card", "Apple Pay", "Cash"]),
        "timestamp": datetime.now().isoformat()
    }
    return jsonify(order)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "live", "service": "QSR-POS-System"})

if __name__ == '__main__':
    # host='0.0.0.0' makes it accessible from the internet
    app.run(host='0.0.0.0', port=5000)