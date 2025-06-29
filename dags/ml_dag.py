from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2024, 1, 1),
}

dag = DAG(
    'velib_data_pipeline',
    default_args=default_args,
    description='DAG ingestion info & status, processing et ML PySpark Velib',
    schedule_interval='@hourly',
    catchup=False
)

data_ingestion_info = BashOperator(
    task_id='data_ingestion_info',
    bash_command='python /app/Scripts/data-ingestion/Station_information_producer.py',
    dag=dag
)

data_ingestion_status = BashOperator(
    task_id='data_ingestion_status',
    bash_command='python /app/Scripts/data-ingestion/Station_status_producer.py',
    dag=dag
)

data_processing = BashOperator(
    task_id='data_processing',
    bash_command=(
        'spark-submit '
        '--conf spark.metrics.conf=/opt/spark/conf/metrics.properties '
        '--conf spark.ui.prometheus.enabled=true '
        '--conf spark.ui.prometheus.port=4041 '
        '--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0,org.mongodb.spark:mongo-spark-connector_2.12:10.1.1 '
        '/app/Scripts/data-transformation/main_transformation.py'
    ),
    dag=dag
)

run_ml_predict_bikes = BashOperator(
    task_id='run_ml_predict_bikes',
    bash_command=(
        'spark-submit '
        '--conf spark.metrics.conf=/opt/spark/conf/metrics.properties '
        '--conf spark.ui.prometheus.enabled=true '
        '--conf spark.ui.prometheus.port=4042 '
        '--packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0,org.mongodb.spark:mongo-spark-connector_2.12:10.1.1 '
        '/app/Scripts/ML_model/predict_bikes.py'
    ),
    dag=dag
)

[data_ingestion_info, data_ingestion_status] >> data_processing >> run_ml_predict_bikes
