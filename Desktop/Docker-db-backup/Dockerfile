# Temel Python görüntüsü
FROM python:3.10-slim

# Sistem güncelleme ve gerekli araçlar
RUN apt-get update && \
    apt-get install -y default-mysql-client && \
    pip install docker schedule mysql-connector-python && \
    apt-get clean

# Uygulama dosyalarını kopyala
WORKDIR /app
COPY . /app

# Yedek klasörünü oluştur
RUN mkdir -p /app/backups

# Scripti çalıştır
CMD ["python", "backup.py"]
