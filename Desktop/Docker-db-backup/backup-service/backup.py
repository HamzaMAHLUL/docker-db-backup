import docker
import schedule
import subprocess
import datetime
import time
import os
import threading
import mysql.connector
import json
from typing import List, Optional
from dataclasses import dataclass
# Global değişkenler
scheduled_jobs = {}
client = docker.from_env()  # global docker client

# Docker container'ları için veri yapısı
@dataclass
class DbItem:
    container_name: str
    host: str
    port: int
    user: str
    password: str
    backup_format: str
    backup_enabled: bool
    backup_folder: str  # <-- yeni alan
    backup_interval_hours: Optional[float] = None
    backup_times: Optional[List[str]] = None
    trigger_backup: bool = False  # Yeni alan: anlık yedekleme tetiklemesi için

#Container Bilgilerini Alma
def get_all_db_items() -> List[DbItem]:
    containers = client.containers.list(all=True)
    db_items = []

    for container in containers:
        labels = container.labels
        interval = labels.get("mybackup.backup_interval_hours")
        times = labels.get("mybackup.backup_times")
        trigger = labels.get("mybackup.trigger_backup", "false").lower() == "true"

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
            backup_folder=labels.get("mybackup.backup_folder", container.name),
            backup_interval_hours=backup_interval_hours,
            backup_times=backup_times,
            trigger_backup=trigger
        )
        db_items.append(db_item)
    return db_items
# MySQL veritabanını yedekleme fonksiyonu
def backup_mysql_database(db: DbItem):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d__%H-%M-%S") # Yedekleme zaman damgası
    folder_path = os.path.join("./backups", db.backup_folder)
    os.makedirs(folder_path, exist_ok=True) # Yedekleme klasörünü oluştur

    # # SQL Yedeği
    # if db.backup_format in ("sql", "both"):
    #     sql_file = os.path.join(folder_path, f"{db.container_name}_{timestamp}.sql")
    #     cmd = [
    #         "mysqldump",
    #         "-h", db.host,
    #         "-P", str(db.port),
    #         "-u", db.user,
    #         f"-p{db.password}",
    #         "--all-databases",
    #         "--routines",
    #         "--events",
    #         "--single-transaction",
    #         "--quick",
    #         "--lock-tables=false"
    #     ]
    #     try:
    #         print(f"[{db.container_name}] SQL yedeği alınıyor → {sql_file}")
    #         with open(sql_file, "w", encoding="utf-8") as f:
    #             subprocess.run(cmd, stdout=f, check=True)
    #         print(f"[{db.container_name}] SQL yedekleme tamamlandı.")
    #     except subprocess.CalledProcessError as e:
    #         print(f"[{db.container_name}] SQL yedekleme hatası: {e}")
    # else:
    #     print(f"[{db.container_name}] SQL yedekleme atlandı (format: {db.backup_format})")

    # JSON Yedeği
    if db.backup_format in ("json", "both"):
        json_file = os.path.join(folder_path, f"{db.container_name}_{timestamp}.json")
        try:
            print(f"[{db.container_name}] JSON yedeği alınıyor → {json_file}")
            conn = mysql.connector.connect(
                host=db.host,
                port=db.port,
                user=db.user,
                password=db.password
            )
            cursor = conn.cursor()
            cursor.execute("SHOW DATABASES")
            databases = cursor.fetchall()

            dump_data = {}

            for (database_name,) in databases:
                if database_name in ("information_schema", "performance_schema", "mysql", "sys"):
                    continue  # sistem veritabanlarını atla
                dump_data[database_name] = {}
                cursor.execute(f"USE `{database_name}`")
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                for (table_name,) in tables:
                    cursor.execute(f"SELECT * FROM `{table_name}`")
                    rows = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    table_data = [dict(zip(columns, row)) for row in rows]
                    dump_data[database_name][table_name] = table_data

            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(dump_data, f, indent=2, ensure_ascii=False)

            print(f"[{db.container_name}] JSON yedekleme tamamlandı.")
            cursor.close()
            conn.close()

        except Exception as e:
            print(f"[{db.container_name}] JSON yedekleme hatası: {e}")
    else:
        print(f"[{db.container_name}] JSON yedekleme atlandı (format: {db.backup_format})")

# Görevleri güncelleme
def update_scheduled_jobs():
    global scheduled_jobs
    current_db_items = get_all_db_items()
    current_names = {db.container_name for db in current_db_items}

    # Yeni containerlar için görev oluştur
    for db in current_db_items:
        if not db.backup_enabled:
            continue

        if db.container_name not in scheduled_jobs:
            scheduled_jobs[db.container_name] = []

            if db.backup_interval_hours:
                interval_minutes = int(db.backup_interval_hours * 60)
                job = schedule.every(interval_minutes).minutes.do(backup_mysql_database, db)
                scheduled_jobs[db.container_name].append(job)
                print(f"[Yeni] {db.container_name} → Her {interval_minutes} dakikada yedeklenecek.")

            if db.backup_times:
                for time_str in db.backup_times:
                    job = schedule.every().day.at(time_str).do(backup_mysql_database, db)
                    scheduled_jobs[db.container_name].append(job)
                    print(f"[Yeni] {db.container_name} → Her gün saat {time_str}'de yedeklenecek.")

    # Silinen container'ların görevlerini iptal et
    for name in list(scheduled_jobs.keys()):
        if name not in current_names:
            print(f"[Silindi] {name} konteyneri için görevler iptal ediliyor.")
            for job in scheduled_jobs[name]:
                schedule.cancel_job(job)
            del scheduled_jobs[name]

# Docker event dinleyicisi
def docker_event_listener():
    print("[EventListener] Docker event dinleyici başlatıldı.")
    for event in client.events(decode=True):
        # event dict içinde 'Type' ve 'Action' var
        if event.get("Type") == "container":
            action = event.get("Action", "")
            container_name = None

            # Container adı bazen "Actor.Attributes.name" altında olur
            actor = event.get("Actor", {})
            attributes = actor.get("Attributes", {})
            container_name = attributes.get("name")

            if container_name:
                if action in ("start", "create", "restart"):
                    print(f"[EventListener] Container başladı/oluşturuldu: {container_name}")
                    update_scheduled_jobs()  # Yeni container için güncelleme
                elif action in ("die", "stop", "destroy"):
                    print(f"[EventListener] Container durdu/silindi: {container_name}")
                    update_scheduled_jobs()  # Container silindi/kapandı, görevleri güncelle

# Anlık yedekleme tetikleyicisi
def trigger_immediate_backup():
    while True:
        db_items = get_all_db_items()
        for db in db_items:
            if db.backup_enabled and db.trigger_backup:
                print(f"[Trigger] Anlık yedekleme tetiklendi: {db.container_name}")
                backup_mysql_database(db)

                # Burada etiketi sıfırlamak veya kaldırmak için Docker API ile label değiştirme yapılabilir.
                # Örnek:
                try:
                    container = client.containers.get(db.container_name)
                    labels = container.labels.copy()
                    if "mybackup.trigger_backup" in labels:
                        labels["mybackup.trigger_backup"] = "false"
                        container.update(labels=labels)
                        print(f"[Trigger] {db.container_name} trigger_backup etiketi sıfırlandı.")
                except Exception as e:
                    print(f"[Trigger] Etiket sıfırlama hatası: {e}")

        time.sleep(10)  # 10 saniyede bir kontrol et 


# Scheduler döngüsü
def scheduler_loop():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    print("Backup servisi başlatıldı!")

    update_scheduled_jobs()

    # Scheduler thread
    threading.Thread(target=scheduler_loop, daemon=True).start()

    # Docker event dinleyici thread
    threading.Thread(target=docker_event_listener, daemon=True).start()

    # Anlık tetikleme kontrol thread
    threading.Thread(target=trigger_immediate_backup, daemon=True).start()

    while True:
        time.sleep(60)
