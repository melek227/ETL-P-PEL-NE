from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash_operator import BashOperator

default_args = {
    'owner': 'etl-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,  # Retry'yi kapat
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'simple_test_dag',
    default_args=default_args,
    description='Simple working test DAG',
    schedule_interval=None,  # Manual trigger only
    catchup=False,
    max_active_runs=1,
    tags=['test', 'simple']
)

# Simple bash tasks
task1 = BashOperator(
    task_id='task_1',
    bash_command='echo "Task 1 başarılı! ETL Pipeline çalışıyor."',
    dag=dag
)

task2 = BashOperator(
    task_id='task_2',
    bash_command='echo "Task 2 başarılı! PostgreSQL bağlantısı hazır."',
    dag=dag
)

task3 = BashOperator(
    task_id='task_3',
    bash_command='echo "Task 3 başarılı! ETL Pipeline tamamlandı!"',
    dag=dag
)

# Simple flow
task1 >> task2 >> task3