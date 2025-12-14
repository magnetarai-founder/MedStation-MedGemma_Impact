# Observability - System Monitoring and Diagnostics

**Date:** 2025-12-13
**Status:** ✅ Implemented

---

## 🎯 Overview

Comprehensive observability system for monitoring MagnetarStudio backend performance, errors, and health.

**What We Monitor:**
- ✅ Request timing and throughput
- ✅ Database query performance
- ✅ Error tracking and aggregation
- ✅ Cache hit rates and memory usage
- ✅ Per-endpoint performance metrics

**Why It Matters:**
- Can't fix what you can't measure
- Identify bottlenecks before they become problems
- Track performance regressions
- Debug production issues faster

---

## 📊 Architecture

### Three-Layer Monitoring

```
┌─────────────────────────────────────────────────────┐
│                  Metrics API                        │
│        GET /metrics/summary - Overview              │
│        GET /metrics/system - All metrics            │
│        GET /metrics/requests - Request stats        │
│        GET /metrics/database - Query stats          │
│        GET /metrics/cache - Cache stats             │
│        GET /metrics/errors - Error tracking         │
└─────────────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Request    │  │   Database   │  │     Cache    │
│  Middleware  │  │   Profiler   │  │   Metrics    │
│              │  │              │  │              │
│ • Timing     │  │ • Query time │  │ • Hit rate   │
│ • Errors     │  │ • Slow logs  │  │ • Memory     │
│ • By endpoint│  │ • Failed     │  │ • Keys count │
└──────────────┘  └──────────────┘  └──────────────┘
```

### Components

1. **Request Middleware** (`api/observability_middleware.py`)
   - Wraps every HTTP request
   - Times request processing
   - Catches and logs errors
   - Tracks metrics per endpoint

2. **Database Profiler** (`api/db_profiler.py`)
   - Wraps SQLite connections
   - Times every query
   - Logs slow queries (>50ms)
   - Warns on very slow queries (>200ms)

3. **Metrics API** (`api/routes/metrics.py`)
   - Exposes all collected metrics
   - Health checks for monitoring systems
   - Summary endpoint for dashboards

---

## 🚀 Quick Start

### Check System Health

```bash
# Quick health check
curl http://localhost:8000/metrics/health

# Response:
{
  "status": "healthy",
  "service": "magnetar-studio-backend",
  "message": "Metrics service operational"
}
```

### Get Metrics Summary

```bash
# High-level overview
curl http://localhost:8000/metrics/summary

# Response:
{
  "overview": {
    "total_requests": 1523,
    "success_rate_percent": 98.5,
    "average_response_time_ms": 45.2,
    "slow_request_rate_percent": 2.1
  },
  "performance": {
    "cache_hit_rate_percent": 87.3,
    "database_queries": 2341,
    "database_avg_time_ms": 12.5,
    "slow_database_queries": 15
  },
  "health": {
    "failed_requests": 23,
    "failed_database_queries": 3,
    "error_types": 2
  }
}
```

### Monitor Request Performance

```bash
# Request timing statistics
curl http://localhost:8000/metrics/requests

# Response:
{
  "total_requests": 1523,
  "successful_requests": 1500,
  "failed_requests": 23,
  "slow_requests": 32,
  "very_slow_requests": 5,
  "average_time_ms": 45.2,
  "total_time_ms": 68830.4
}
```

### Check Database Performance

```bash
# Query performance stats
curl http://localhost:8000/metrics/database

# Response:
{
  "total_queries": 2341,
  "slow_queries": 15,
  "very_slow_queries": 2,
  "failed_queries": 3,
  "average_time_ms": 12.5,
  "total_time_ms": 29262.5
}
```

### Track Errors

```bash
# Error tracking
curl http://localhost:8000/metrics/errors

# Response:
{
  "error_counts": {
    "ValueError": 12,
    "HTTPException": 8,
    "OperationalError": 3
  },
  "recent_errors": [
    {
      "timestamp": "2025-12-13T10:23:45.123Z",
      "method": "POST",
      "path": "/api/chat/send",
      "error_type": "ValueError",
      "elapsed_ms": 15.3
    }
  ],
  "total_error_types": 3
}
```

### Per-Endpoint Metrics

```bash
# Top 10 endpoints by request count
curl http://localhost:8000/metrics/endpoints?limit=10

# Response:
{
  "endpoints": [
    {
      "endpoint": "GET /api/chat/sessions",
      "count": 432,
      "average_time_ms": 25.3,
      "total_time_ms": 10929.6,
      "errors": 2,
      "error_rate": 0.46
    },
    {
      "endpoint": "POST /api/chat/send",
      "count": 287,
      "average_time_ms": 120.5,
      "total_time_ms": 34583.5,
      "errors": 5,
      "error_rate": 1.74
    }
  ],
  "total_endpoints": 10
}
```

---

## 📈 What Gets Logged

### Request Timing

**Normal requests:**
```
DEBUG: ✓ GET /api/chat/sessions → 200 (25ms)
```

**Slow requests (>1s):**
```
INFO: 🐌 Slow request (1250ms): POST /api/chat/send → 200
```

**Very slow requests (>5s):**
```
WARNING: ⚠️  VERY SLOW REQUEST (5430ms): GET /api/vault/items → 200
```

**Failed requests:**
```
ERROR: ❌ Request failed (150ms): POST /api/auth/login - ValueError: Invalid credentials
```

### Database Query Timing

**Normal queries:**
```
# No logging (below threshold)
```

**Slow queries (>50ms):**
```
INFO: 🐌 Slow query (75.3ms) [teams.db]: SELECT * FROM team_vault_items WHERE team_id = ?...
```

**Very slow queries (>200ms):**
```
WARNING: ⚠️  VERY SLOW QUERY (350.2ms) [chat_memory.db]: SELECT * FROM chat_messages WHERE user_id = ?...
```

**Failed queries:**
```
ERROR: ❌ Query failed (25.1ms) [elohimos_app.db]: SELECT * FROM users WHERE email = ? - no such column: email
```

---

## 🔧 Configuration

### Thresholds

**Request Timing** (in `api/observability_middleware.py`):
```python
SLOW_REQUEST_THRESHOLD_MS = 1000      # Log requests > 1 second
VERY_SLOW_REQUEST_THRESHOLD_MS = 5000  # Warn on requests > 5 seconds
```

**Database Queries** (in `api/db_profiler.py`):
```python
SLOW_QUERY_THRESHOLD_MS = 50          # Log queries > 50ms
VERY_SLOW_QUERY_THRESHOLD_MS = 200    # Warn on queries > 200ms
```

### Adjusting Thresholds

For development (more verbose):
```python
SLOW_REQUEST_THRESHOLD_MS = 500    # Log anything > 500ms
SLOW_QUERY_THRESHOLD_MS = 20       # Log anything > 20ms
```

For production (less noise):
```python
SLOW_REQUEST_THRESHOLD_MS = 2000   # Only log very slow requests
SLOW_QUERY_THRESHOLD_MS = 100      # Only log really slow queries
```

---

## 🛠️ Usage in Code

### Using Profiled Database Connections

**Instead of:**
```python
import sqlite3

conn = sqlite3.connect('.neutron_data/teams.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM teams WHERE team_id = ?", (team_id,))
```

**Use:**
```python
from api.db_profiler import get_profiled_connection

conn = get_profiled_connection('.neutron_data/teams.db')
cursor = conn.cursor()
cursor.execute("SELECT * FROM teams WHERE team_id = ?", (team_id,))
# Automatically logs if query is slow!
```

**Or with context manager:**
```python
from api.db_profiler import profiled_connection

with profiled_connection('.neutron_data/teams.db') as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM teams")
    results = cursor.fetchall()
# Connection auto-closed, queries auto-profiled
```

### Analyzing Query Plans

Find missing indexes:
```python
from api.db_profiler import analyze_query_plan, get_profiled_connection

conn = get_profiled_connection('.neutron_data/teams.db')

analyze_query_plan(
    conn,
    "SELECT * FROM team_vault_items WHERE team_id = ? AND item_type = ?",
    ("team123", "password")
)
# Logs query plan, warns if full table scan detected
```

Output:
```
📊 Query Plan Analysis:
Query: SELECT * FROM team_vault_items WHERE team_id = ? AND item_type = ?...
  SEARCH TABLE team_vault_items USING INDEX idx_vault_team_type_deleted (team_id=? AND item_type=?)
✓ Query uses indexes efficiently
```

Or if missing index:
```
📊 Query Plan Analysis:
Query: SELECT * FROM users WHERE job_role = ?...
  SCAN TABLE users
⚠️  Full table scan detected! Consider adding an index.
```

---

## 📊 Monitoring Dashboards

### What to Monitor

**1. Request Performance**
- Average response time (should be <100ms)
- Slow request rate (should be <5%)
- Error rate (should be <1%)

**2. Database Performance**
- Average query time (should be <20ms)
- Slow query count (investigate any >200ms)
- Failed queries (should be 0)

**3. Cache Effectiveness**
- Hit rate (should be >80%)
- Memory usage (monitor growth)
- Key count (ensure not unbounded)

**4. Error Patterns**
- Error types (identify systemic issues)
- Recent errors (debug production issues)
- Error frequency (detect spikes)

### Alert Thresholds

**Production Alerts:**
- ⚠️  Warning: Average response time >200ms
- 🚨 Critical: Average response time >500ms
- ⚠️  Warning: Error rate >2%
- 🚨 Critical: Error rate >5%
- ⚠️  Warning: Cache hit rate <70%
- 🚨 Critical: Cache hit rate <50%

---

## 🔄 Metrics Reset

**Reset all metrics** (for testing or after maintenance):
```bash
curl -X POST http://localhost:8000/metrics/reset

# Response:
{
  "status": "success",
  "message": "All metrics have been reset",
  "timestamp": "now"
}
```

**WARNING:** This clears all accumulated statistics. Use only for:
- Testing metrics collection
- After maintenance windows
- When metrics are corrupted

---

## 🎯 Performance Targets

### Response Times

| Target | Threshold | Status |
|--------|-----------|--------|
| Excellent | < 50ms | ✅ |
| Good | 50-100ms | ✅ |
| Acceptable | 100-500ms | ⚠️ |
| Slow | 500-1000ms | ⚠️ |
| Very Slow | > 1000ms | 🚨 |

### Database Queries

| Target | Threshold | Status |
|--------|-----------|--------|
| Excellent | < 10ms | ✅ |
| Good | 10-50ms | ✅ |
| Acceptable | 50-100ms | ⚠️ |
| Slow | 100-200ms | ⚠️ |
| Very Slow | > 200ms | 🚨 |

### Cache Hit Rate

| Target | Threshold | Status |
|--------|-----------|--------|
| Excellent | > 90% | ✅ |
| Good | 80-90% | ✅ |
| Acceptable | 70-80% | ⚠️ |
| Poor | 50-70% | ⚠️ |
| Critical | < 50% | 🚨 |

---

## 🔍 Troubleshooting

### High Response Times

**Check:**
1. Database query times (`/metrics/database`)
2. Cache hit rate (`/metrics/cache`)
3. Per-endpoint metrics (`/metrics/endpoints`)

**Fix:**
- Add database indexes for slow queries
- Increase cache TTL for frequently accessed data
- Optimize slow endpoints

### Many Slow Queries

**Check:**
1. Query plans with `analyze_query_plan()`
2. Database indexes with `PRAGMA index_list(table_name)`
3. Table sizes with `SELECT COUNT(*) FROM table`

**Fix:**
- Add missing indexes
- Optimize query structure
- Consider archiving old data

### Low Cache Hit Rate

**Check:**
1. Cache key patterns (are they too specific?)
2. TTL values (are they too short?)
3. Redis memory usage

**Fix:**
- Adjust cache key structure
- Increase TTL for stable data
- Add more cacheable endpoints

### Error Spikes

**Check:**
1. Recent errors (`/metrics/errors`)
2. Error types (what's failing?)
3. Failed endpoints (`/metrics/endpoints`)

**Fix:**
- Review error logs
- Add input validation
- Improve error handling

---

## 📁 Files

**Core Components:**
- `api/observability_middleware.py` (278 lines) - Request timing and error tracking
- `api/db_profiler.py` (291 lines) - Database query profiling
- `api/routes/metrics.py` (275 lines) - Metrics API endpoints

**Integration:**
- `api/router_registry.py` - Middleware registration (line 54-61)

**Documentation:**
- `OBSERVABILITY.md` - This file

---

## ✅ Summary

**Implemented:**
- ✅ Request timing middleware
- ✅ Database query profiler
- ✅ Error tracking and aggregation
- ✅ Metrics API endpoints
- ✅ Slow query detection
- ✅ Per-endpoint performance tracking
- ✅ Cache metrics integration

**Benefits:**
- 🔍 Full visibility into system performance
- 🐛 Faster debugging of production issues
- 📊 Data-driven performance optimization
- 🚨 Early detection of problems

**Next Steps:**
1. ✅ Observability complete
2. 🔄 Monitor metrics in development
3. 🔄 Set up alerting for production
4. 🔄 Create performance dashboards
5. ⏳ Move to Priority 3: API Design & Consistency

---

**Status:** ✅ Production-ready
**Date:** 2025-12-13
**Foundation Layer:** Complete (Database + Observability)
