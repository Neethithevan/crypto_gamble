from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from airflow.operators.empty import EmptyOperator
from datetime import datetime, timedelta
"""
# Example of resource declaration
compute_resources=k8s.V1ResourceRequirements(
    limits={
        'memory': '8Gi',
        'cpu': '2000m'
    },
    requests={
        'memory': '4Gi',
        'cpu': '1000m'
    }
)

# Host Volume for development
host_path_volume = V1Volume(
   name='flink-volume',
   host_path=V1HostPathVolumeSource(
       path='/mnt/data/flink_consumer/',  # Path on the host
       type='DirectoryOrCreate'  # Creates the directory if it doesn't exist
   )
)

volume_mount = V1VolumeMount(
   name='flink-volume',
   mount_path='/opt/flink_consumer'  # Path inside the pod
)
"""


# Default DAG arguments
default_args = {
    'owner': 'default',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=30),
}

# Define DAG
with DAG(
    'K8S-KAFKA-PRODUCER',
    default_args=default_args,
    description='A pipeline to process meme coin sentiments from Reddit using Kafka & Flink',
    schedule= "*/15 * * * *",  # Runs every 15 minutes
    start_date=datetime.now(),
    catchup=False,
    tags=['meme', 'coins', 'sentiment'],
) as dag:

    # Empty start task
    start = EmptyOperator(task_id='start')

    # Task: Kafka Producer as a Kubernetes Pod
    kafka_producer_task = KubernetesPodOperator(
        task_id="kafka_producer",
        name="kafka-producer-pod",
        namespace="crypto-gamble",
        image="kafka-producer:latest",
        image_pull_policy="Never",
        cmds=["python", "producer.py", "--limit", "1000"],
        # cmds= ["python", "producer.py", "--limit", "1000", "--subreddits","cryptocurrency,bitcoin"], # Example of passing arguments
            
        # },
        labels={"app": "kafka-producer"},
        is_delete_operator_pod=True,
        get_logs=True,
    )
 
    # Empty end task
    end = EmptyOperator(task_id='end')

    # Define dependencies
    start >> kafka_producer_task >> end

