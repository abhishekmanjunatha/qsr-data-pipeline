from airflow import DAG
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
from datetime import datetime

# 1. Define default arguments (who owns it, when to retry)
default_args = {
    'owner': 'airflow',
    'start_date': datetime(2023, 1, 1),
    'retries': 0
}

# 2. Define the DAG
with DAG('01_s3_sensor_dag',
         default_args=default_args,
         schedule_interval='@daily',
         catchup=False) as dag:

    # 3. Define the Task: Wait for orders.csv
    wait_for_file = S3KeySensor(
        task_id='wait_for_s3_file',
        bucket_name='qsr-data-lake-a4857ac9', # <--- VERIFY THIS MATCHES YOUR BUCKET
        bucket_key='raw/orders.csv',
        aws_conn_id='aws_default', # Airflow uses this to talk to S3
        poke_interval=10,          # Check every 10 seconds
        timeout=600                # Fail if file not found after 10 mins
    )
