FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set environment variable - defaults to development, overridable during build
ARG ENVIRONMENT=development
ENV ENVIRONMENT=${ENVIRONMENT}

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]