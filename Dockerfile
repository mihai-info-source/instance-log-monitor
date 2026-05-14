FROM python:3.11-slim
WORKDIR /app
COPY instance_health_monitor.py .
RUN chmod +x instance_health_monitor.py
RUN mkdir -p /opt/apps/Company
ENTRYPOINT ["python3", "instance_health_monitor.py"]
