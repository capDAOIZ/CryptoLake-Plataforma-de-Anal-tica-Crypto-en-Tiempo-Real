# ============================================================
# Spark 3.5 + Apache Iceberg + S3 (MinIO)
# ============================================================
# Imagen oficial del proyecto Apache Spark con PySpark incluido.
# "py" significa que viene con Python y PySpark preinstalados.
#
# Documentación: https://hub.docker.com/r/apache/spark-py
# ============================================================
FROM apache/spark:3.5.3-python3

# Cambiar a root para instalar dependencias
USER root

# ── Instalar librerías Python ──────────────────────────────
# Estas son las librerías que usarán nuestros jobs de Spark.
# --break-system-packages es necesario en imágenes basadas en
# Debian 12+ que protegen el Python del sistema.
RUN pip install --no-cache-dir \
    pyiceberg[s3fs]==0.7.1 \
    pyarrow==15.0.1 \
    kafka-python==2.0.2 \
    requests==2.31.0 \
    pydantic==2.5.0 \
    pydantic-settings==2.1.0 \
    structlog==24.1.0

# ── Descargar JARs de Iceberg ─────────────────────────────
# Spark es Java por dentro. Para que "entienda" Iceberg y S3,
# necesita librerías .jar (el equivalente Java de los .whl de Python).
# Los descargamos de Maven Central (el PyPI de Java).
#
# iceberg-spark-runtime: permite a Spark leer/escribir tablas Iceberg
# iceberg-aws-bundle: permite a Iceberg conectar con S3/MinIO
ENV ICEBERG_VERSION=1.5.2

RUN curl -L -o /opt/spark/jars/iceberg-spark-runtime-3.5_2.12-${ICEBERG_VERSION}.jar \
    "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/${ICEBERG_VERSION}/iceberg-spark-runtime-3.5_2.12-${ICEBERG_VERSION}.jar" \
 && curl -L -o /opt/spark/jars/iceberg-aws-bundle-${ICEBERG_VERSION}.jar \
    "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-aws-bundle/${ICEBERG_VERSION}/iceberg-aws-bundle-${ICEBERG_VERSION}.jar"

# ── Descargar JARs de Kafka ───────────────────────────────
# JARs de Kafka para Spark Structured Streaming
# Estos permiten que Spark lea/escriba de Kafka directamente.
ENV SPARK_VERSION=3.5.3
ENV SCALA_VERSION=2.12
RUN curl -L -o /opt/spark/jars/spark-sql-kafka-0-10_${SCALA_VERSION}-${SPARK_VERSION}.jar \
    "https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_${SCALA_VERSION}/${SPARK_VERSION}/spark-sql-kafka-0-10_${SCALA_VERSION}-${SPARK_VERSION}.jar" \
 && curl -L -o /opt/spark/jars/kafka-clients-3.6.1.jar \
    "https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.6.1/kafka-clients-3.6.1.jar" \
 && curl -L -o /opt/spark/jars/spark-token-provider-kafka-0-10_${SCALA_VERSION}-${SPARK_VERSION}.jar \
    "https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_${SCALA_VERSION}/${SPARK_VERSION}/spark-token-provider-kafka-0-10_${SCALA_VERSION}-${SPARK_VERSION}.jar" \
 && curl -L -o /opt/spark/jars/commons-pool2-2.12.0.jar \
    "https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.12.0/commons-pool2-2.12.0.jar"

# ── Copiar configuración de Spark ──────────────────────────
COPY spark-defaults.conf /opt/spark/conf/spark-defaults.conf

# PYTHONPATH: permite que los scripts hagan "from src.config import settings"
# /opt/spark/work es donde montamos el código del proyecto
ENV PYTHONPATH="/opt/spark/work:${PYTHONPATH}"

# Volver al usuario spark (UID 185) por seguridad.
# Nunca ejecutes servicios como root en producción.
USER spark
