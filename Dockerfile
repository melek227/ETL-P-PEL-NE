FROM apache/airflow:2.9.0

USER root

RUN apt-get update && apt-get install -y \
    git \
    curl \
    unixodbc \
    unixodbc-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/airflow/.dbt \
    && mkdir -p /opt/dbt \
    && mkdir -p /opt/sql \
    && mkdir -p /opt/data \
    && chown -R airflow:root /opt/

USER airflow

# requirements.txt dosyasını kopyala ve minio dahil paketleri yükle
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

RUN pip install --no-cache-dir \
    dbt-postgres==1.8.2 \
    dbt-core==1.8.2 \
    dbt-trino \
    markupsafe==2.0.1 \
    minio \
    pyarrow==14.0.0 \
    pandas \
    sqlalchemy \
    requests \
    boto3 \
    great-expectations \
    gitpython \
    plyvel \
    && pip install --upgrade cmake

ENV DBT_PROFILES_DIR=/opt/airflow/.dbt
ENV DBT_PROJECT_DIR=/opt/dbt
ENV PYTHONPATH="${PYTHONPATH}:/opt/airflow/dags"