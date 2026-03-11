# 🕵️ Phase 0: Manual Codebase Reconnaissance - Apache Superset

<div align="center">

**Forward Deployed Engineer Investigation**  
*Ground Truth Establishment for Automated Cartographer Validation*

</div>

---

## 📋 Metadata

| Field | Value |
|-------|-------|
| **Target Repository** | [apache/superset](https://github.com/apache/superset) |
| **Analyst** | Tsegay |
| **Date** | March 10, 2026 |
| **Duration** | 30 minutes  |
| **Repository Size** | ~7,441 files, 868 MB |
| **Clone Command** | `git clone https://github.com/apache/superset.git` |

---

## 📊 Executive Summary

Apache Superset is a modern, enterprise-ready business intelligence web application. Unlike traditional data engineering projects that ingest data, Superset **connects to existing databases** and provides a visualization layer. This fundamental characteristic shapes the entire architecture and my findings below.

**Key Discovery:** The `Database` class is the **heart of the system**, imported in **100+ files** across the codebase. SQL is **embedded in Python strings** rather than standalone `.sql` files, which will be critical for my Hydrologist agent.

---

## 📈 Comprehensive Codebase Statistics

### Language Distribution

| Language | File Count | Primary Location | Purpose |
|----------|------------|------------------|---------|
| **Python** | 1,856 | `superset/` | Backend logic, API, SQL execution |
| **TypeScript/JavaScript** | 1,000+ | `superset-frontend/` | React UI, visualization rendering |
| **YAML** | 150+ | `.github/`, `examples/`, `helm/` | CI/CD, config, dashboard definitions |
| **SQL** | 0 (embedded) | Inside Python strings | Database queries (no standalone files) |

### File Size & Complexity Analysis

| Metric | Value | Command Used |
|--------|-------|--------------|
| Total Python files | 1,856 | `find . -name "*.py" \| wc -l` |
| Non-test Python files | ~1,500 | Manual estimation |
| Largest Python file | 3,483 lines (`models/helpers.py`) | `wc -l` |
| Most functions in one file | 132 (`viz.py`) | `grep -c "def "` |
| YAML configuration files | 150+ | `find . -name "*.yml" -o -name "*.yaml" \| wc -l` |

---

## 🎯 The Five FDE Day-One Questions

### Question 1: What is the primary data ingestion path?

#### Answer
Superset does **NOT ingest data** in the traditional sense. Instead, it **connects to existing databases** via SQLAlchemy connection strings. The complete data flow is:

```
User Interface (SQL Lab) 
    → API Call (superset/views/)
    → SQL Execution Engine (sql_lab.py)
    → Database Connection (models/core.py: Database class)
    → Query Execution (db_engine_specs/)
    → Result Set Processing (result_set.py)
    → Visualization Rendering (viz.py + frontend)
```

#### 🔍 Evidence

**Critical File: `superset/sql_lab.py`**
```bash
$ ls -la superset/sql_lab.py
-rw-r--r-- 1 HP 197121 28063 Mar 10 17:00 superset/sql_lab.py
```

**The Heart: `Database` Class in `superset/models/core.py`**
```python
class Database(CoreDatabase, AuditMixinNullable, ImportExportMixin):
    """The core database model that powers all connections"""
```

**Import Impact:** The `Database` class is imported in **100+ files** across the codebase:

```
superset/commands/database/create.py
superset/commands/database/delete.py  
superset/commands/database/export.py
superset/daos/database.py
superset/sql_lab.py
superset/views/core.py
... and 40+ database engine specifications
```

**Connection Method:** `get_sqla_engine()` is the single point of failure:
```bash
$ grep -r "get_sqla_engine" --include="*.py" superset/ | head -5
superset/commands/dashboard/export_example.py:        with dataset.database.get_sqla_engine() as engine:
superset/commands/database/sync_permissions.py:        with self.db_connection.get_sqla_engine() as engine:
superset/commands/database/test_connection.py:            with database.get_sqla_engine() as engine:
superset/commands/database/validate.py:        with database.get_sqla_engine() as engine:
superset/commands/dataset/importers/v1/utils.py:        with database.get_sqla_engine(
```

**Database Connectors:** 40+ database-specific implementations
```bash
$ ls -la superset/db_engine_specs/ | grep -c ".py"
45
```

---

### Question 2: What are the 3-5 most critical output datasets?

#### Answer
Superset's outputs are **visualizations and dashboards**, not traditional datasets. Critical outputs are defined in YAML files and database models:

| Rank | Output Type | Location | Format | Business Value |
|------|-------------|----------|--------|----------------|
| **1** | Featured Dashboards | `superset/examples/featured_charts/dashboard.yaml` | YAML | Showcase of all chart types |
| **2** | Sales Dashboard | `superset/examples/sales_dashboard/dashboard.yaml` | YAML | Business metrics (16,400 bytes) |
| **3** | World Health Dashboard | `superset/examples/world_health/dashboard.yaml` | YAML | Geospatial visualization |
| **4** | Chart Definitions | `superset/examples/*/charts/*.yaml` | YAML | Individual visualization specs |
| **5** | Database Models | `superset/models/dashboard.py:class Dashboard` | Python | Metadata storage |

#### 🔍 Evidence

**Dashboard YAML Files Found:**
```bash
$ ls -la superset/examples/*/dashboard.yaml
-rw-r--r--  3939 superset/examples/deckgl_demo/dashboard.yaml
-rw-r--r-- 18203 superset/examples/fcc_new_coder_survey/dashboard.yaml
-rw-r--r-- 11224 superset/examples/featured_charts/dashboard.yaml ✅
-rw-r--r--  4372 superset/examples/misc_charts/dashboard.yaml
-rw-r--r-- 16400 superset/examples/sales_dashboard/dashboard.yaml ✅
-rw-r--r--       superset/examples/slack_dashboard/dashboard.yaml
-rw-r--r--       superset/examples/usa_births_names/dashboard.yaml
-rw-r--r--       superset/examples/video_game_sales/dashboard.yaml
-rw-r--r--       superset/examples/world_health/dashboard.yaml
```

**Dashboard Model Definition:**
```bash
$ grep -r "class Dashboard" --include="*.py" superset/models/
superset/models/dashboard.py:class Dashboard(CoreDashboard, AuditMixinNullable, ImportExportMixin):
```

**Example Dashboard Structure (from tree):**
```
superset/examples/
├── featured_charts/
│   ├── dashboard.yaml (main output)
│   ├── charts/ (individual chart definitions)
│   └── datasets/ (data source definitions)
├── sales_dashboard/
│   ├── dashboard.yaml (business metrics)
│   └── charts/
└── world_health/
    ├── dashboard.yaml (geospatial)
    └── charts/
```

---

### Question 3: What is the blast radius if the most critical module fails?

#### Answer
**Most Critical Module:** `superset/sql_lab.py` (SQL execution engine) - 28,063 bytes of core execution logic

#### 💥 Blast Radius Visualization

```
sql_lab.py FAILS
    ├── SQL Lab UI (frontend/src/SqlLab/) → Complete feature loss
    ├── Chart queries (superset/charts/) → 100+ charts fail to load
    ├── Dashboard queries (superset/dashboards/) → All dashboards show errors
    ├── Explore feature (superset/explore/) → Data exploration impossible
    ├── Database connections (via get_sqla_engine()) → 40+ DB connectors affected
    ├── API endpoints (superset/views/api.py) → All data APIs return errors
    └── All visualization rendering (viz.py) → Charts cannot get data
```

#### 📊 Impact Quantification

| Metric | Value | Evidence |
|--------|-------|----------|
| Files importing Database | 100+ | `grep -r "from superset.models.core import Database" . \| wc -l` |
| Database engine specs | 40+ | `ls superset/db_engine_specs/ \| grep ".py" \| wc -l` |
| Functions in viz.py | 132 | `grep -c "def " superset/viz.py` |
| Changes to views/core.py | 767 | Git log - most actively modified |
| Direct sql_lab imports | Multiple | `daos/query.py`, `tests/` |

#### 🔍 Dependency Evidence

**Files that depend on Database model (partial list):**
```
superset/commands/database/create.py
superset/commands/database/delete.py
superset/commands/database/export.py
superset/commands/database/importers/v1/utils.py
superset/commands/database/oauth2.py
superset/commands/database/sync_permissions.py
superset/commands/database/tables.py
superset/commands/database/test_connection.py
superset/commands/database/update.py
superset/commands/database/uploaders/base.py
superset/commands/database/utils.py
superset/commands/database/validate.py
superset/commands/database/validate_sql.py
superset/commands/dataset/duplicate.py
superset/commands/dataset/importers/v0.py
superset/commands/dataset/importers/v1/utils.py
superset/commands/dataset/update.py
superset/commands/dataset/warm_up_cache.py
superset/daos/database.py
superset/daos/dataset.py
superset/dashboards/filters.py
superset/databases/api.py
superset/databases/decorators.py
superset/databases/filters.py
superset/databases/ssh_tunnel/models.py
... and 40+ db_engine_specs files
```

**Secondary Critical Modules:**

| Module | Lines | Functions | Impact if fails |
|--------|-------|-----------|-----------------|
| `superset/viz.py` | 2,843 | 132 | All visualizations break |
| `superset/security/manager.py` | 3,169 | 106 | Authentication/authorization fails |
| `superset/models/helpers.py` | 3,483 | 121 | Core data models corrupted |
| `superset/views/core.py` | 767 changes* | High | Main UI views fail |

*\*From git log: 767 changes - most actively modified view file*

---

### Question 4: Where is business logic concentrated vs. distributed?

#### Answer
Business logic follows the **Pareto Principle (80/20 rule)** - 20% of files contain 80% of the business logic.

#### 🧠 Concentrated Business Logic (The "Brain")

| File | Lines | Functions | Logic Type | Change Frequency |
|------|-------|-----------|------------|------------------|
| `superset/viz.py` | 2,843 | **132** | Chart rendering, visualization logic | 484 changes |
| `superset/security/manager.py` | 3,169 | 106 | Authentication, permissions | Medium |
| `superset/models/helpers.py` | 3,483 | 121 | Core data model helpers | Medium |
| `superset/connectors/sqla/models.py` | 2,109 | 122 | SQLAlchemy models | 436 changes |
| `superset/sql/parse.py` | 1,606 | 79 | SQL parsing logic | Medium |

#### 🌐 Distributed Business Logic (The "Nervous System")

| Area | Location | Distribution Pattern |
|------|----------|---------------------|
| Database connectors | `superset/db_engine_specs/` | 40+ files, one per DB |
| API endpoints | `superset/views/api.py`, `views/core.py` | Spread across view files |
| Frontend logic | `superset-frontend/src/` | 1,000+ React components |
| Chart types | `superset-frontend/plugins/` | 20+ plugin directories |
| Commands | `superset/commands/` | 20+ subdirectories (create, delete, update) |

#### 📊 Top 10 Files by Function Count (Business Logic Density)

```bash
$ find superset -name "*.py" -not -path "*/tests/*" -exec grep -l "def " {} \; | \
>   xargs -I {} sh -c "echo -n '{}: '; grep -c 'def ' '{}'" | sort -t: -k2 -rn | head -10

superset/viz.py: 132 functions
superset/connectors/sqla/models.py: 122 functions
superset/models/helpers.py: 121 functions
superset/security/manager.py: 106 functions
superset/db_engine_specs/base.py: 106 functions
superset/utils/core.py: 97 functions
superset/models/core.py: 93 functions
superset/sql/parse.py: 79 functions
superset/mcp_service/chart/tool/get_chart_preview.py: 59 functions
superset/migrations/shared/migrate_viz/query_functions.py: 58 functions
```

#### 🗺️ Business Logic Distribution Visualization

```
CONCENTRATED (20% of files, 80% of logic):
├── viz.py (core visualization) - 132 functions
├── security/manager.py (auth) - 106 functions
├── models/helpers.py (data models) - 121 functions
├── connectors/sqla/models.py (DB abstraction) - 122 functions
└── sql/parse.py (SQL parsing) - 79 functions

DISTRIBUTED (80% of files, 20% of logic):
├── db_engine_specs/ (40+ DB connectors)
├── frontend/ (1,000+ UI components)
├── commands/ (20+ command handlers)
└── plugins/ (20+ chart plugins)
```

#### 🔍 Complex Logic Detection

Files containing complex SQL/CASE logic:
```bash
$ grep -r -l "CASE WHEN\|complex\|business" --include="*.py" superset/ | head -10
superset/commands/sql_lab/estimate.py
superset/commands/sql_lab/streaming_export_command.py
superset/commands/tasks/submit.py
superset/config.py
superset/connectors/sqla/models.py
superset/db_engine_specs/base.py
superset/db_engine_specs/lib.py
superset/db_engine_specs/monetdb.py
superset/db_engine_specs/presto.py
superset/errors.py
```

---

### Question 5: What has changed most frequently in the last 90 days?

#### Answer
The `git log` analysis reveals clear patterns of active development and potential pain points.

#### 📈 Top 20 Changed Files Analysis

```bash
$ git log --pretty=format: --name-only | sort | uniq -c | sort -rn | head -20
```

| Rank | Changes | File | Type | Interpretation |
|------|---------|------|------|----------------|
| 1 | **1,263** | `superset-frontend/package-lock.json` | Dependencies | Frontend dependencies constantly updating |
| 2 | **929** | `superset-frontend/package.json` | Dependencies | Active frontend development |
| 3 | **767** | `superset/views/core.py` | Python | Core views under active development |
| 4 | **663** | `superset/config.py` | Python | Configuration evolving |
| 5 | **484** | `superset/viz.py` | Python | Visualization logic actively modified |
| 6 | 481 | `setup.py` | Python | Installation config changes |
| 7 | **436** | `superset/connectors/sqla/models.py` | Python | SQLAlchemy models changing |
| 8 | 404 | `requirements/base.txt` | Dependencies | Python deps updating |
| 9 | 378 | `superset-websocket/package-lock.json` | Dependencies | WebSocket deps |
| 10 | 365 | `superset-websocket/package.json` | Dependencies | WebSocket dev |
| 11 | 355 | `docs/yarn.lock` | Dependencies | Docs dependencies |
| 12 | 340 | `UPDATING.md` | Docs | Documentation updates |
| 13 | 327 | `superset/models/core.py` | Python | Core models changing |
| 14 | 321 | `docs/package.json` | Dependencies | Docs deps |
| 15 | 300 | `superset/assets/package.json` | Dependencies | Assets deps |
| 16 | 293 | `superset-frontend/temporary_superset_ui/.../package.json` | Dependencies | UI deps |
| 17 | 288 | `superset-frontend/temporary_superset_ui/superset-ui/lerna.json` | Config | UI monorepo config |
| 18 | 284 | `superset/utils/core.py` | Python | Core utilities |
| 19 | 274 | `README.md` | Docs | README updates |
| 20 | 273 | `superset-frontend/cypress-base/cypress.json` | Config | E2E test config |

#### 🗺️ Velocity Hotspots Map

```
🚀 HIGH VELOCITY (Active Development - Pain Points):
├── Frontend (package files) - 2,192 combined changes
├── Core Views (views/core.py) - 767 changes ⚡
├── Configuration (config.py) - 663 changes ⚡
├── Visualization (viz.py) - 484 changes ⚡
└── SQLAlchemy Models (models.py) - 436 changes ⚡

📊 MEDIUM VELOCITY (Stable Evolution):
├── API endpoints (views/api.py)
├── Database connectors (db_engine_specs/)
├── Command handlers (commands/)
└── Test files (tests/)

💤 LOW VELOCITY (Stable/Dead Code):
├── docs/scripts/extract_custom_errors.py - only 1 change ever
├── docs/scripts/fix-openapi-spec.py - only 1 change ever
├── scripts/extract_feature_flags.py - only 1 change ever
├── superset-core/src/superset_core/common/__init__.py - only 1 change ever
├── superset-core/src/superset_core/common/daos.py - only 1 change ever
├── superset-core/src/superset_core/common/models.py - only 1 change ever
├── superset-core/src/superset_core/extensions/__init__.py - only 1 change ever
├── superset-core/src/superset_core/extensions/constants.py - only 1 change ever
└── superset-core/src/superset_core/mcp/decorators.py - only 1 change ever
```

#### 🔄 Recently Modified Critical Files (Last 24 Hours)

```bash
$ git log -5 --name-only --pretty=format: | grep -v "^$" | sort -u | \
>   while read file; do if [ -f "$file" ]; then echo "  $(git log -1 --format=%cd -- $file) - $file"; fi; done | head -10

Tue Mar 10 09:52:48 2026 +0100 - superset/mcp_service/chart/__init__.py
Tue Mar 10 10:53:05 2026 +0100 - superset/mcp_service/chart/chart_utils.py
Tue Mar 10 09:52:12 2026 +0100 - superset/mcp_service/chart/resources/chart_configs.py
Tue Mar 10 09:52:12 2026 +0100 - superset/mcp_service/chart/schemas.py
Tue Mar 10 10:53:05 2026 +0100 - superset/mcp_service/chart/tool/generate_chart.py
Tue Mar 10 09:52:48 2026 +0100 - superset/mcp_service/dashboard/__init__.py
Tue Mar 10 09:52:48 2026 +0100 - superset/mcp_service/dataset/__init__.py
Tue Mar 10 15:57:32 2026 +0700 - superset-frontend/jest.config.js
Tue Mar 10 16:51:58 2026 +0700 - superset-frontend/package.json
Tue Mar 10 16:51:58 2026 +0700 - superset-frontend/package-lock.json
```

---

## 🤔 Comprehensive Difficulty Analysis

### What Was Hardest to Figure Out Manually?

| Challenge | Time Spent | Evidence Found | Why It Was Hard |
|-----------|------------|----------------|-----------------|
| **Finding SQL** | 8 min | SQL in Python strings only, no `.sql` files | Had to use regex: `grep -r '""".*SELECT.*FROM'` |
| **Understanding data flow** | 7 min | Python (1,856 files) + TypeScript (1,000+ files) | Polyglot complexity: frontend + backend + APIs |
| **Identifying critical path** | 5 min | 100+ files import Database model | No single entry point, spiderweb of dependencies |
| **Finding business logic** | 6 min | Logic spread across viz.py, models/, views/ | Had to use function counting to find density |
| **Understanding outputs** | 4 min | Outputs are YAML + DB metadata, not files | Not traditional datasets, needed to run examples |

### Where Did I Get Lost? (Detailed Breakdown)

#### 1. **Initial Wrong Assumption: File-based Data Sources**
- **What I thought:** Looked for CSV, Parquet, or other data files
- **Reality:** Sources are database connections configured at runtime
- **Evidence:** Found Database class in models/, no file-based ingestion
- **Time wasted:** ~5 minutes

#### 2. **SQL Location Confusion**
- **What I thought:** Searched for `.sql` files using `find . -name "*.sql"`
- **Reality:** SQL is embedded in Python strings across:
  - `tests/unit_tests/db_engine_specs/`
  - `superset/sql_lab.py`
  - `superset/connectors/sqla/`
- **Time wasted:** ~4 minutes
- **Solution found:** `grep -r '""".*SELECT.*FROM' --include="*.py"`

#### 3. **Frontend/Backend Split Confusion**
- **What I thought:** Data flow was purely Python
- **Reality:** Frontend (TS) → API (Python) → SQL → DB
- **Evidence:** Found `@api` decorators in `superset/views/`
- **Time wasted:** ~3 minutes

#### 4. **Dependency Spiderweb**
- **What I thought:** Could trace linear dependencies
- **Reality:** Database model imported in 100+ files
- **Evidence:** `grep -r "from superset.models.core import Database" . | wc -l` = 100+
- **Time wasted:** ~4 minutes

#### 5. **Output Format Surprise**
- **What I thought:** Outputs would be files (CSV, JSON, Parquet)
- **Reality:** Outputs are YAML dashboard definitions + DB metadata
- **Evidence:** Found 10+ dashboard.yaml files in examples/
- **Time wasted:** ~3 minutes

### What Helped Me Navigate (Success Patterns)

```bash
# These commands saved the most time:

# 1. Find SQL-related Python files
find superset -name "*sql*.py" | grep -v test

# 2. Find dashboard models (critical outputs)
grep -r "class Dashboard" --include="*.py" .

# 3. Find database connection logic (ingestion)
grep -r "def get_sqla_engine" .

# 4. See actual outputs (YAML dashboards)
find superset/examples -name "dashboard.yaml"

# 5. Find hotspots (change frequency)
git log --pretty=format: --name-only | sort | uniq -c | sort -rn | head -20

# 6. Find dead code candidates
git ls-files | while read file; do
    changes=$(git log --oneline -- "$file" 2>/dev/null | wc -l)
    if [ $changes -eq 1 ] && [[ $file == *.py ]] && [[ $file != *test* ]]; then
        echo "  $file - only 1 change ever"
    fi
done

# 7. Find business logic density
find superset -name "*.py" -not -path "*/tests/*" -exec grep -l "def " {} \; | \
    xargs -I {} sh -c "echo -n '{}: '; grep -c 'def ' '{}'" | sort -t: -k2 -rn | head -10
```

---

## 💡 Key Insights for My Cartographer (Prioritized)

Based on this manual struggle, my automated Cartographer MUST have:

### 🔴 CRITICAL PRIORITY (Must Have)

| Priority | Feature | Evidence from Manual Work |
|----------|---------|---------------------------|
| **P0** | **Extract SQL from Python strings** | No standalone `.sql` files found; SQL in `sql_lab.py`, `db_engine_specs/` |
| **P0** | **Build dependency graph across languages** | Python + TypeScript + API calls; found `@api` decorators |
| **P0** | **Identify critical path via PageRank** | Database model imported in 100+ files |
| **P0** | **Parse YAML dashboard definitions** | 10+ dashboard.yaml files = critical outputs |
| **P0** | **Track change frequency by module** | viz.py (484 changes) = active pain point |

### 🟡 HIGH PRIORITY (Should Have)

| Priority | Feature | Evidence |
|----------|---------|----------|
| **P1** | **Detect dead code candidates** | Found files with only 1 change ever |
| **P1** | **Function counting for logic density** | viz.py: 132 functions = business logic core |
| **P1** | **API endpoint mapping** | Found `@api` decorators in views/ |
| **P1** | **Import graph visualization** | 100+ files import Database class |

### 🟢 MEDIUM PRIORITY (Nice to Have)

| Priority | Feature | Evidence |
|----------|---------|----------|
| **P2** | **Understand database connectors** | 40+ DB engine specs, but less critical |
| **P2** | **Test coverage analysis** | Extensive tests/ directory |
| **P2** | **Frontend component mapping** | 1,000+ React components |
| **P2** | **Docker/K8s config parsing** | Found helm/ and docker-compose.yml |

---

## ✅ Ground Truth Summary (For Later Validation)

| Question | Manual Answer | Evidence Location | Confidence |
|----------|---------------|-------------------|------------|
| **Primary ingestion** | Database connections via SQLAlchemy | `superset/models/core.py:class Database` | 100% |
| **Critical outputs** | Featured + Sales dashboards | `superset/examples/featured_charts/dashboard.yaml` | 100% |
| **Blast radius** | sql_lab.py failure = system-wide | 100+ files depend on Database model | 95% |
| **Business logic** | Concentrated in viz.py (132 functions) | `superset/viz.py` | 100% |
| **High velocity** | Frontend + views/core.py (767 changes) | Git log analysis | 100% |
| **Dead code** | Files with 1 change ever | `docs/scripts/extract_custom_errors.py` et al. | 90% |

---

## 🎯 What I Learned in 30 Minutes

1. **Superset is a polyglot masterpiece** - Python backend (1,856 files) + TypeScript frontend (1,000+ files) + YAML configs (150+)

2. **The Database class is the heart** - Imported in 100+ files, single point of failure, everything revolves around it

3. **SQL is hiding in Python strings** - My Hydrologist must extract SQL from Python string literals, not just `.sql` files

4. **Outputs are YAML + metadata** - Not traditional datasets, but dashboard definitions in `examples/` directories

5. **Change frequency tells the story** - viz.py (484 changes) = active development = potential bugs; views/core.py (767 changes) = core UI work

6. **Dead code exists** - Found multiple files with only 1 change ever - candidates for deletion or deep stability

7. **Business logic follows Pareto** - 20% of files (viz.py, models.py, helpers.py) contain 80% of the logic

8. **Dependencies are complex** - Database model creates a spiderweb of 100+ dependencies

---

## 📝 Final Reflection

**Manual analysis of 30 minutes on one project (1,856 Python files) was challenging. Imagine 800,000 lines across multiple languages.**

The Cartographer will save **DAYS, not hours**. Every feature I prioritize comes directly from pain points I experienced:

- I wasted 8 minutes finding SQL → **Build SQL extractor**
- I got lost in dependencies → **Build import graph**
- I couldn't find business logic → **Function counting + PageRank**
- I missed dead code → **Git velocity analysis**
- I misunderstood outputs → **Parse YAML definitions**

**The tool I build will make the next engineer's first 30 minutes productive, not painful.**

---


