from airflow import DAG
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2023, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}

# Schedule: Run every hour to process the stream backlog
with DAG('03_process_stream_data',
         default_args=default_args,
         schedule_interval='@hourly',
         catchup=False) as dag:

    trigger_glue_stream = GlueJobOperator(
        task_id='trigger_glue_stream',
        job_name='qsr-clean-orders-job',
        script_args={
            '--bucket_name': 'qsr-data-lake-14a75b64', # <--- YOUR BUCKET HERE
            '--source_key': 'raw_stream/',             # Point to Kinesis dump
            '--format': 'json'                         # Tell Spark it is JSON
        },
        aws_conn_id='aws_default',
        region_name='us-east-1',
        wait_for_completion=True
    )