import docker
import schedule
import subprocess
import datetime
import time
import os
from typing import List, Optional
from dataclasses import dataclass

# Veritabanı yapı modeli
@dataclass
class DbItem:
    container_name: str
    host: str
    port: int
    user: str
    password: str
    backup_format: str
    backup_enabled: bool
    backup_interval_hours: Optional[float] = None
    backup_times: Optional[List[str]] = None  # Belirli saatler: ["17:00", "19:00"]

# Docker etiketlerinden yedeklenebilir veritabanlarını çek
def get_all_db_items() -> List[DbItem]:
    client = docker.from_env()
    containers = client.containers.list(all=True)
    db_items = []

    for container in containers:
        labels = container.labels

        interval = labels.get("mybackup.backup_interval_hours")
        times = labels.get("mybackup.backup_times")

        backup_interval_hours = float(interval) if interval else None
        backup_times = [t.strip() for t in times.split(",")] if times else None

        db_item = DbItem(
            container_name=container.name,
            host=labels.get("mybackup.host", "localhost"),
            port=int(labels.get("mybackup.port", 3306)),
            user=labels.get("mybackup.user", "root"),
            password=labels.get("mybackup.password", ""),
            backup_format=labels.get("mybackup.backup_format", "sql"),
            backup_enabled=labels.get("mybackup.enable", "false").lower() == "true",
            backup_interval_hours=backup_interval_hours,
            backup_times=backup_times
        )

        db_items.append(db_item)

    return db_items

# mysqldump ile yedek alma
def backup_mysql_database(db: DbItem):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    folder_path = os.path.join("./backups", db.container_name)
    os.makedirs(folder_path, exist_ok=True)

    if db.backup_format in ("sql", "both"):
        sql_file = os.path.join(folder_path, f"{db.container_name}_{timestamp}.sql")
        cmd = [
            "mysqldump",
            "-h", db.host,
            "-P", str(db.port),
            "-u", db.user,
            f"-p{db.password}",
            "--all-databases",
            "--routines",
            "--events",
            "--single-transaction",
            "--quick",
            "--lock-tables=false"
        ]

        try:
            print(f"Yedek alınıyor → {sql_file}")
            with open(sql_file, "w", encoding="utf-8") as f:
                subprocess.run(cmd, stdout=f, check=True)
            print(f"{db.container_name}: Yedekleme tamamlandı.")
        except subprocess.CalledProcessError as e:
            print(f"{db.container_name}: Yedekleme hatası: {e}")
    else:
        print(f"{db.container_name}: SQL yedekleme atlandı (format: {db.backup_format})")

# Yedekleme görevlerini zamanla
def schedule_backups(db_items: List[DbItem]):
    for db in db_items:
        if db.backup_enabled:
            # Zaman aralığına göre
            if db.backup_interval_hours is not None:
                interval_minutes = int(db.backup_interval_hours * 60)
                schedule.every(interval_minutes).minutes.do(backup_mysql_database, db)
                print(f"{db.container_name} → Her {interval_minutes} dakikada yedeklenecek.")
            
            # Belirli saatlerde
            if db.backup_times:
                for time_str in db.backup_times:
                    schedule.every().day.at(time_str).do(backup_mysql_database, db)
                    print(f"{db.container_name} → Her gün saat {time_str}'de yedeklenecek.")
        else:
            print(f"{db.container_name}: Yedekleme devre dışı.")

    print("\nOtomatik yedekleme zamanlayıcısı başlatıldı...\n")
    while True:
        schedule.run_pending()
        time.sleep(10)

# Ana fonksiyon
if __name__ == "__main__":
    print("Docker içindeki yedeklenebilir veritabanları:")
    db_items = get_all_db_items()
    for item in db_items:
        print(
            f"{item.container_name} - Host: {item.host}, Port: {item.port}, "
            f"Enabled: {item.backup_enabled}, Interval (h): {item.backup_interval_hours}, "
            f"Times: {item.backup_times}"
        )

    schedule_backups(db_items)
