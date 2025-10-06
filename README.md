# ETL Pipeline with Airflow, dbt, and Trino

This project provides a complete ETL (Extract, Transform, Load) pipeline that extracts data from CRM and ERP systems, transforms it using dbt (data build tool), and orchestrates everything with Apache Airflow.

## Architecture

- **Apache Airflow**: Workflow orchestration and scheduling
- **dbt**: Data transformation and modeling
- **Trino**: Distributed SQL query engine
- **PostgreSQL**: Data storage for source systems and data warehouse
- **MinIO**: Object storage (S3-compatible)
- **Redis**: Message broker for Celery executor

## Features

- Automated data extraction from CRM and ERP systems
- Data quality validation and testing
- Incremental data transformations with dbt
- Comprehensive logging and monitoring
- Scalable architecture with Docker Compose
- Data lineage and documentation

## Quick Start

1. **Prerequisites**
   ```bash
   # Install Docker and Docker Compose
   # Ensure you have at least 4GB RAM and 2 CPU cores available
   ```

2. **Setup and Start**
   ```bash
   # Clone or create the project directory
   chmod +x setup.sh
   ./setup.sh
   ```

3. **Access the Services**
   - **Airflow Web UI**: http://localhost:8081 (admin/admin123)
   - **Trino UI**: http://localhost:8080
   - **MinIO Console**: http://localhost:9001 (admin/password)

## Project Structure

```
├── docker-compose.yml          # Service orchestration
├── Dockerfile                  # Custom Airflow image
├── dags/                       # Airflow DAGs
│   └── crm_erp_etl_dag.py     # Main ETL pipeline
├── datalake/                   # dbt project
│   ├── dbt_project.yml        # dbt configuration
│   └── models/                # Data models
│       ├── staging/           # Raw data staging
│       ├── intermediate/      # Business logic
│       └── marts/            # Final analytics tables
├── profile/                    # dbt profiles
│   └── profiles.yml           # Database connections
├── config/                     # Configuration files
│   └── airflow.cfg            # Airflow configuration
├── etc/                        # Trino configuration
│   ├── config.properties     # Trino settings
│   └── catalog/              # Data source catalogs
├── init-scripts/              # Database initialization
├── sql/                       # SQL scripts and queries
└── logs/                      # Application logs
```

## ETL Pipeline Flow

1. **Health Checks**: Verify Trino and PostgreSQL connectivity
2. **Data Extraction**: Extract data from CRM and ERP systems
3. **Data Validation**: Run quality checks on extracted data
4. **dbt Transformation**: Transform and model data using dbt
5. **Report Generation**: Generate pipeline summary

## Data Models

### Staging Layer
- `stg_crm_customers`: Cleaned customer data
- `stg_crm_sales`: Normalized sales transactions
- `stg_erp_products`: Product master data
- `stg_erp_inventory`: Current inventory levels

### Intermediate Layer
- `int_sales_with_customers`: Sales data enriched with customer information
- `int_sales_enriched`: Complete sales data with product details

### Marts Layer
- `customer_summary`: Customer performance metrics
- `product_performance`: Product sales and inventory analytics
- `monthly_sales_summary`: Time-series sales analytics

## Configuration

### Database Connections
The pipeline connects to multiple databases:
- **CRM Database**: Customer and sales data
- **ERP Database**: Product and inventory data
- **Warehouse Database**: Transformed analytics data

### dbt Profiles
Configure target databases in `profile/profiles.yml`:
- **dev**: PostgreSQL for development
- **prod**: Trino for production queries

## Monitoring and Maintenance

### Airflow UI
- Monitor DAG runs and task status
- View logs and error messages
- Trigger manual runs and backfills

### Data Quality
- Automated data validation in dbt models
- Custom data quality checks in SQL scripts
- Comprehensive testing suite

### Logging
All services log to the `logs/` directory with structured logging format.

## Customization

### Adding New Data Sources
1. Add source configuration in `datalake/models/schema.yml`
2. Create staging models in `datalake/models/staging/`
3. Update the DAG to include new extraction logic

### Modifying Transformations
1. Edit existing models or create new ones in `datalake/models/`
2. Add tests in the schema.yml files
3. Run `dbt run` and `dbt test` to validate changes

### Scaling
- Increase Celery worker count in docker-compose.yml
- Add more Trino worker nodes for larger datasets
- Configure external object storage (S3, GCS) for production

## Troubleshooting

### Common Issues
1. **Out of Memory**: Increase Docker memory allocation to 4GB+
2. **Port Conflicts**: Modify port mappings in docker-compose.yml
3. **Permission Errors**: Ensure proper file permissions with `chmod +x`

### Useful Commands
```bash
# View service status
docker-compose ps

# View service logs
docker-compose logs -f airflow-webserver

# Restart specific service
docker-compose restart airflow-scheduler

# Access Airflow CLI
docker-compose exec airflow-webserver airflow --help

# Run dbt commands manually
docker-compose exec airflow-webserver dbt run --project-dir /opt/dbt

# Access PostgreSQL
docker-compose exec postgres psql -U airflow -d warehouse
```

## Security Considerations

- Change default passwords in production
- Use proper authentication backends
- Encrypt sensitive connections
- Implement proper access controls
- Use secrets management for production deployments

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.