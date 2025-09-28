# 🔬 Enterprise Data Quality Monitoring Platform

A comprehensive data quality monitoring and analytics platform built with **Streamlit**, **dbt**, **Airflow**, and **PostgreSQL**.

## 🏗️ **Architecture Overview**

```
📊 Streamlit Dashboard (Frontend)
    ↓
🔬 Data Quality Engine (dbt + Airflow)
    ↓
🗄️ PostgreSQL Database (Storage)
    ↓
📈 Monitoring Stack (Prometheus + Grafana)
```

## ✨ **Key Features**

### 📋 **Data Quality Framework**
- **6 DQ Dimensions**: Completeness, Uniqueness, Validity, Consistency, Accuracy, Timeliness
- **Domain-Based Testing**: HR, Finance, Sales domains with specific rules
- **Automated Test Execution**: Airflow-orchestrated dbt tests
- **Failed Record Tracking**: Primary key-based failed record investigation

### 🎯 **Interactive Dashboard**
- **Real-time Analytics**: Live data quality metrics and trends
- **Interactive Charts**: WebGL-powered visualizations with zoom/pan
- **Deep Dive Investigation**: Select failed tests → see actual failing records
- **Column Highlighting**: Visual identification of failing data columns
- **Export Capabilities**: CSV, JSON, and comprehensive reports

### ⚙️ **Automation & Orchestration**
- **Airflow DAGs**: Automated test execution and result processing
- **dbt Models**: Reusable data quality macros and models
- **Docker Deployment**: Complete containerized stack
- **Monitoring**: Prometheus metrics and Grafana dashboards

## 🚀 **Quick Start**

### Prerequisites
- Docker & Docker Compose
- Python 3.9+
- Git

### 1. Clone Repository
```bash
git clone <your-repo-url>
cd dq_streamlit_app
```

### 2. Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

### 3. Deploy Stack
```bash
# Start all services
docker-compose up -d

# Verify services
docker-compose ps
```

### 4. Access Applications
- **Streamlit Dashboard**: http://localhost:8501
- **Airflow Web UI**: http://localhost:8080
- **Grafana Monitoring**: http://localhost:3000

## 📊 **Data Quality Dimensions**

| Dimension | Description | Example Tests |
|-----------|-------------|---------------|
| **Completeness** | Data presence and non-missing values | `not_null`, `required_fields` |
| **Uniqueness** | No duplicate records where expected | `unique`, `primary_key` |
| **Validity** | Conformance to formats and ranges | `email_format`, `date_range` |
| **Consistency** | Data consistency across systems | `referential_integrity` |
| **Accuracy** | Correct representation of entities | `business_rule_validation` |
| **Timeliness** | Data availability when needed | `future_dates`, `data_freshness` |

## 🗄️ **Database Schema**

### Core Tables
```sql
-- Test Registry
dbt.dq_test_registry          -- Catalog of all DQ tests

-- Execution Results  
dbt.dq_test_results          -- Test execution status and scores

-- Failed Records
dbt.dq_record_failures       -- Actual failed records with primary keys

-- Domain Data
hr.employees                 -- HR domain data
finance.transactions         -- Finance domain data  
sales.orders                -- Sales domain data
```

## 🔧 **Development**

### Project Structure
```
dq_streamlit_app/
├── streamlit_app/           # Frontend dashboard
│   ├── pages/              # Streamlit pages
│   ├── components/         # Reusable UI components
│   ├── services/           # Database connections
│   └── utils/              # Helper functions
├── dbt/                    # Data transformation
│   └── dq_dbt_project/     # dbt models and macros
│       ├── macros/         # DQ test macros
│       └── models/         # Data models
├── airflow/                # Orchestration
│   └── dags/               # Airflow DAGs
├── postgres/               # Database setup
├── monitoring/             # Prometheus + Grafana
└── docker-compose.yml      # Service orchestration
```

### Adding New Data Quality Tests

1. **Create dbt Macro**:
```sql
-- macros/my_custom_test.sql
{% macro my_custom_test(table_name, column_name) %}
    select count(*) as failures
    from {{ table_name }}
    where {{ column_name }} fails_my_condition
{% endmacro %}
```

2. **Register in Test Registry**:
```sql
INSERT INTO dbt.dq_test_registry (test_name, test_type, dq_dimension, domain, table_name, column_name)
VALUES ('my_custom_test', 'validity', 'validity', 'hr', 'hr.employees', 'my_column');
```

3. **Add to Airflow DAG**:
```python
def run_my_custom_test(**context):
    # Execute test and capture results
    pass
```

## 🎯 **Usage Examples**

### Deep Dive Investigation
1. Navigate to **Analytics** page
2. Select failed tests from the table
3. Click **"🔍 Investigate Selected Tests"**
4. View actual failing records with highlighted columns
5. Download detailed analysis reports

### Monitoring & Alerting
- Set up Grafana alerts for DQ score thresholds
- Monitor test execution trends
- Track remediation progress

## 📈 **Monitoring & Observability**

### Metrics Tracked
- **Test Execution Rates**: Success/failure rates by domain
- **Data Quality Scores**: Dimensional and overall scores
- **Performance Metrics**: Test execution times
- **Business Impact**: Failed record counts and remediation status

### Grafana Dashboards
- **Executive Overview**: High-level DQ metrics
- **Operational Dashboard**: Test execution monitoring
- **Domain Deep Dives**: Domain-specific analytics

## 🔐 **Security & Configuration**

### Environment Variables
```bash
# Database
POSTGRES_USER=dq_user
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=dq_db

# Airflow
AIRFLOW_USER=admin
AIRFLOW_PASSWORD=admin_password

# Streamlit
STREAMLIT_SECRET_KEY=your_secret_key
```

### Credential Management
- Credentials externalized to `config/credentials.yml`
- Environment-specific configurations
- Secure secret management

## 📚 **Documentation**

- [Architecture Guide](ARCHITECTURE_IMPROVEMENTS.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)
- [Complete Redesign Notes](README_COMPLETE_REDESIGN.md)

## 🤝 **Contributing**

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 **Support**

For questions and support:
- Create an issue in this repository
- Check existing documentation
- Review troubleshooting guides

---

## 🏷️ **Tech Stack**

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Frontend** | Streamlit | Interactive dashboard |
| **Backend** | Python, FastAPI | API services |
| **Database** | PostgreSQL | Data storage |
| **ETL** | dbt | Data transformation |
| **Orchestration** | Apache Airflow | Workflow automation |
| **Monitoring** | Prometheus + Grafana | Metrics and alerting |
| **Deployment** | Docker Compose | Container orchestration |
| **Charts** | Plotly.js | Interactive visualizations |

---

**Built with ❤️ for enterprise data quality monitoring**
