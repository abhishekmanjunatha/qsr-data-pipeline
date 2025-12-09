Set-Content -Path api_setup.sh -Value @"
#!/bin/bash
# 1. Install Dependencies
apt-get update
apt-get install -y python3-pip python3-venv

# 2. Setup App Directory
mkdir -p /home/ubuntu/api
cd /home/ubuntu/api

# 3. Create the Python API Code
cat <<EOF > mock_api.py
from flask import Flask, jsonify
from faker import Faker
import random
from datetime import datetime

app = Flask(__name__)
fake = Faker()

MENU = [
    {"item": "Double Cheeseburger", "category": "Burgers", "price_range": (8, 12)},
    {"item": "Spicy Chicken Wrap", "category": "Wraps", "price_range": (6, 9)},
    {"item": "Caesar Salad", "category": "Salads", "price_range": (10, 14)},
    {"item": "Large Fries", "category": "Sides", "price_range": (3, 5)},
    {"item": "Vanilla Shake", "category": "Drinks", "price_range": (4, 7)}
]

@app.route('/order', methods=['GET'])
def generate_order():
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
EOF

# 4. Setup Virtual Env & Run
python3 -m venv venv
source venv/bin/activate
pip install flask faker
nohup python mock_api.py > api.log 2>&1 &
"@