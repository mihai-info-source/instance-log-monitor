FROM python:3.11-slim
WORKDIR /app
COPY instance_health_monitor.py .
RUN mkdir -p /opt/apps/Company/Instance1_LTD/logs && \
    touch /opt/apps/Company/Instance1_LTD/logs/sync.log
RUN chmod +x instance_health_monitor.py
ENTRYPOINT ["python3", "instance_health_monitor.py", "--base-dir", "/opt/apps/Company"]
