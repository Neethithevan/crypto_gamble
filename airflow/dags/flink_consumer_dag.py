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
    'retries': 3,
    'retry_delay': timedelta(minutes=15),
}

# Define DAG
with DAG(
    'K8S-FLINK-CONSUMER',
    default_args=default_args,
    description='A pipeline to process meme coin sentiments from Reddit using Kafka & Flink',
    schedule= None,
    start_date=datetime.now(),
    catchup=False,
    tags=['meme', 'coins', 'sentiment'],
) as dag:

    # Empty start task
    start = EmptyOperator(task_id='start')

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
            "FLINK_PARALLELISM": "3", # Default to 1
        },
        labels={"app": "flink-jobmanager"},
        is_delete_operator_pod=True,
        get_logs=True,
        # volumes=[host_path_volume], # Mount Volume to develop
        # volume_mounts=[volume_mount], # 
    )

    # Empty end task
    end = EmptyOperator(task_id='end')

    # Define dependencies
    start >> submit_flink_job >> end
