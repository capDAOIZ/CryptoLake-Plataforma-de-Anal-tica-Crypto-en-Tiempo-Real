#!/usr/bin/env python3
"""
Health check: verifica que todos los servicios de CryptoLake estan running.

Uso:
    python scripts/health_check.py
"""

import subprocess
import sys


SERVICES = {
    "minio": "MinIO (Storage)",
    "kafka": "Kafka (Streaming)",
    "spark-master": "Spark Master",
    "spark-worker": "Spark Worker",
    "spark-thrift": "Spark Thrift Server",
    "airflow-webserver": "Airflow Webserver",
    "airflow-scheduler": "Airflow Scheduler",
    "iceberg-rest": "Iceberg REST Catalog",
    "api": "FastAPI",
    "dashboard": "Streamlit Dashboard",
}


def check_services():
    print("CryptoLake Health Check")
    print("=" * 50)

    result = subprocess.run(
        ["docker", "compose", "ps", "--services", "--status", "running"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print("ERROR: cannot query docker compose status")
        print(result.stderr.strip())
        sys.exit(1)

    running = set(line.strip() for line in result.stdout.splitlines() if line.strip())
    healthy = 0
    total = len(SERVICES)

    for service, label in SERVICES.items():
        if service in running:
            print(f"  OK   {label:<30} running")
            healthy += 1
        else:
            print(f"  FAIL {label:<30} NOT RUNNING")

    print("=" * 50)
    print(f"  {healthy}/{total} services running")

    if healthy < total:
        print("\nTip: run 'make up' to start all services")
        sys.exit(1)


if __name__ == "__main__":
    check_services()
