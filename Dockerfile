FROM python:3.11-slim

WORKDIR /app

# Copy the script (make sure the file name is the correct one from your repo)
# Copiem scriptul (asigură-te că numele fișierului este cel corect din repo-ul tău)
COPY Company_monitor.py .

# We create the directory structure and a test instance directly in the container
# This allows the script to run successfully without external configuration
# Creăm structura de directoare și o instanță de test direct în container
# Asta permite scriptului să ruleze cu succes fără configurări externe
RUN mkdir -p /opt/apps/Company/Instance1_LTD/logs && \
    touch /opt/apps/Company/Instance1_LTD/logs/sync.log

# We grant execution rights
# Acordăm drepturi de execuție
RUN chmod +x Company_monitor.py

# We run the script indicating the internal location of the data
# Rulăm scriptul indicând locația internă a datelor
ENTRYPOINT ["python3", "Company_monitor.py", "--base-dir", "/opt/apps/Company"]
