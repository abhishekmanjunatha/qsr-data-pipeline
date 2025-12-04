from airflow import DAG
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator
from datetime import datetime

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2023, 1, 1),
    'retries': 1
}

with DAG('02_end_to_end_pipeline',
         default_args=default_args,
         schedule_interval='@daily',
         catchup=False) as dag:

    # 1. Wait for the file to land
    wait_for_file = S3KeySensor(
        task_id='wait_for_raw_data',
        bucket_name='qsr-data-lake-14a75b64', # <--- VERIFY YOUR BUCKET NAME
        bucket_key='raw/orders.csv',
        aws_conn_id='aws_default',
        poke_interval=10,
        timeout=600
    )

    # 2. Trigger the Glue Job (Updated with arguments)
    trigger_glue = GlueJobOperator(
        task_id='trigger_glue_job',
        job_name='qsr-clean-orders-job',
        script_args={
            '--bucket_name': 'qsr-data-lake-14a75b64', # <--- YOUR BUCKET HERE
            '--source_key': 'raw/orders.csv',          # Point to specific CSV
            '--format': 'csv'                          # Tell Spark it is CSV
        },
        aws_conn_id='aws_default',
        region_name='us-east-1',
        wait_for_completion=True
    )

    # 3. Define Dependency
    wait_for_file >> trigger_glue