FROM apache/airflow:2.9.0

# Switch to root for system installations
USER root

# Update package lists and install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    unixodbc \
    unixodbc-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create directories and set permissions
RUN mkdir -p /opt/airflow/.dbt \
    && mkdir -p /opt/dbt \
    && mkdir -p /opt/sql \
    && mkdir -p /opt/data \
    && chown -R airflow:root /opt/

# Switch back to airflow user
USER airflow

# Install Python packages
RUN pip install --no-cache-dir \
    dbt-postgres==1.8.2 \
    dbt-core==1.8.2 \
    dbt-trino \
    markupsafe==2.0.1 \
    apache-airflow-providers-postgres \
    apache-airflow-providers-odbc \
    apache-airflow-providers-trino \
    apache-airflow-providers-http \
    psycopg2-binary \
    gitpython \
    plyvel \
    pyarrow==14.0.0 \
    pandas \
    sqlalchemy \
    requests \
    boto3 \
    minio \
    great-expectations \
    && pip install --upgrade cmake

# Set environment variables
ENV DBT_PROFILES_DIR=/opt/airflow/.dbt
ENV DBT_PROJECT_DIR=/opt/dbt
ENV PYTHONPATH="${PYTHONPATH}:/opt/airflow/dags"