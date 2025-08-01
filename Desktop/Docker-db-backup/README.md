
# 🐳 Docker-DB-Backup

A lightweight, automatic MySQL database backup system running inside a Docker environment.  
This solution scans all Docker containers for specific backup labels and periodically backs up enabled MySQL databases in `.sql` or `.csv` format — or both.

---

## 📦 Features

- 🔍 **Auto-discovery** of databases via Docker labels
- 🕓 **Per-database custom intervals** (e.g. every 30 minutes, hourly, daily)
- 📁 **SQL & CSV** backup formats supported
- 🐳 **Runs in a Docker container** with minimal dependencies
- 🔁 **Auto-scheduled** backups using Python's `schedule`
- 📦 Backups stored in `./backups/[container_name]/`

---

## 🚀 Project Structure

```
docker-db-backup/
├── backup-service/           # Example backup service (placeholder)
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── backups/                  # Generated backups
├── mysql-data-*/            # Docker volume mounts
├── mysql-init/              # Initialization scripts for MySQL containers
├── backup.py                # Main Python backup script
├── docker-compose.yml       # Multi-container Docker setup
└── Dockerfile               # Dockerfile for backup service
```

---

## 🛠️ Requirements

- Docker Engine
- Docker Compose

---

## 🔧 Setup

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/docker-db-backup.git
cd docker-db-backup
```

### 2. Build & start the containers

```bash
docker-compose up -d --build
```

This will:
- Start 4 MariaDB containers with individual configs
- Start the `backup-service` container
- Schedule automatic backups per container based on labels

---

## 🧠 How it Works

The `backup.py` script automatically:

- Connects to Docker Engine via socket
- Detects containers labeled for backup
- Schedules backups based on metadata

### Supported Labels

| Label                       | Description                                       |
|----------------------------|---------------------------------------------------|
| `mybackup.enable`          | Enable backup (`true` or `false`)                |
| `mybackup.host`            | Hostname or container name of the DB             |
| `mybackup.port`            | Port (default: 3306)                              |
| `mybackup.user`            | MySQL username                                    |
| `mybackup.password`        | MySQL password                                    |
| `mybackup.backup_format`   | Backup format: `sql`, `csv`, or `both`           |
| `mybackup.backup_interval_hours` | Backup interval in hours (e.g. `0.5` = 30 min) |

---

## 📤 Backup Output

Backups are stored in the following structure:

```
./backups/
├── mysql/
│   └── mysql_2025-08-01_14-00-00.sql
├── hamza/
│   └── hamza_2025-08-01_14-30-00.sql
...
```

Each subfolder represents one container and includes timestamped backup files.

---

## 🧪 Included Services (docker-compose)

- `mysql`: Main DB (1-hour interval)
- `hamza`: Secondary DB (30-min interval)
- `hamzam`: Third DB (30-min interval)
- `deneme`: Fourth DB (1-hour interval)
- `backup-service`: Python-based backup engine

---

## 🔐 Security Notes

- MySQL credentials are passed via Docker labels (visible in container metadata).
- Do not use this system in production without secrets management and secured volumes.

---

## 🧼 Recommended `.dockerignore`

```dockerignore
__pycache__/
*.pyc
backups/
mysql-data-*/
```

---

## 📄 License

This project is shared for learning, internal automation, and development use only.  
Feel free to extend and customize it to your needs.

---

## 🙌 Author

Created by **Hamza Mahlul** — inspired by automation, Docker, and clean data practices 🚀
