FROM python:3.11-slim
WORKDIR /workspace
COPY requirements/antigravity.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY antigravity ./antigravity
COPY config ./config
CMD ["python", "antigravity/sandbox.py", "--corpus", "config/task_library.json"]
