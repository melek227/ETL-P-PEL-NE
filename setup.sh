#!/bin/bash

# ETL Pipeline Deployment and Setup Script

echo "=== ETL Pipeline Setup ==="
echo "Building and starting the ETL pipeline..."

# Check if Docker and Docker Compose are installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Set proper permissions for initialization scripts
chmod +x init-scripts/init-databases.sh

# Create necessary directories
mkdir -p logs
mkdir -p plugins
mkdir -p data

# Build the custom Airflow image
echo "Building custom Airflow image with dbt and Trino support..."
docker-compose build

# Start the services
echo "Starting services..."
docker-compose up -d postgres redis object-store

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
sleep 30

# Initialize databases
echo "Initializing databases..."
docker-compose exec postgres bash -c "cd /docker-entrypoint-initdb.d && ./init-databases.sh"

# Start Trino
echo "Starting Trino..."
docker-compose up -d trino

# Wait for Trino to be ready
echo "Waiting for Trino to be ready..."
sleep 30

# Initialize Airflow
echo "Initializing Airflow..."
docker-compose up airflow-init

# Start Airflow services
echo "Starting Airflow services..."
docker-compose up -d airflow-webserver airflow-scheduler airflow-worker airflow-triggerer

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Services are starting up. Please wait a few minutes for all services to be ready."
echo ""
echo "Access URLs:"
echo "- Airflow Web UI: http://localhost:8081"
echo "  Username: admin"
echo "  Password: admin123"
echo ""
echo "- Trino UI: http://localhost:8080"
echo "- MinIO Console: http://localhost:9001"
echo "  Username: admin"
echo "  Password: password"
echo ""
echo "- PostgreSQL: localhost:5432"
echo "  Username: airflow"
echo "  Password: airflow"
echo "  Databases: airflow, crm, erp, warehouse"
echo ""
echo "To check service status:"
echo "docker-compose ps"
echo ""
echo "To view logs:"
echo "docker-compose logs -f [service_name]"
echo ""
echo "To stop all services:"
echo "docker-compose down"
echo ""
echo "The ETL DAG 'crm_erp_etl_pipeline' will be available in Airflow once services are fully started."
echo "You can trigger it manually or it will run daily according to the schedule."