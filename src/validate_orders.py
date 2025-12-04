import sys
import boto3
import pandas as pd
import great_expectations as gx
from io import BytesIO

# --- Configuration ---
BUCKET_NAME = "qsr-data-lake-14a75b64" # <--- UPDATE THIS
KEY = "raw/orders.csv"

def validate_data():
    print("⬇️ Downloading data from S3...")
    s3 = boto3.client('s3')
    obj = s3.get_object(Bucket=BUCKET_NAME, Key=KEY)
    df = pd.read_csv(BytesIO(obj['Body'].read()))
    print(f"✅ Loaded {len(df)} rows.")

    # --- Setup Great Expectations ---
    context = gx.get_context()
    
    # Create a temporary validator for this dataframe
    validator = context.sources.add_pandas("my_pandas_datasource").read_dataframe(
        df, asset_name="orders_csv"
    )

    # --- Define Rules (Expectations) ---
    print("🕵️ Running Validation Checks...")
    
    # Rule 1: Order ID must exist (Critical)
    validator.expect_column_values_to_not_be_null("order_id")
    
    # Rule 2: Amount must be positive money
    validator.expect_column_values_to_be_between("amount", min_value=0.01, max_value=1000)
    
    # Rule 3: City must be a valid location (Catch typos like "Maimi")
    # Note: We are flexible with case (New York vs new york) because Glue fixes that,
    # but we reject completely wrong cities.
    valid_cities = ["New York", "new york", "NY", "Chicago", "chicago", "San Francisco", "Austin", "Seattle", "Miami"]
    validator.expect_column_values_to_be_in_set("city", valid_cities)

    # --- Run Validation ---
    checkpoint = validator.validate()
    
    if not checkpoint["success"]:
        print("❌ Data Quality Check FAILED!")
        print(checkpoint)
        sys.exit(1) # Fail the Airflow Task
    
    print("✅ All Data Quality Checks PASSED.")
    sys.exit(0) # Success

if __name__ == "__main__":
    validate_data()
