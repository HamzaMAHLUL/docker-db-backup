FROM python:3.10-slim 
# Python 3.10 tabanlı bir imaj kullanıyorum

# Gerekli araçları yükle
RUN apt-get update && \
    apt-get install -y default-mysql-client && \
    pip install docker schedule mysql-connector-python && \
    apt-get clean

# Çalışma dizini ve dosyaları kopyala
WORKDIR /app
COPY . /app

# Scripti başlat
CMD ["python", "backup.py"]
