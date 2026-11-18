@echo off
REM iniciar_celery.bat - worker + Flower sin Docker
cd /d C:\Temp_Workspace_ERP

start "Celery Worker" cmd /k "call env_erp\Scripts\activate && celery -A core worker -l info -Q erp_django --pool=solo"
start "Flower" cmd /k "call env_erp\Scripts\activate && celery -A core flower --port=5555"