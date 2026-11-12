FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir paho-mqtt==2.1.0 psutil==6.1.0
COPY *.py ./
CMD ["python", "-u", "device_agent.py"]
