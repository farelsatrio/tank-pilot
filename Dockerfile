# Base image Python 3.12
FROM python:3.12-slim

# Set working directory
WORKDIR /app


# Copy requirements dulu (untuk optimalisasi layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy seluruh aplikasi
COPY . .

# Expose port
EXPOSE 8000

# Jalankan aplikasi
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
