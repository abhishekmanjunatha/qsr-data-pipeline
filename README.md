## 🍔 QSR Real-Time Analytics Platform

![Status](https://img.shields.io/badge/Status-Active-success)
![Terraform](https://img.shields.io/badge/IaC-Terraform-purple)
![AWS](https://img.shields.io/badge/Cloud-AWS-orange)
![Airflow](https://img.shields.io/badge/Orchestration-Airflow-blue)
![Spark](https://img.shields.io/badge/Processing-PySpark-red)

A unified **Batch** and **Real-Time Streaming** data platform for Quick Service Restaurants (QSR).
This project ingests mock sales data, processes it using PySpark (AWS Glue), and stores it in a partitioned S3 Data Lake queryable via Athena.

---

## 🏗️ Architecture

The platform uses the **Medallion Architecture** for both batch CSV dumps and real-time JSON streams.

### **1. Bronze Layer (Ingestion)**

* **Batch:** Manual CSV uploads → `s3://.../raw/`
* **Streaming:** Python Producer → Kinesis Data Stream → Firehose → `s3://.../raw_stream/`

### **2. Silver Layer (Processing)**

* **AWS Glue:**

  * Cleans and normalizes data (`"new york"` → `"New York"`),
  * Adds metadata + lineage fields,
  * Writes partitioned output.
* **Airflow:**

  * **Sensors** detect batch file arrivals
  * **Schedules** trigger micro-batch streaming jobs

### **3. Gold Layer (Analytics)**

* **Athena:** Serverless SQL engine to query unified sales from both pipelines.

---

## 🛠️ Tech Stack

| Layer              | Tools                                        |
| ------------------ | -------------------------------------------- |
| **Infrastructure** | Terraform (VPC, EC2, S3, IAM, Kinesis, Glue) |
| **Orchestration**  | Apache Airflow (EC2)                         |
| **Compute**        | AWS Glue (Serverless Spark)                  |
| **Streaming**      | Kinesis Data Streams + Firehose              |
| **Language**       | Python 3.x (Boto3, PySpark)                  |

---

## 🚀 Setup Guide

### **Prerequisites**

* AWS CLI configured (`qsr-dev` profile)
* Terraform v1.0+
* Python 3.x

---

## **1. Deploy Infrastructure**

```bash
terraform init
terraform apply
```

Type **yes** when prompted.

---

## **2. Configure Airflow on EC2**

### **Connect to EC2**

#### Fix key permissions (Windows)

```powershell
icacls.exe qsr-key.pem /reset
icacls.exe qsr-key.pem /grant:r "$($env:USERNAME):(R)"
icacls.exe qsr-key.pem /inheritance:r
```

#### SSH into instance

```bash
ssh -i qsr-key.pem ubuntu@<ECEC_PUBLIC_IP>
```

---

### **Install Airflow**

```bash
sudo apt-get update && sudo apt-get install -y python3-pip python3-venv

python3 -m venv airflow_venv
source airflow_venv/bin/activate

pip install "apache-airflow==2.9.2" apache-airflow-providers-amazon \
  --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.9.2/constraints-3.12.txt"

airflow db migrate

airflow users create \
  --username admin \
  --firstname Admin \
  --lastname User \
  --role Admin \
  --email admin@example.com \
  --password admin

airflow webserver --port 8080 -D
airflow scheduler -D
```

---

## **3. Deploy DAGs**

Update bucket names according to Terraform outputs, then upload:

```bash
scp -i qsr-key.pem *.py ubuntu@<EC2_PUBLIC_IP>:~/airflow/dags/
```

---

## 🎮 How to Run

### **Batch Pipeline (Manual)**

1. Upload file:

   ```
   s3://<BUCKET_NAME>/raw/orders.csv
   ```
2. Airflow **S3KeySensor** detects arrival.
3. Sensor triggers AWS Glue job.
4. Data lands in:

   ```
   s3://.../clean/input_source=batch_manual/
   ```

---

### **Streaming Pipeline (Real-Time)**

Start the producer:

```bash
python producer.py
```

Flow:
**Producer → Kinesis → Firehose → S3 → Airflow → Glue**

Output stored in:

```
s3://.../clean/input_source=stream_kinesis/
```

---

## 📊 Analytics (Athena)

Example query:

```sql
SELECT 
  input_source,
  COUNT(*) AS total_orders,
  SUM(amount) AS revenue
FROM "qsr_analytics_db"."clean"
GROUP BY input_source;
```

---

## 💰 Cost Management (Pause Resources)

To stop streaming resources:

```bash
terraform destroy \
  -target="aws_kinesis_stream.order_stream" \
  -target="aws_kinesis_firehose_delivery_stream.s3_stream"
```

To stop compute cost:
→ **Stop EC2 instance** in AWS Console.

---
