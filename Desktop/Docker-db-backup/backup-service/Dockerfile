FROM python:3.10-slim 
# Python 3.10 tabanlı bir imaj kullanıyorum

# Gerekli araçları yükle ve saat dilimini Istanbul olarak ayarla
ENV TZ=Europe/Istanbul

RUN apt-get update && \
    apt-get install -y default-mysql-client tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    pip install docker schedule mysql-connector-python && \
    apt-get clean

# Çalışma dizini ve dosyaları kopyala
WORKDIR /app
COPY . /app

# Scripti başlat
CMD ["python", "-u" , "backup.py"]
