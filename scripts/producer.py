import boto3
import json
import time
import requests
import random
from datetime import datetime

# --- Configuration ---
STREAM_NAME = "qsr-real-time-orders"
REGION = "us-east-1"

# 👇 PASTE YOUR STATIC INSTANCE ID HERE (The one you just copied)
MOCK_API_ID = "i-01efee8954b0cca1b" 

# Initialize Clients
kinesis = boto3.client('kinesis', region_name=REGION)
ec2 = boto3.client('ec2', region_name=REGION)

def get_dynamic_api_url():
    """Asks AWS for the current Public IP of the API Server."""
    try:
        # Find the server by its Static ID
        response = ec2.describe_instances(InstanceIds=[MOCK_API_ID])
        
        # Extract the Public IP
        instance = response['Reservations'][0]['Instances'][0]
        public_ip = instance.get('PublicIpAddress')
        
        if not public_ip:
            print("⚠️ Server is running but has no Public IP yet.")
            return None
            
        return f"http://{public_ip}:5000/order"
        
    except Exception as e:
        print(f"❌ Failed to find API Server IP: {e}")
        return None

print(f"🔍 Looking for API Server (ID: {MOCK_API_ID})...")
API_URL = get_dynamic_api_url()

if API_URL:
    print(f"🚀 Found Order System at: {API_URL}")
    print(f"📡 Streaming to Kinesis: {STREAM_NAME}...")

    while True:
        try:
            response = requests.get(API_URL, timeout=2)
            if response.status_code == 200:
                order = response.json()
                
                # Send to Kinesis
                kinesis.put_record(
                    StreamName=STREAM_NAME,
                    Data=json.dumps(order),
                    PartitionKey=order['category']
                )
                print(f"✅ [New Sale] {order['item']} (${order['amount']}) - {order['city']}")
            else:
                print(f"⚠️ API Error: {response.status_code}")
        except Exception as e:
            print(f"❌ Connection Error: {e}")
            # If connection fails, maybe IP changed? Refresh it.
            time.sleep(5)
            API_URL = get_dynamic_api_url() 
        
        # Throttle
        time.sleep(0.5)
else:
    print("❌ Could not find API Server. Is it running?")