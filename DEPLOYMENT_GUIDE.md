# 🚀 **Professional DQ Framework Deployment Guide**

## 📋 **Complete Steps to Deploy and Test**

### **Phase 1: Infrastructure Setup**

#### **Step 1: Run Foundation DAG (One-time)**
```bash
# In Airflow UI or CLI
airflow dags trigger dq_foundation

# What it does:
✅ Creates all infrastructure tables (dq_test_registry, dq_test_results, etc.)
✅ Populates test registry with predefined tests
✅ Creates summary views and indexes
✅ Sets up audit logging tables

# Expected duration: 2-3 minutes
# Status: Check in Airflow UI - should show "success"
```

#### **Step 2: Verify Infrastructure**
```bash
# Connect to your PostgreSQL database and verify:
SELECT COUNT(*) FROM dbt.dq_test_registry;        # Should show ~12 tests
SELECT COUNT(*) FROM dbt.dq_test_results;         # Should be 0 (no tests run yet)
SELECT COUNT(*) FROM dbt.dq_record_failures;      # Should be 0 (no failures yet)
SELECT COUNT(*) FROM dbt.dq_audit_log;           # Should be 0 (no events yet)
```

### **Phase 2: Domain Testing**

#### **Step 3: Run Domain DAGs (Parallel)**
```bash
# Run these simultaneously for best performance
airflow dags trigger dq_hr_domain
airflow dags trigger dq_finance_domain

# What each does:
🏢 dq_hr_domain:
  - Tests hr.employees table
  - Completeness (emp_id, name, email)
  - Uniqueness (emp_id, email)
  - Validity (email format)
  - Stores results in dq_test_results

💰 dq_finance_domain:
  - Tests finance.transactions table
  - Uniqueness (txn_id)
  - Validity (amount range)
  - Consistency (emp_id references hr.employees)
  - Stores results in dq_test_results

# Expected duration: 3-5 minutes each
# Status: Both should show "success" in Airflow UI
```

#### **Step 4: Verify Domain Results**
```bash
# Check that domain tests ran successfully
SELECT domain, COUNT(*) as test_count, 
       COUNT(CASE WHEN status = 'pass' THEN 1 END) as passed,
       COUNT(CASE WHEN status = 'fail' THEN 1 END) as failed
FROM dbt.dq_test_results 
WHERE DATE(execution_timestamp) = CURRENT_DATE
GROUP BY domain;

# Expected output:
# domain  | test_count | passed | failed
# hr      | 5          | 3-5    | 0-2
# finance | 3          | 2-3    | 0-1
```

### **Phase 3: Global Aggregation**

#### **Step 5: Run Orchestrator DAG**
```bash
# Wait for domain DAGs to complete, then run:
airflow dags trigger dq_orchestrator

# What it does:
🌍 Global Aggregation:
  - Calculates overall DQ scores
  - Creates domain summaries
  - Updates materialized views
  - Checks thresholds and creates alerts
  - Performs data cleanup

# Expected duration: 2-3 minutes
# Status: Should show "success" in Airflow UI
```

#### **Step 6: Verify Global Results**
```bash
# Check global summary was created
SELECT * FROM dbt.dq_global_summary 
WHERE calculation_date = CURRENT_DATE;

# Check materialized view
SELECT * FROM dbt.dq_dimensional_summary_mv;

# Check for any alerts
SELECT event_type, event_subtype, status 
FROM dbt.dq_audit_log 
WHERE event_type = 'threshold_alert' 
AND DATE(event_timestamp) = CURRENT_DATE;
```

### **Phase 4: UI Testing**

#### **Step 7: Restart Streamlit Service**
```bash
# If running locally:
cd C:/Users/sbessat/DXC/dq_streamlit_app
streamlit run app.py

# If running as service:
# Stop and restart your Streamlit service
# The exact command depends on your setup
```

#### **Step 8: Test Home Page (Professional)**
```
🌐 Navigate to: http://localhost:8501
📊 Use: pages/home_professional.py

✅ Expected Results:
- Global DQ metrics displayed (overall score, pass rate, total tests)
- Domain-level cards showing HR and Finance scores
- Date range selector working (Last 7 days, Last 30 days, etc.)
- No demo data - only real test results
- Quick action buttons working

🔍 Test Scenarios:
1. Change date range → metrics should update
2. Check domain cards → should show real HR/Finance data
3. Click "View Detailed Analytics" → should navigate to analytics page
```

#### **Step 9: Test Analytics Page (Professional)**
```
🌐 Navigate to: pages/analytics_professional.py

✅ Expected Results:
- Dimensional overview with real test results
- Enhanced filters: Date Range, DQ Dimension, Domain, Test Status
- Interactive test results table with real data
- Select failed tests → detailed analysis available
- Record-level failure analysis working

🔍 Test Scenarios:
1. Filter by dimension (completeness, uniqueness, etc.) → results update
2. Filter by domain (HR, Finance) → results update
3. Select failed tests → "Analyze Record Failures" button enabled
4. Click analyze → detailed record failures displayed
5. Export functionality working
```

### **Phase 5: Advanced Testing**

#### **Step 10: Test Date Range Functionality**
```
🗓️ Home Page Date Range Testing:
1. Select "Last 7 days" → should show recent results
2. Select "Last 30 days" → should show more historical data
3. Select "Custom Range" → pick specific dates
4. Verify metrics change based on date selection

📊 Analytics Page Date Range Testing:
1. Change date range → test results table updates
2. Dimensional overview reflects selected period
3. Record failures match selected date range
```

#### **Step 11: Test Multi-Domain Scenarios**
```
👥 User Access Testing:
1. Admin user → sees all domains (HR, Finance)
2. HR user → sees only HR domain data
3. Finance user → sees only Finance domain data
4. Domain filtering works correctly in both pages
```

#### **Step 12: Test Drill-Down Functionality**
```
🔍 Analytics Drill-Down Testing:
1. Select multiple failed tests in table
2. Click "Analyze Record Failures"
3. Verify detailed failure analysis appears
4. Check record-level data is displayed correctly
5. Test remediation priority sorting
6. Export failure report → CSV download works
```

### **Phase 6: Validation & Monitoring**

#### **Step 13: Validate Data Integrity**
```bash
# Check data consistency
SELECT 
    tr.domain,
    COUNT(DISTINCT tr.test_id) as unique_tests,
    COUNT(*) as total_results,
    COUNT(DISTINCT rf.failure_id) as unique_failures
FROM dbt.dq_test_results tr
LEFT JOIN dbt.dq_record_failures rf ON tr.result_id = rf.result_id
WHERE DATE(tr.execution_timestamp) = CURRENT_DATE
GROUP BY tr.domain;

# Verify test registry matches results
SELECT 
    reg.domain,
    COUNT(reg.test_id) as registered_tests,
    COUNT(res.result_id) as executed_tests
FROM dbt.dq_test_registry reg
LEFT JOIN dbt.dq_test_results res ON reg.test_id = res.test_id 
    AND DATE(res.execution_timestamp) = CURRENT_DATE
GROUP BY reg.domain;
```

#### **Step 14: Performance Validation**
```bash
# Check query performance on key views
EXPLAIN ANALYZE SELECT * FROM dbt.dq_dimensional_summary_mv;
EXPLAIN ANALYZE SELECT * FROM dbt.dq_test_results WHERE DATE(execution_timestamp) = CURRENT_DATE;

# Verify indexes are being used
SELECT schemaname, tablename, indexname, idx_tup_read, idx_tup_fetch 
FROM pg_stat_user_indexes 
WHERE schemaname = 'dbt';
```

### **Phase 7: Ongoing Operations**

#### **Step 15: Set Up Smart Daily Scheduling**
```bash
# Recommended schedule in Airflow (ALL DAGs can run daily - they're smart!):
dq_foundation:     "0 5 * * *"  # Daily at 5 AM (checks if infrastructure needed)
dq_hr_domain:      "0 7 * * *"  # Daily at 7 AM (checks if HR tests needed)
dq_finance_domain: "0 7 * * *"  # Daily at 7 AM (checks if Finance tests needed)
dq_orchestrator:   "0 9 * * *"  # Daily at 9 AM (always runs aggregation)

# Enable ALL DAGs in Airflow UI:
# 1. Go to Airflow web interface
# 2. Toggle ON for: dq_foundation, dq_hr_domain, dq_finance_domain, dq_orchestrator
# 3. All DAGs are now smart and will skip unnecessary work!

# Smart Features:
# ✅ dq_foundation: Only creates tables if missing, skips if already exists
# ✅ dq_hr_domain: Always runs if HR table exists and has data (multiple runs per day OK)
# ✅ dq_finance_domain: Always runs if Finance table exists and has data (multiple runs per day OK)
# ✅ dq_orchestrator: Always runs (aggregation and cleanup, uses latest results)
```

#### **Step 16: Monitor and Maintain**
```bash
# Daily monitoring queries:
-- Check today's test execution
SELECT domain, COUNT(*) as tests_run, 
       AVG(dq_score) as avg_score,
       COUNT(CASE WHEN status = 'fail' THEN 1 END) as failures
FROM dbt.dq_test_results 
WHERE DATE(execution_timestamp) = CURRENT_DATE
GROUP BY domain;

-- Check for alerts
SELECT event_subtype, COUNT(*) as alert_count
FROM dbt.dq_audit_log 
WHERE event_type = 'threshold_alert' 
AND DATE(event_timestamp) = CURRENT_DATE
GROUP BY event_subtype;

-- Monitor data growth
SELECT 
    'test_results' as table_name, COUNT(*) as row_count
FROM dbt.dq_test_results
UNION ALL
SELECT 
    'record_failures' as table_name, COUNT(*) as row_count  
FROM dbt.dq_record_failures
UNION ALL
SELECT 
    'audit_log' as table_name, COUNT(*) as row_count
FROM dbt.dq_audit_log;
```

## 🧠 **Smart DAG Features**

### **✅ Intelligent Infrastructure Management**
```python
# dq_foundation DAG now includes:
✅ Table existence checks before creation
✅ Registry population only if empty
✅ View creation only if missing
✅ Detailed logging of what was skipped vs created
✅ XCom communication between tasks
```

### **✅ Smart Domain Testing**
```python
# Domain DAGs now include:
✅ Verify source tables exist and have data
✅ Skip execution only if tables missing/no data
✅ Allow multiple runs per day (always use latest results)
✅ Detailed status logging
✅ Graceful handling of missing dependencies
```

### **✅ Resource Optimization**
```bash
# Benefits of smart scheduling:
🚀 Faster execution (skip unnecessary work)
💾 Reduced database load (no redundant operations)
📊 Better logging (clear skip reasons)
🔧 Easier maintenance (self-healing infrastructure)
⚡ Improved reliability (graceful degradation)
```

### **✅ Multiple Runs Per Day Behavior**
```bash
# What happens when DAGs run multiple times per day:

First Run (Any Day):
- dq_foundation: Creates all tables, populates registry ✅
- dq_hr_domain: Runs all HR tests ✅
- dq_finance_domain: Runs all Finance tests ✅
- dq_orchestrator: Aggregates results ✅

Subsequent Runs (Same Day):
- dq_foundation: Checks tables exist, skips creation ✅
- dq_hr_domain: Runs HR tests again (uses latest results) ✅
- dq_finance_domain: Runs Finance tests again (uses latest results) ✅
- dq_orchestrator: Always runs aggregation (uses latest results) ✅

Smart Skipping:
- dq_hr_domain: Only skips if HR table missing/no data ⚠️
- dq_finance_domain: Only skips if Finance table missing/no data ⚠️
- Multiple runs per day = Always get latest data quality status

Manual Infrastructure Changes:
- dq_foundation: Can be triggered manually for schema updates
- Will detect missing tables and create them
- Will repopulate registry if needed
```

## 🎯 **Success Criteria Checklist**

### **✅ Infrastructure**
- [ ] All tables created successfully
- [ ] Test registry populated with 12+ tests
- [ ] Indexes created and functioning
- [ ] Audit logging operational

### **✅ Data Pipeline**
- [ ] Domain DAGs run successfully
- [ ] Test results stored correctly
- [ ] Record failures captured
- [ ] Global aggregation working

### **✅ User Interface**
- [ ] Home page shows real data (no demo data)
- [ ] Date range filtering functional
- [ ] Domain-level metrics accurate
- [ ] Analytics page drill-down working

### **✅ Data Quality**
- [ ] Dimensional classification working
- [ ] Test ID system functioning
- [ ] Many-to-many relationships correct
- [ ] Audit trail complete

### **✅ Performance**
- [ ] Queries execute in <5 seconds
- [ ] Parallel DAG execution working
- [ ] Materialized views updating
- [ ] Data retention policies active

## 🆘 **Troubleshooting Guide**

### **Common Issues & Solutions**

#### **Issue: DAG fails with "table does not exist"**
```bash
# Solution: Run foundation DAG first
airflow dags trigger dq_foundation
# Wait for completion, then retry domain DAGs
```

#### **Issue: No data in UI despite successful DAGs**
```bash
# Check data actually exists:
SELECT COUNT(*) FROM dbt.dq_test_results;
SELECT COUNT(*) FROM dbt.dq_global_summary;

# If empty, check DAG logs for errors
# Verify database connection in Streamlit
```

#### **Issue: Analytics page shows "No results"**
```bash
# Check date range - might be too narrow
# Verify domain access permissions
# Check if tests actually failed (no failures = no drill-down data)
```

#### **Issue: Performance problems**
```bash
# Check if indexes exist:
SELECT * FROM pg_indexes WHERE schemaname = 'dbt';

# Rebuild materialized views:
REFRESH MATERIALIZED VIEW dbt.dq_dimensional_summary_mv;
```

---

## 🎉 **You're Ready!**

After completing all steps, you'll have a **production-ready, professional data quality framework** with:

- ✅ **Domain-based DAG architecture** for scalable execution
- ✅ **Real-time dimensional analysis** across completeness, uniqueness, validity, etc.
- ✅ **Global and domain-specific scoring** with date range support
- ✅ **Record-level failure analysis** with remediation planning
- ✅ **Comprehensive audit logging** for compliance
- ✅ **Professional UI** with no demo data

**Next Steps:**
1. Add more domains (Sales, Marketing) following the same pattern
2. Customize thresholds and alerting rules
3. Integrate with your monitoring systems
4. Train users on the new interface
5. Set up automated reporting

**Support:** Refer to `airflow/dags/README_DQ_Architecture.md` for detailed technical documentation.
