FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY docs /app/docs
COPY prompt.py ingest.py main.py /app/

ENV MOCK_LLM=1
ENV PYTHONUNBUFFERED=1

# Build-time ingestion creates the local Chroma collection inside the image.
RUN python ingest.py

EXPOSE 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
