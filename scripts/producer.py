import boto3
import json
import time
import requests

# --- Configuration ---
STREAM_NAME = "qsr-real-time-orders"
REGION = "us-east-1"
# 👇 YOUR NEW API IP (The "Order System")
API_URL = "http://44.200.65.175:5000/order"

# Initialize Kinesis
kinesis = boto3.client('kinesis', region_name=REGION)

def get_live_order():
    """Fetches a real-time order from our custom API."""
    try:
        response = requests.get(API_URL, timeout=2)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"⚠️ API Error: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None

print(f"🚀 Connecting to Order System at {API_URL}...")
print(f"📡 Streaming to Kinesis: {STREAM_NAME}...")

while True:
    order = get_live_order()
    
    if order:
        # Send to Kinesis
        kinesis.put_record(
            StreamName=STREAM_NAME,
            Data=json.dumps(order),
            PartitionKey=order['category'] # Partition by Food Category
        )
        print(f"✅ [New Sale] {order['item']} (${order['amount']}) - {order['city']}")
    
    # Simulate realistic traffic (2 orders per second)
    time.sleep(0.5)