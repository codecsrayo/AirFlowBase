from airflow import DAG
from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.contrib.hooks.ssh_hook import SSHHook
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from datetime import datetime
import time
import logging

logger = logging.getLogger(__name__)

default_args = {
    "owner": "knime_demo",
    "start_date": datetime(2024, 2, 6),
}

dag = DAG(
    dag_id="ssh_demo",
    default_args=default_args,
    schedule_interval=None,
    # schedule_interval="0 10 * * *",  # The DAG will run at 5:00 am Colombian time (10:00 am UTC) every day
)

start_task = DummyOperator(
    task_id="start_task",
    dag=dag,
)


def ssh_start_service(**kwargs):
    command = "echo '12345' | sudo -S systemctl start knime.test.service"

    ssh_hook = SSHHook(ssh_conn_id="ssh_demo_local", cmd_timeout=None)
    ssh_conn = ssh_hook.get_conn()

    assert ssh_conn.exec_command(command)


ssh_start_services_task = PythonOperator(
    task_id="ssh_start_service",
    python_callable=ssh_start_service,
    provide_context=True,
    dag=dag,
)   




def check_service_status(**kwargs):
    check_status_command = "echo '12345' | sudo -S  systemctl is-active knime.test.service"

    ssh_hook = SSHHook(ssh_conn_id="ssh_demo_local", cmd_timeout=None)
    logger.info(ssh_hook)
    ssh_conn = ssh_hook.get_conn()
    logger.info(ssh_conn)

    while True:
        stdin, stdout, stderr = ssh_conn.exec_command(check_status_command)
        status_output = stdout.read().decode("utf-8").strip()

    
        if status_output == 'inactive':
            logger.info("Service has stopped.")
            break

        logger.warning(f"Service status is {status_output}. Retrying in 10 seconds.")
        time.sleep(10)


check_status_task_init = PythonOperator(
    task_id="check_status_task_init",
    python_callable=check_service_status,
    provide_context=True,
    dag=dag,
)

check_status_task = PythonOperator(
    task_id="check_status_task",
    python_callable=check_service_status,
    provide_context=True,
    dag=dag,
)

end_task = DummyOperator(
    task_id="end_task",
    dag=dag,
)

start_task >> check_status_task_init  >> ssh_start_services_task >> check_status_task >> end_task