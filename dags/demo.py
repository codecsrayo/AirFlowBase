from airflow import DAG
from airflow.contrib.operators.ssh_operator import SSHOperator
from airflow.contrib.hooks.ssh_hook import SSHHook
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from datetime import datetime
import time
import logging

logger = logging.getLogger(__name__)


ROOT_COMMAND = "echo '12345' | sudo -S "
SERVICE_NAME = 'knime.test.service'
SHH_ID_CONNECT = 'ssh_demo_local'
OWNER= 'knime_demo'
DAG_NAME= 'ssh_demo'
GROUP = ['example']

default_args = {
    "owner": OWNER,
    "start_date": datetime(2024, 2, 6),
}

dag = DAG(
    dag_id=DAG_NAME,
    default_args=default_args,
    schedule_interval=None,
    # schedule_interval="0 10 * * *",  # The DAG will run at 5:00 am Colombian time (10:00 am UTC) every day
    tags=GROUP,
)

start_task = DummyOperator(
    task_id="start_task",
    dag=dag,
)



def service_stop(**kwargs):
    check_status_command = f"{ROOT_COMMAND} systemctl stop {SERVICE_NAME}"

    ssh_hook = SSHHook(ssh_conn_id=SHH_ID_CONNECT, cmd_timeout=None)
    logger.info(ssh_hook)
    ssh_conn = ssh_hook.get_conn()
    logger.info(ssh_conn)
    assert ssh_conn.exec_command(check_status_command)


def ssh_start_service(**kwargs):
    command = f"{ROOT_COMMAND} systemctl start {SERVICE_NAME}"

    ssh_hook = SSHHook(ssh_conn_id=SHH_ID_CONNECT, cmd_timeout=None)
    ssh_conn = ssh_hook.get_conn()

    assert ssh_conn.exec_command(command)


 




def check_service_status(**kwargs):
    check_status_command = f"{ROOT_COMMAND} systemctl is-active {SERVICE_NAME}"

    ssh_hook = SSHHook(ssh_conn_id=SHH_ID_CONNECT, cmd_timeout=None)
    ssh_conn = ssh_hook.get_conn()

    while True:
        stdin, stdout, stderr = ssh_conn.exec_command(check_status_command)
        status_output = stdout.read().decode("utf-8").strip()

    
        if status_output == 'inactive':
            check_status_command = f'{ROOT_COMMAND}  journalctl -u  {SERVICE_NAME} --since "12 hour ago"'
            stdin, stdout, stderr = ssh_conn.exec_command(check_status_command)
            status_output = stdout.read().decode("utf-8").strip()
            logger.info(status_output)
            break

        logger.warning(f"Service status is {status_output}. Retrying in 10 seconds.")
        time.sleep(10)






check_status_task_init = PythonOperator(
    task_id="is_running_else_stop",
    python_callable=service_stop,
    provide_context=True,
    dag=dag,
)

ssh_start_services_task = PythonOperator(
    task_id="start_service",
    python_callable=ssh_start_service,
    provide_context=True,
    dag=dag,
)  
check_status_task = PythonOperator(
    task_id="check_is_running",
    python_callable=check_service_status,
    provide_context=True,
    dag=dag,
)

end_task = DummyOperator(
    task_id="end_task",
    dag=dag,
)

start_task >> check_status_task_init  >> ssh_start_services_task >> check_status_task >> end_task