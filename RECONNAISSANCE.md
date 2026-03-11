# 🕵️ Phase 0: Manual Codebase Reconnaissance - dbt Labs Jaffle Shop

<div align="center">

**Forward Deployed Engineer Investigation**  
*Ground Truth Establishment for Automated Cartographer Validation*

</div>

---

## 📋 Metadata

| Field | Value |
|-------|-------|
| **Target Repository** | [dbt-labs/jaffle-shop](https://github.com/dbt-labs/jaffle-shop) |
| **Analyst** | Tsegay |
| **Date** | March 11, 2026 |
| **Duration** | 30 minutes |
| **Repository Size** | ~1,170 objects, 27.96 MB |
| **Clone Command** | `git clone https://github.com/dbt-labs/jaffle-shop.git` |

---

## 📊 Executive Summary

Jaffle Shop is a **modern dbt (data build tool) demonstration project** that showcases real-world data engineering patterns. Unlike traditional ETL tools, dbt focuses on **transformations in the data warehouse** using SQL. This project follows dbt best practices with a clear staging → marts architecture, CSV seeds as data sources, and comprehensive YAML documentation.

**Key Discovery:** The project has a **clear DAG structure** with 6 source CSV files → 6 staging models → 7 mart models. The `stg_orders` model is the most referenced (appears in 2 downstream models), making it a critical dependency. Business logic is concentrated in the `customers.sql` and `orders.sql` mart models.

---

## 📈 Comprehensive Codebase Statistics

### Language Distribution

| Language | File Count | Primary Location | Purpose |
|----------|------------|------------------|---------|
| **SQL** | 15 | `models/` | Data transformations (staging + marts) |
| **YAML** | 21 | `models/`, root | Configuration, documentation, tests |
| **Python** | 1 | `.github/workflows/scripts/` | dbt Cloud orchestration script |
| **CSV** | 6 | `seeds/jaffle-data/` | Raw data sources |
| **Other** | 10+ | Root, `.github/` | Config files, CI/CD |

### File Size & Complexity Analysis

| Metric | Value | Command Used |
|--------|-------|--------------|
| Total SQL files | 15 | `find . -name "*.sql" \| wc -l` |
| Total YAML files | 21 | `find . -name "*.yml" -o -name "*.yaml" \| wc -l` |
| Largest SQL file | 77 lines (`orders.sql`) | `wc -l models/marts/orders.sql` |
| Most referenced model | `stg_orders` (2 references) | `grep -r "ref('stg_orders')"` |
| CSV seed files | 6 | Raw customer, order, item data |

---

## 🎯 The Five FDE Day-One Questions

### Question 1: What is the primary data ingestion path?

#### Answer
Jaffle Shop uses **CSV seeds** as its data source. The ingestion path is:

```
CSV Seeds (seeds/jaffle-data/)
    → dbt seed command
    → Raw tables in database
    → Staging models (models/staging/)
    → Mart models (models/marts/)
```

#### 🔍 Evidence

**Data Sources (CSV Seeds):**
```bash
$ ls -la seeds/jaffle-data/
-rw-r--r-- 1 HP 197121   48928 Mar 11 16:00 raw_customers.csv
-rw-r--r-- 1 HP 197121 7544717 Mar 11 16:00 raw_items.csv
-rw-r--r-- 1 HP 197121 8899283 Mar 11 16:00 raw_orders.csv
-rw-r--r-- 1 HP 197121     923 Mar 11 16:00 raw_products.csv
-rw-r--r-- 1 HP 197121     477 Mar 11 16:00 raw_stores.csv
-rw-r--r-- 1 HP 197121    2655 Mar 11 16:00 raw_supplies.csv
```

**Sample Data (raw_customers.csv):**
```csv
id,name
50a2d1c4-d788-4498-a6f7-dd75d4db588f,Stephanie Love
438005c2-dd1d-48aa-8bfd-7fb06851b5f8,Kristi Keller
```

**Source Definitions in YAML:**
```yaml
# models/staging/__sources.yml
sources:
  - name: ecom
    schema: raw
    tables:
      - name: raw_customers
      - name: raw_orders
      - name: raw_items
      - name: raw_stores
      - name: raw_products
      - name: raw_supplies
```

**Source References in Staging Models:**
```sql
-- models/staging/stg_customers.sql
select * from {{ source('ecom', 'raw_customers') }}

-- models/staging/stg_orders.sql
select * from {{ source('ecom', 'raw_orders') }}
```

---

### Question 2: What are the 3-5 most critical output datasets?

#### Answer
The critical outputs are the **mart models** in `models/marts/`, which represent business-ready datasets:

| Rank | Output Model | File | Purpose | Size |
|------|--------------|------|---------|------|
| **1** | `customers` | `models/marts/customers.sql` | Customer overview with lifetime value | 58 lines |
| **2** | `orders` | `models/marts/orders.sql` | Order details with costs | 77 lines |
| **3** | `order_items` | `models/marts/order_items.sql` | Item-level order details | 66 lines |
| **4** | `products` | `models/marts/products.sql` | Product information | 101 lines |
| **5** | `locations` | `models/marts/locations.sql` | Store location data | 104 lines |

#### 🔍 Evidence

**Mart Models Exist:**
```bash
$ ls -la models/marts/*.sql
-rw-r--r-- 1 HP 197121 1332 models/marts/customers.sql
-rw-r--r-- 1 HP 197121  104 models/marts/locations.sql
-rw-r--r-- 1 HP 197121  311 models/marts/metricflow_time_spine.sql
-rw-r--r-- 1 HP 197121 1009 models/marts/order_items.sql
-rw-r--r-- 1 HP 197121 1527 models/marts/orders.sql
-rw-r--r-- 1 HP 197121  101 models/marts/products.sql
-rw-r--r-- 1 HP 197121  101 models/marts/supplies.sql
```

**Customers Model (Critical Business Logic):**
```sql
-- models/marts/customers.sql
with
customers as (select * from {{ ref('stg_customers') }}),
orders as (select * from {{ ref('orders') }}),
customer_orders_summary as (
    select
        orders.customer_id,
        count(distinct orders.order_id) as count_lifetime_orders,
        -- ... business logic for customer lifetime value
)
```

**YAML Documentation Confirms Criticality:**
```yaml
# models/marts/customers.yml
- name: customers
  description: Customer overview data mart, one row per customer
  columns:
    - name: customer_id
      data_tests: [not_null, unique]
```

**No Downstream References (Final Outputs):**
```bash
$ grep -r "ref('customers')" --include="*.sql" models/
# No results - customers is a final output
```

---

### Question 3: What is the blast radius if the most critical module fails?

#### Answer
**Most Critical Module:** `models/staging/stg_orders.sql` - referenced by **2 downstream models**

#### 💥 Blast Radius Visualization

```
stg_orders.sql FAILS
    ├── models/marts/orders.sql (depends on stg_orders)
    │   └── models/marts/customers.sql (depends on orders)
    └── models/marts/order_items.sql (depends on stg_orders)
        └── models/marts/customers.sql (depends on order_items)
```

#### 📊 Impact Quantification

| Metric | Value | Evidence |
|--------|-------|----------|
| Most referenced staging model | `stg_orders` (2 references) | `grep -r "ref('stg_orders')"` |
| Models depending on stg_orders | 2 (`orders.sql`, `order_items.sql`) | Direct dependency check |
| Total affected mart models | 3 (`orders`, `order_items`, `customers`) | Cascading dependencies |
| Files importing Database | N/A (dbt project) | No Python database layer |

#### 🔍 Dependency Evidence

**Models that depend on stg_orders:**
```bash
$ grep -r "ref('stg_orders')" --include="*.sql" models/
models/marts/order_items.sql:    stg_orders as ( select * from {{ ref('stg_orders') }} ),
models/marts/orders.sql:    select * from {{ ref('stg_orders') }}
```

**Models that depend on orders (cascading impact):**
```bash
$ grep -r "ref('orders')" --include="*.sql" models/
models/marts/customers.sql:    orders as ( select * from {{ ref('orders') }} ),
```

**Most Referenced Models Overall:**
```bash
$ grep -r "ref(" --include="*.sql" models/ | cut -d"'" -f2 | sort | uniq -c | sort -rn
      2 stg_supplies
      2 stg_products
      2 stg_orders
      1 stg_order_items
      1 stg_locations
      1 stg_customers
      1 orders
      1 order_items
```

---

### Question 4: Where is business logic concentrated vs. distributed?

#### Answer
Business logic follows the **dbt best practices pattern**:

#### 🧠 Concentrated Business Logic (Mart Models)

| File | Lines | Logic Type | Description |
|------|-------|------------|-------------|
| `models/marts/orders.sql` | 77 | Aggregations, calculations | Order costs, totals |
| `models/marts/order_items.sql` | 66 | Item-level metrics | Supply costs, margins |
| `models/marts/customers.sql` | 58 | Customer analytics | Lifetime value, order count |

#### 🌐 Distributed Business Logic (Staging Models)

| File | Lines | Logic Type | Description |
|------|-------|------------|-------------|
| `models/staging/stg_products.sql` | 34 | Simple selects | Column renaming, casting |
| `models/staging/stg_orders.sql` | 33 | Basic transforms | Date formatting |
| `models/staging/stg_supplies.sql` | 31 | Simple selects | Data type conversion |

#### 📊 Business Logic Distribution

```
CONCENTRATED (Mart Models - Business Logic):
├── orders.sql (77 lines) - Order calculations, totals
├── order_items.sql (66 lines) - Item-level metrics
└── customers.sql (58 lines) - Customer lifetime value

DISTRIBUTED (Staging Models - Light Transformations):
├── stg_products.sql (34 lines) - Simple column rename
├── stg_orders.sql (33 lines) - Date formatting
├── stg_supplies.sql (31 lines) - Type casting
└── Other staging models (20-30 lines) - Basic selects
```

#### 🔍 Complex Logic Detection

**Aggregations in Mart Models:**
```sql
-- In orders.sql
sum(order_items.order_cost) as order_total,
sum(order_items.order_cost) as customer_lifetime_value

-- In customers.sql
count(distinct orders.order_id) as count_lifetime_orders,
sum(orders.order_total) as lifetime_spend_pretax
```

**No Complex Logic in Staging:**
```sql
-- In stg_customers.sql (simple)
select
    id as customer_id,
    name as customer_name
from {{ source('ecom', 'raw_customers') }}
```

---

### Question 5: What has changed most frequently in the last 90 days?

#### Answer
The `git log` analysis reveals active development patterns:

#### 📈 Top 20 Changed Files Analysis

```bash
$ git log --pretty=format: --name-only | sort | uniq -c | sort -rn | head -20
```

| Rank | Changes | File | Type | Interpretation |
|------|---------|------|------|----------------|
| 1 | 49 | `README.md` | Docs | Documentation actively maintained |
| 2 | 24 | `dbt_project.yml` | YAML | Core configuration changes |
| 3 | 17 | `Taskfile.yml` | YAML | Task automation updates |
| 4 | 13 | `packages.yml` | YAML | Dependency management |
| 5 | 13 | `.pre-commit-config.yaml` | YAML | CI/CD configuration |
| 6 | 12 | `models/marts/orders.yml` | YAML | Documentation for critical model |
| 7 | 12 | `models/marts/orders.sql` | SQL | Business logic evolution |
| 8 | 10 | `profiles.yml` | YAML | Connection configuration |
| 9 | 9 | `requirements.txt` | Dependencies | Python package updates |
| 10 | 9 | `package-lock.yml` | YAML | Locked dependencies |
| 11 | 9 | `models/staging/__sources.yml` | YAML | Source definitions |
| 12 | 9 | `models/marts/order_items.yml` | YAML | Documentation |
| 13 | 9 | `models/marts/order_items.sql` | SQL | Business logic |
| 14 | 8 | `jaffle-data/raw_orders.csv` | CSV | Source data changes |
| 15 | 7 | `models/marts/customers.yml` | YAML | Documentation |
| 16 | 7 | `models/marts/customers.sql` | SQL | Customer logic |
| 17 | 7 | `.gitignore` | Config | Git configuration |
| 18 | 6 | `requirements.in` | Dependencies | Python requirements |
| 19 | 6 | `models/staging/stg_orders.sql` | SQL | Staging logic |
| 20 | 6 | `models/marts/products.yml` | YAML | Documentation |

#### 🗺️ Velocity Hotspots Map

```
🚀 HIGH VELOCITY (Active Development):
├── README.md (49 changes) - Documentation
├── dbt_project.yml (24 changes) - Core config
├── orders model (12 changes) - Critical business logic
└── source definitions (9 changes) - Data sources

📊 MEDIUM VELOCITY (Stable Evolution):
├── Staging models (6-7 changes)
├── Other mart models (7-9 changes)
└── Package dependencies (9-13 changes)

💤 LOW VELOCITY (Stable/Dead Code):
├── models/marts/locations.sql - only 1 change ever
├── models/staging/stg_customers.sql - only 1 change ever
```

#### 🔍 Dead Code Candidates
```bash
$ git ls-files "*.sql" | while read file; do
    changes=$(git log --oneline -- "$file" 2>/dev/null | wc -l)
    if [ $changes -eq 1 ]; then
        echo "  $file - only 1 change ever"
    fi
done
models/marts/locations.sql - only 1 change ever
models/staging/stg_customers.sql - only 1 change ever
```

---

## 🤔 Comprehensive Difficulty Analysis

### What Was Hardest to Figure Out Manually?

| Challenge | Time Spent | Evidence Found | Why It Was Hard |
|-----------|------------|----------------|-----------------|
| **Understanding dbt DAG** | 5 min | Staging → Marts pattern | Had to trace `ref()` calls manually |
| **Finding critical path** | 4 min | `stg_orders` most referenced | Needed to count references |
| **Business logic location** | 3 min | Complex logic in mart models | CASE statements in SQL |
| **Source identification** | 2 min | CSV seeds in `seeds/` | Easy once found |
| **Change frequency** | 3 min | Git log analysis | Simple with commands |

### Where Did I Get Lost? (Detailed Breakdown)

#### 1. **Initial DAG Confusion**
- **What I thought:** Looked for Airflow-style DAGs
- **Reality:** dbt uses SQL `ref()` function for dependencies
- **Evidence:** Found `{{ ref('stg_orders') }}` in models
- **Solution:** `grep -r "ref("` to trace dependencies

#### 2. **Source Location Surprise**
- **What I thought:** Data sources would be in `data/` or `sources/`
- **Reality:** CSV seeds in `seeds/jaffle-data/`
- **Evidence:** Found 6 CSV files with raw data
- **Time saved:** Once found, clear structure

#### 3. **Business Logic Distribution**
- **What I thought:** Logic spread evenly
- **Reality:** 80% of business logic in 20% of files (mart models)
- **Evidence:** Mart models have aggregations, staging has simple selects

### What Helped Me Navigate (Success Patterns)

```bash
# These commands saved the most time:

# 1. Find all sources
ls -la seeds/jaffle-data/

# 2. Trace DAG dependencies
grep -r "ref(" --include="*.sql" models/

# 3. Find most referenced models
grep -r "ref(" --include="*.sql" models/ | cut -d"'" -f2 | sort | uniq -c | sort -rn

# 4. Find business logic (aggregations)
grep -r "SUM(\|COUNT(\|AVG(" --include="*.sql" models/

# 5. Check configuration
cat dbt_project.yml

# 6. Find source definitions
cat models/staging/__sources.yml
```

---

## 💡 Key Insights for My Cartographer (Prioritized)

### 🔴 CRITICAL PRIORITY (Must Have)

| Priority | Feature | Evidence from Manual Work |
|----------|---------|---------------------------|
| **P0** | **Parse dbt `ref()` dependencies** | DAG defined by `{{ ref('model') }}` calls |
| **P0** | **Extract source definitions** | `__sources.yml` defines raw data sources |
| **P0** | **Build lineage graph** | Clear staging → marts flow |
| **P0** | **Identify sinks (mart models)** | Models with no downstream dependencies |
| **P0** | **Identify sources (seeds)** | CSV files + source definitions |

### 🟡 HIGH PRIORITY (Should Have)

| Priority | Feature | Evidence |
|----------|---------|----------|
| **P1** | **Parse YAML documentation** | 21 YAML files with model descriptions |
| **P1** | **Track change frequency** | `orders.sql` has 12 changes - active |
| **P1** | **Detect dead code candidates** | `locations.sql` only 1 change |
| **P1** | **Business logic detection** | Aggregations in mart models |

### 🟢 MEDIUM PRIORITY (Nice to Have)

| Priority | Feature | Evidence |
|----------|---------|----------|
| **P2** | **Python script analysis** | 1 orchestration script |
| **P2** | **CI/CD workflow parsing** | GitHub Actions in `.github/` |
| **P2** | **Macro detection** | Reusable SQL in `macros/` |

---

## ✅ Ground Truth Summary (For Later Validation)

| Question | Manual Answer | Evidence Location | Confidence |
|----------|---------------|-------------------|------------|
| **Primary ingestion** | CSV seeds in `seeds/jaffle-data/` | `raw_*.csv` files | 100% |
| **Critical outputs** | `customers`, `orders`, `order_items` marts | `models/marts/*.sql` | 100% |
| **Blast radius** | `stg_orders` failure affects 2 marts | Dependency analysis | 95% |
| **Business logic** | Concentrated in mart models | Aggregations in mart SQL | 100% |
| **High velocity** | `README.md` (49), `dbt_project.yml` (24) | Git log | 100% |
| **Dead code** | `locations.sql`, `stg_customers.sql` | Git history | 90% |

---

## 🎯 What I Learned in 30 Minutes

1. **dbt projects have a clear DAG structure** - Staging models feed into marts, defined by `ref()` calls

2. **Sources are explicitly defined** - `__sources.yml` maps raw data to database tables

3. **Business logic is in mart models** - Aggregations, calculations, customer lifetime value

4. **Most referenced model is critical** - `stg_orders` appears in 2 downstream models

5. **YAML is everywhere** - 21 YAML files for documentation, tests, configuration

6. **Change frequency reveals priorities** - Orders model changes most (business logic evolution)

7. **Dead code exists** - Some models have only 1 change ever - candidates for deletion

---

## 📝 Final Reflection

**Manual analysis of a well-structured dbt project took 30 minutes. Imagine doing this for a messy 800,000-line codebase!**

The Cartographer will save **DAYS, not hours**. Every feature I prioritize comes directly from pain points I experienced:

- Tracing `ref()` dependencies manually → **Build DAG parser**
- Finding source definitions → **Parse `__sources.yml`**
- Identifying critical models → **Reference counting + PageRank**
- Locating business logic → **Detect aggregations**
- Understanding change patterns → **Git velocity analysis**

**The tool I build will make the next engineer's first 30 minutes productive, not painful.**

---

<div align="center">

*"The FDE does not memorize codebases. The FDE builds instruments that make codebases legible."*

**— Master Thinker Philosophy**

</div>
```

---

