from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
from airflow.operators.dummy import DummyOperator
from datetime import datetime, timedelta
from kubernetes.client import models as k8s
from kubernetes.client import V1Volume, V1VolumeMount, V1HostPathVolumeSource

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
    'retries': 3,
    'retry_delay': timedelta(minutes=15),
}

# Define DAG
with DAG(
    'K8S-FLINK-CONSUMER',
    default_args=default_args,
    description='A pipeline to process meme coin sentiments from Reddit using Kafka & Flink',
    schedule_interval= None,
    start_date=datetime.now(),
    catchup=False,
    tags=['meme', 'coins', 'sentiment'],
) as dag:

    # Dummy start task
    start = DummyOperator(task_id='start')

    submit_flink_job = KubernetesPodOperator(
        task_id='submit_flink_job',
        name='flink-job-submitter',
        namespace='crypto-gamble',
        image='flink-consumer:latest',
        image_pull_policy='Never',
        cmds=['/bin/bash', '-c'],
        arguments=[
            '/opt/flink/bin/flink run '
            '-m jobmanager.crypto-gamble.svc.cluster.local:8081 '
            '-py /opt/flink_consumer/src/jobs/flink_kafka_consumer.py '
            '--pyFiles /opt/flink_consumer/usrlib/ -d '
        ],
        env_vars={
            # "FLINK_PROPERTIES": "jobmanager.rpc.address=jobmanager.crypto-gamble.svc.cluster.local\nparallelism.default=8",
            "FLINK_PARALLELISM": "3", # Default to 1
            # "FLINK_AUTO_OFFSET" :  "earliest", # Can change between earliest and latest # Default to earliest
            # "FLINK_SCAN_STARTUP_MODE" : "earliest-offset", # Can change between earliest-offset and latest-offset # Default to earliest-offset
            # "POSTGRES_URL": "jdbc:postgresql://postgres.crypto-gamble.svc.cluster.local:5432/reddit",
            # "POSTGRES_USER": "postgres",
            # "POSTGRES_PASSWORD": "postgres",
            # "POSTGRES_DB": "postgres",
            # "REDDIT_DATABASE": "reddit",
            # "REDDIT_POSTS_TABLE": "reddit_posts",
            # "KAFKA_BROKER": "kafka.crypto-gamble.svc.cluster.local:9092",
            # "KAFKA_TOPIC": "reddit-topic",
            # "KAFKA_GROUP_ID": "reddit-consumer-group",
            # "KAFKA_SOURCE_TABLE": "reddit_source",
        },
        labels={"app": "flink-jobmanager"},
        is_delete_operator_pod=True,
        in_cluster=True,
        get_logs=True,
        # volumes=[host_path_volume], # Mount Volume to develop
        # volume_mounts=[volume_mount], # 
    )

    # Dummy end task
    end = DummyOperator(task_id='end')

    # Define dependencies
    start >> submit_flink_job >> end
