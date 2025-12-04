from airflow import DAG
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator
from airflow.operators.bash import BashOperator # <--- NEW IMPORT
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

    # 1. Wait for file
    wait_for_file = S3KeySensor(
        task_id='wait_for_raw_data',
        bucket_name='qsr-data-lake-f2ee1900', # <--- VERIFY THIS
        bucket_key='raw/orders.csv',
        aws_conn_id='aws_default',
        poke_interval=10,
        timeout=600
    )

    # 2. Quality Gate (NEW)
    # We use the full path to the python executable in the virtualenv
    validate_data = BashOperator(
        task_id='validate_data_quality',
        bash_command='/home/ubuntu/airflow_venv/bin/python /home/ubuntu/airflow/dags/validate_orders.py',
        retries=0
    )

    # 3. Trigger Glue (Only if Validation Passes)
    trigger_glue = GlueJobOperator(
        task_id='trigger_glue_job',
        job_name='qsr-clean-orders-job',
        script_args={
            '--bucket_name': 'qsr-data-lake-f2ee1900', # <--- VERIFY THIS
            '--source_key': 'raw/orders.csv',
            '--format': 'csv'
        },
        aws_conn_id='aws_default',
        region_name='us-east-1',
        wait_for_completion=True
    )

    # 4. Define Flow
    wait_for_file >> validate_data >> trigger_glue
