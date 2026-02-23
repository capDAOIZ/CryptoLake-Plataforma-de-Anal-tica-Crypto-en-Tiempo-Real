"""
DAG Master de CryptoLake - Fase 7.

Pipeline completo:
1. Init namespaces Iceberg
2. Ingesta batch (CoinGecko + Fear & Greed)
3. Bronze load (APIs -> Iceberg)
4. Silver processing (Bronze -> Silver con Spark)
5. Gold transformation (Silver -> Gold con dbt)
6. Data quality checks (validadores custom)

Schedule: Diario a las 06:00 UTC
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.task_group import TaskGroup

default_args = {
    "owner": "cryptolake",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=1),
}

# Prefijo comun para aislar dbt del entorno de Airflow.
# PYTHONNOUSERSITE=1 evita que Python cargue paquetes del usuario.
# PYTHONPATH apunta exclusivamente al virtualenv de dbt, evitando
# conflictos de protobuf entre dbt-core (>=6.0) y Airflow (<5.0).
DBT_ENV = (
    "export PYTHONNOUSERSITE=1 && export PYTHONPATH=/opt/dbt-venv/lib/python3.11/site-packages && "
)
DBT_CMD = DBT_ENV + "cd /opt/airflow/src/transformation/dbt_cryptolake && /opt/dbt-venv/bin/dbt"

# Resolver el contenedor Spark por labels de Docker Compose (sin nombres hardcodeados).
SPARK_CONTAINER_RESOLVER = """
set -euo pipefail
SPARK_SERVICE="${SPARK_SERVICE:-spark-master}"
if [ -n "${SPARK_CONTAINER:-}" ]; then
  TARGET_CONTAINER="${SPARK_CONTAINER}"
else
  SELF_CONTAINER="$(hostname)"
  PROJECT_NAME="$(docker inspect --format \
    '{{ index .Config.Labels "com.docker.compose.project" }}' \
    "$SELF_CONTAINER" 2>/dev/null || true)"

  if [ -z "$PROJECT_NAME" ]; then
    echo "ERROR: unable to resolve compose project from Airflow container labels."
    echo "Set SPARK_CONTAINER or SPARK_SERVICE env vars and retry."
    exit 1
  fi

  TARGET_CONTAINER="$(docker ps \
    --quiet \
    --filter "label=com.docker.compose.project=${PROJECT_NAME}" \
    --filter "label=com.docker.compose.service=${SPARK_SERVICE}" | head -n 1)"

  if [ -z "$TARGET_CONTAINER" ]; then
    echo "ERROR: no running container found for service '${SPARK_SERVICE}'"
    echo "in project '${PROJECT_NAME}'."
    echo "Start it with: docker compose up -d ${SPARK_SERVICE}"
    exit 1
  fi
fi
"""


def spark_submit(script_path: str, master: str | None = None) -> str:
    """Build a spark-submit command targeting the runtime-resolved Spark container."""
    master_arg = f"--master {master} " if master else ""
    return (
        SPARK_CONTAINER_RESOLVER
        + f'docker exec "$TARGET_CONTAINER" /opt/spark/bin/spark-submit {master_arg}{script_path}'
    )


with DAG(
    dag_id="cryptolake_full_pipeline",
    default_args=default_args,
    description="Pipeline: Ingesta -> Bronze -> Silver -> Gold -> Quality",
    schedule="0 6 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["cryptolake", "production"],
    doc_md=__doc__,
) as dag:
    # -- INIT ------------------------------------------------
    init_namespaces = BashOperator(
        task_id="init_namespaces",
        bash_command=spark_submit(
            "/opt/spark/work/src/processing/batch/init_namespaces.py",
            "local[1]",
        ),
    )

    # -- INGESTA ---------------------------------------------
    with TaskGroup("ingestion", tooltip="Descarga datos de APIs externas") as ingestion_group:
        extract_coingecko = BashOperator(
            task_id="extract_coingecko",
            bash_command="cd /opt/airflow && python -m src.ingestion.batch.coingecko_extractor",
        )
        extract_fear_greed = BashOperator(
            task_id="extract_fear_greed",
            bash_command="cd /opt/airflow && python -m src.ingestion.batch.fear_greed_extractor",
        )

    # -- BRONZE ----------------------------------------------
    with TaskGroup("bronze_load", tooltip="Cargar datos en Iceberg Bronze") as bronze_group:
        api_to_bronze = BashOperator(
            task_id="api_to_bronze",
            bash_command=spark_submit("/opt/spark/work/src/processing/batch/api_to_bronze.py"),
        )

    # -- SILVER ----------------------------------------------
    with TaskGroup("silver_processing", tooltip="Limpiar y deduplicar en Silver") as silver_group:
        bronze_to_silver = BashOperator(
            task_id="bronze_to_silver",
            bash_command=spark_submit("/opt/spark/work/src/processing/batch/bronze_to_silver.py"),
        )

    # -- GOLD (dbt) ------------------------------------------
    with TaskGroup("gold_transformation", tooltip="Modelado dimensional con dbt") as gold_group:
        dbt_run = BashOperator(
            task_id="dbt_run",
            bash_command=f"{DBT_CMD} run --profiles-dir . --target prod",
        )
        dbt_test = BashOperator(
            task_id="dbt_test",
            bash_command=f"{DBT_CMD} test --profiles-dir . --target prod",
        )
        dbt_run >> dbt_test

    # -- DATA QUALITY (Fase 7) -------------------------------
    with TaskGroup("data_quality", tooltip="Validacion de calidad de datos") as quality_group:
        quality_checks = BashOperator(
            task_id="quality_checks",
            bash_command=spark_submit("/opt/spark/work/src/quality/run_quality_checks.py"),
        )

    # -- DEPENDENCIAS ----------------------------------------
    (
        init_namespaces
        >> ingestion_group
        >> bronze_group
        >> silver_group
        >> gold_group
        >> quality_group
    )
