import boto3
import json
import time
import random
from datetime import datetime
from faker import Faker

# --- Configuration ---
STREAM_NAME = "qsr-real-time-orders"
REGION = "us-east-1"
PROFILE = "qsr-dev" # Using your configured profile

# --- Setup ---
session = boto3.Session(profile_name=PROFILE, region_name=REGION)
kinesis = session.client('kinesis')
fake = Faker()

# --- Menu Data ---
MENU_ITEMS = [
    {"item": "Chicken Burger", "price": 5.50},
    {"item": "Cheese Burger", "price": 6.00},
    {"item": "Fries", "price": 2.50},
    {"item": "Soda", "price": 1.50},
    {"item": "Ice Cream", "price": 3.00},
    {"item": "Nuggets", "price": 4.50}
]

CITIES = ["New York", "Chicago", "San Francisco", "Austin", "Seattle", "Miami"]

def generate_order():
    """Create a random order"""
    choice = random.choice(MENU_ITEMS)
    
    order = {
        "order_id": fake.uuid4(),
        "customer_id": f"C{random.randint(100, 999)}",
        "item": choice["item"],
        "amount": choice["price"],
        "city": random.choice(CITIES),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return order

print(f"🌊 Starting stream to {STREAM_NAME}...")

try:
    while True:
        order = generate_order()
        
        # Send to Kinesis
        response = kinesis.put_record(
            StreamName=STREAM_NAME,
            Data=json.dumps(order),
            PartitionKey=order["city"] # Group by City for sharding
        )
        
        print(f"✅ Sent: {order['item']} (${order['amount']}) in {order['city']}")
        
        # Speed: 2 orders per second
        time.sleep(0.5)

except KeyboardInterrupt:
    print("\n🛑 Stream stopped.")