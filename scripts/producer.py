import boto3
import json
import time
import requests
import random
from datetime import datetime

# --- Configuration ---
STREAM_NAME = "qsr-real-time-orders"
REGION = "us-east-1"
API_URL = "https://www.themealdb.com/api/json/v1/1/random.php"

# Initialize Kinesis
kinesis = boto3.client('kinesis', region_name=REGION)

def get_real_food_order():
    """Fetches a random real meal from TheMealDB to simulate an order."""
    try:
        response = requests.get(API_URL)
        if response.status_code == 200:
            data = response.json()['meals'][0]
            
            # Create a realistic order object
            order = {
                "order_id": data['idMeal'],            # Real DB ID
                "item": data['strMeal'],               # Real Meal Name
                "category": data['strCategory'],       # e.g., Seafood, Vegan
                "cuisine": data['strArea'],            # e.g., Italian, Japanese
                "amount": round(random.uniform(8.00, 25.00), 2), # Simulated Price
                "city": random.choice(["New York", "London", "Tokyo", "Mumbai", "Paris"]),
                "timestamp": datetime.now().isoformat()
            }
            return order
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

print(f"🚀 Starting Stream to {STREAM_NAME}...")

while True:
    order = get_real_food_order()
    
    if order:
        # Send to Kinesis
        kinesis.put_record(
            StreamName=STREAM_NAME,
            Data=json.dumps(order),
            PartitionKey=order['category'] # Partition by Food Category
        )
        print(f"✅ Sent: {order['item']} (${order['amount']}) - {order['cuisine']}")
    
    # Throttle (TheMealDB is free, let's be nice)
    time.sleep(1)