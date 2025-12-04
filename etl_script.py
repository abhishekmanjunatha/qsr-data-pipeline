import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import col, initcap, current_timestamp, lit

# 1. Initialize Glue
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'bucket_name', 'source_key', 'format'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# 2. Variables
bucket_name = args['bucket_name']
source_key = args['source_key']
data_format = args['format'] 

source_path = f"s3://{bucket_name}/{source_key}"
target_path = f"s3://{bucket_name}/clean/"

# 3. Read Data & Assign Lineage
if data_format == 'csv':
    # Batch Pipeline
    df = spark.read.option("header", "true").option("inferSchema", "true").csv(source_path)
    source_tag = "batch_manual"
else:
    # Streaming Pipeline
    df = spark.read.option("recursiveFileLookup", "true").json(source_path)
    source_tag = "stream_kinesis"

# 4. Transformations (Now adding 'input_source' column)
df_clean = df.withColumn("city", initcap(col("city"))) \
             .withColumn("amount", col("amount").cast("double")) \
             .withColumn("processed_at", current_timestamp()) \
             .withColumn("input_source", lit(source_tag)) # <--- NEW METADATA COLUMN

# 5. Write Data (Consolidated)
# We partition by source so you can physically see the separation if you browse S3,
# but logically they are in the same dataset.
df_clean.write.mode("append").partitionBy("input_source").parquet(target_path)

job.commit()