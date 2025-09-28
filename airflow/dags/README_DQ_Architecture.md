# Professional Data Quality Framework - Domain-Based Architecture

## 🏗️ **Architecture Overview**

This professional DQ framework uses a **domain-based DAG architecture** for optimal scalability, maintainability, and parallel execution.

### **📋 DAG Structure**

```
dq_foundation         # Infrastructure & Registry (Manual/One-time)
    ↓
dq_hr_domain         # HR Domain Tests (Daily 7 AM)
dq_finance_domain    # Finance Domain Tests (Daily 7 AM) 
dq_sales_domain      # Sales Domain Tests (Daily 7 AM) [Future]
    ↓
dq_orchestrator      # Aggregation & Alerts (Daily 9 AM)
```

## 🎯 **Why Domain-Based DAGs?**

### **✅ Advantages**
- **Parallel Execution**: All domain DAGs run simultaneously
- **Clear Ownership**: Each domain team owns their DQ tests
- **Independent Scaling**: Add new domains without affecting existing ones  
- **Isolated Failures**: One domain failure doesn't block others
- **Domain-Specific SLAs**: Different alerting and remediation rules per domain
- **Easier Debugging**: Clear separation of concerns

### **❌ Alternative Architectures Considered**

**Dimensional DAGs** (completeness, uniqueness, etc.)
- ❌ Cross-domain complexity
- ❌ Harder to assign ownership
- ❌ Mixed business contexts

**Monolithic DAG**
- ❌ Sequential execution (slow)
- ❌ Single point of failure
- ❌ Difficult to maintain and debug

**Table-Level DAGs**
- ❌ Too granular (many DAGs)
- ❌ Complex dependency management
- ❌ Resource overhead

## 📊 **Data Flow Architecture**

### **1. Foundation Layer** (`dq_foundation`)
```sql
-- Core Tables Created:
dbt.dq_test_registry      # Test catalog with dimensional classification
dbt.dq_test_results       # Execution results with scoring
dbt.dq_record_failures    # Many-to-many record-level failures  
dbt.dq_audit_log         # Comprehensive audit trail
dbt.dq_global_summary    # Daily aggregated metrics
```

### **2. Domain Layer** (HR, Finance, Sales)
```python
# Each domain DAG:
1. Generates unique run_id
2. Executes dimensional tests (completeness, uniqueness, validity, etc.)
3. Calculates DQ scores with business weighting
4. Captures detailed record failures
5. Stores results in standardized format
```

### **3. Orchestration Layer** (`dq_orchestrator`)
```python
# Aggregation & Management:
1. Waits for all domain DAGs to complete
2. Calculates global DQ metrics
3. Updates materialized views for performance
4. Checks thresholds and triggers alerts
5. Performs data retention cleanup
```

## 🔧 **Implementation Details**

### **Test ID Strategy**
```
Format: {test_type}_{table}_{column}_{timestamp_ms}
Example: completeness_not_null_hr_employees_emp_id_20250915_143022_123

Benefits:
✅ Unique across all executions
✅ Traceable to specific test runs
✅ Sortable by execution time
✅ Human-readable for debugging
```

### **Dimensional Classification**
```python
DQ_DIMENSIONS = {
    'completeness': 'Data presence and non-missing values',
    'uniqueness': 'No duplicate records where expected',
    'validity': 'Conforms to formats and business rules', 
    'consistency': 'Consistent across systems and time',
    'accuracy': 'Correctly represents real-world entities',
    'timeliness': 'Available when needed, reflects current state'
}
```

### **Scoring Algorithm**
```python
# Base Score Calculation
if status == 'pass':
    dq_score = 100.0
elif records_failed <= 1:
    dq_score = 95.0  # <1% failure
elif records_failed <= 5:
    dq_score = 85.0  # <5% failure
else:
    dq_score = max(0, 100 - (records_failed / total_records * 100))

# Business Weighting
weighted_score = dq_score * severity_multiplier
# critical: 1.5x, high: 1.2x, medium: 1.0x, low: 0.8x
```

## 🚀 **Getting Started**

### **Step 1: Setup Infrastructure**
```bash
# Run once to create all tables and populate test registry
airflow dags trigger dq_foundation
```

### **Step 2: Run Domain Tests**
```bash
# These can run in parallel
airflow dags trigger dq_hr_domain
airflow dags trigger dq_finance_domain
# airflow dags trigger dq_sales_domain  # Future
```

### **Step 3: Aggregate Results**
```bash
# Run after domain DAGs complete (or set up scheduling)
airflow dags trigger dq_orchestrator
```

### **Step 4: View Results**
- Navigate to `analytics_professional.py` in Streamlit
- View dimensional overview and domain-specific metrics
- Drill down to record-level failures
- Export remediation reports

## 📈 **Scheduling Strategy**

### **Recommended Schedule**
```python
dq_foundation:     None          # Manual trigger for infrastructure changes
dq_hr_domain:      "0 7 * * *"   # Daily at 7 AM
dq_finance_domain: "0 7 * * *"   # Daily at 7 AM (parallel)
dq_sales_domain:   "0 7 * * *"   # Daily at 7 AM (parallel) [Future]
dq_orchestrator:   "0 9 * * *"   # Daily at 9 AM (after domains)
```

### **Execution Timeline**
```
06:00 - Foundation (if needed)
07:00 - Domain DAGs start (parallel)
07:30 - Domain DAGs complete
09:00 - Orchestrator starts
09:30 - Full pipeline complete
```

## 🔍 **Monitoring & Alerting**

### **Built-in Thresholds**
```python
thresholds = {
    'min_pass_rate': 85.0,           # Minimum acceptable pass rate
    'min_overall_score': 80.0,       # Minimum acceptable overall score  
    'max_critical_failures': 5,      # Maximum critical failures
    'max_high_priority_failures': 15 # Maximum high priority failures
}
```

### **Alert Types**
- **Critical**: Immediate attention required (critical test failures)
- **High**: Action needed within 24 hours (pass rate drops)
- **Medium**: Monitor and plan remediation (score degradation)

### **Audit Trail**
All activities are logged to `dbt.dq_audit_log`:
- Test executions and results
- User actions in Streamlit
- Threshold breaches and alerts
- System events and errors

## 🛠️ **Adding New Domains**

### **1. Create Domain DAG**
```python
# Copy dq_hr_domain_dag.py
# Update domain name, tables, and tests
# Add to orchestrator dependencies
```

### **2. Update Test Registry**
```python
# Add domain tests to dq_foundation.py
# Or populate via separate script
```

### **3. Update Orchestrator**
```python
# Add ExternalTaskSensor for new domain
# Update global calculations
```

### **4. Update Analytics**
```python
# Domain will automatically appear in filters
# No code changes needed in most cases
```

## 📊 **Performance Optimization**

### **Database Indexes**
```sql
-- Automatically created by DAGs:
idx_test_results_domain          # Domain filtering
idx_test_results_dimension       # Dimensional analysis  
idx_test_results_timestamp       # Time-based queries
idx_record_failures_priority     # Remediation prioritization
```

### **Materialized Views**
```sql
-- Created by orchestrator for fast analytics:
dbt.dq_dimensional_summary_mv    # Pre-aggregated dimensional metrics
```

### **Data Retention**
```python
# Automatic cleanup by orchestrator:
test_results: 90 days
record_failures: 30 days  
audit_logs: 180 days
global_summary: 365 days
```

## 🎯 **Best Practices**

### **Domain DAG Development**
1. **Keep tests focused** on domain-specific business rules
2. **Use consistent naming** following the test ID strategy
3. **Implement proper error handling** with detailed logging
4. **Set appropriate severity levels** based on business impact
5. **Include remediation suggestions** in failure records

### **Test Design**
1. **Start with critical tests** (primary keys, required fields)
2. **Add business rule validation** specific to domain
3. **Consider data volume** when setting failure thresholds
4. **Document test business logic** in test registry
5. **Review and update tests** based on data evolution

### **Monitoring**
1. **Set domain-specific SLAs** based on business criticality
2. **Monitor execution times** and optimize slow tests
3. **Track remediation progress** using failure tables
4. **Review threshold settings** based on historical performance
5. **Analyze trends** to identify systemic issues

---

## 🤝 **Support & Maintenance**

**Platform Team**: Maintains foundation, orchestrator, and overall architecture
**Domain Teams**: Own and maintain domain-specific tests and remediation
**Analytics Team**: Uses Streamlit interface for monitoring and reporting

For questions or issues, refer to the audit logs and contact the appropriate team based on the domain or component involved.
