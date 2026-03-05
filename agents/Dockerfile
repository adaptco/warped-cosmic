FROM python:3.11-slim
WORKDIR /workspace
ENV LLM_TARGET=gemini
ENV MODEL_ID=
ENV OLLAMA_HOST=http://localhost:11434
COPY requirements/agents.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY agents ./agents
CMD ["python", "agents/avatar_codegen_agent.py"]
