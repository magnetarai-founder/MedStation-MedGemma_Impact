# ElohimOS Monitoring Guide

Production monitoring setup for ElohimOS using Prometheus and Grafana.

---

## Overview

This directory contains monitoring configuration for ElohimOS:

- **Prometheus Alert Rules**: `ops/monitoring/alerts/elohimos_alerts.yml`
- **Grafana Dashboard**: `docs/monitoring/grafana_dashboards/elohimos_vault_ops.json`

### What's Monitored

- HTTP request rates and status codes
- P95/P50 latency (response times)
- Rate limiting (429 responses)
- Share link errors
- Vault operations (downloads, uploads)
- CPU and memory usage
- Authentication failures
- Top endpoints by traffic

---

## Quick Start

### Prerequisites

- **Prometheus** installed and running
- **Grafana** installed and running
- **ElohimOS** exporting metrics at `/metrics`

---

## Setup Prometheus

### 1. Verify ElohimOS Metrics Endpoint

ElohimOS exports Prometheus metrics at `/metrics`:

```bash
curl http://localhost:8000/metrics
```

Expected output (sample):
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",path="/api/v1/vault/files",status="200"} 1234.0

# HELP http_request_duration_seconds HTTP request latency
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{le="0.1"} 5678.0
http_request_duration_seconds_bucket{le="0.5"} 6789.0
...
```

### 2. Add to prometheus.yml

Add ElohimOS scrape config and alert rules:

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

# Alert manager
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['localhost:9093']

# Load alert rules
rule_files:
  - 'ops/monitoring/alerts/elohimos_alerts.yml'

# Scrape configs
scrape_configs:
  # ElohimOS API
  - job_name: 'elohimos'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
    scrape_timeout: 10s
```

### 3. Verify Configuration

```bash
# Check prometheus.yml syntax
promtool check config prometheus.yml

# Check alert rules syntax
promtool check rules ops/monitoring/alerts/elohimos_alerts.yml

# Reload Prometheus
curl -X POST http://localhost:9090/-/reload
```

### 4. Verify Scraping

Visit Prometheus UI:
- **Targets**: http://localhost:9090/targets
- **Graph**: http://localhost:9090/graph

Run test queries:
```promql
# Total request rate
sum(rate(http_requests_total[5m]))

# Error rate
sum(rate(http_requests_total{status=~"5.."}[5m]))

# P95 latency
histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))
```

---

## Setup Grafana Dashboard

### 1. Import Dashboard

**Option A: Via UI**
1. Open Grafana: http://localhost:3000
2. Navigate to **Dashboards** → **Import**
3. Upload `docs/monitoring/grafana_dashboards/elohimos_vault_ops.json`
4. Select Prometheus datasource
5. Click **Import**

**Option B: Via API**
```bash
curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @docs/monitoring/grafana_dashboards/elohimos_vault_ops.json
```

### 2. Configure Datasource

If Prometheus datasource not configured:

1. Go to **Configuration** → **Data Sources**
2. Click **Add data source** → **Prometheus**
3. Set URL: `http://localhost:9090`
4. Click **Save & Test**

### 3. View Dashboard

Navigate to **Dashboards** → **ElohimOS — Vault & API Overview**

---

## Dashboard Panels

### Panel 1: HTTP Request Rate by Status
- **Metric**: `http_requests_total` by status code
- **Shows**: Request volume split by 2xx, 4xx, 5xx
- **Alert**: High error rate (5xx > 1%)

### Panel 2: P95 Latency
- **Metric**: `http_request_duration_seconds_bucket` (histogram)
- **Shows**: P95 and P50 response times
- **Threshold**: Red line at 1s (SLO target)

### Panel 3: Rate Limiting (429 Responses)
- **Metric**: `http_requests_total{status="429"}`
- **Shows**: Rate limit enforcement
- **Alert**: >10/s sustained for 5m

### Panel 4: Share Link Errors
- **Metric**: `http_requests_total{path="/api/v1/vault/share.*", status="4..|5.."}`
- **Shows**: Share endpoint failures
- **Alert**: >5/s sustained for 5m

### Panel 5: Vault Downloads/Uploads
- **Metric**: `http_requests_total{path=~"/api/v1/vault/files/.*/download|upload"}`
- **Shows**: Vault operation volume

### Panel 6: CPU Usage
- **Metric**: `process_cpu_seconds_total`
- **Shows**: CPU utilization rate

### Panel 7: Memory Usage
- **Metric**: `process_resident_memory_bytes`
- **Shows**: RSS memory
- **Threshold**: Warning at 5GB (3 models ≈ 4.5GB)

### Panel 8: Error Rate by Endpoint
- **Metric**: `http_requests_total{status=~"5.."}` grouped by path
- **Shows**: Top 10 endpoints with errors (table)

### Panel 9: Authentication Failures
- **Metric**: `http_requests_total{path="/api/v1/auth/login", status="401|403"}`
- **Shows**: Failed login attempts
- **Alert**: >5/s (potential brute force)

### Panel 10: Top Endpoints by Request Count
- **Metric**: `http_requests_total` grouped by path and method
- **Shows**: Top 15 busiest endpoints (table)

---

## Metric Name Variations

If your ElohimOS instance uses different metric names, update the dashboard:

### Latency Metric (Histogram vs Summary)

**Default (Histogram)**:
```promql
histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))
```

**If Using Summary**:
```promql
http_request_duration_seconds{quantile="0.95"}
```

### Adjusting Metric Names

Edit the dashboard JSON or use Grafana UI:
1. Edit panel → **Queries** tab
2. Update metric names to match your exported metrics
3. Save dashboard

---

## Alert Rules

See `ops/monitoring/alerts/README.md` for complete alert rule documentation.

### Alert Summary

| Alert | Threshold | Severity | Action |
|-------|-----------|----------|--------|
| High 5xx Rate | >1% for 5m | Page | Investigate backend errors |
| High P95 Latency | >1s for 5m | Page | Check database, models |
| Rate Limit Spike | >10/s for 5m | Warn | Check client behavior |
| Share Errors | >5/s for 5m | Warn | Check tokens, IP throttles |
| High Memory | >5GB for 10m | Warn | Check model preloader |

---

## Testing Monitoring

### Generate Test Load

```bash
# Install Apache Bench
brew install httpd

# Generate load
ab -n 1000 -c 10 http://localhost:8000/api/v1/vault/search?query=test

# Trigger errors (404s)
for i in {1..100}; do
  curl http://localhost:8000/api/v1/invalid-endpoint
  sleep 0.1
done
```

### Use Locust for Load Testing

```bash
# Run load test
locust -f apps/backend/locustfile.py --host http://localhost:8000

# Open UI
# http://localhost:8089
# Set: 50 users, 5 spawn rate, 5 minutes
```

Watch metrics update in Grafana dashboard.

---

## Production Deployment

### Recommended Setup

```
┌─────────────┐
│  ElohimOS   │ :8000 → /metrics
└─────┬───────┘
      │
      ↓ scrape (15s)
┌─────────────┐
│ Prometheus  │ :9090
└─────┬───────┘
      │
      ↓ query
┌─────────────┐
│   Grafana   │ :3000
└─────────────┘
      │
      ↓ alerts
┌─────────────┐
│Alertmanager │ :9093 → Slack/PagerDuty
└─────────────┘
```

### Retention Policies

**Prometheus**:
```bash
# Start with 30-day retention
prometheus \
  --config.file=prometheus.yml \
  --storage.tsdb.retention.time=30d \
  --storage.tsdb.path=/var/lib/prometheus
```

**Grafana**:
- Default data source: Prometheus
- Dashboard refresh: 10s
- Auto-refresh: Enabled

---

## Troubleshooting

### Metrics Not Appearing

1. **Check ElohimOS is exporting**:
   ```bash
   curl http://localhost:8000/metrics
   ```

2. **Check Prometheus scraping**:
   - Visit http://localhost:9090/targets
   - Verify `elohimos` job is UP

3. **Check Prometheus logs**:
   ```bash
   journalctl -u prometheus -f
   ```

### Dashboard Shows No Data

1. **Verify datasource**: Grafana → Configuration → Data Sources → Prometheus
2. **Check time range**: Dashboard time picker (top right)
3. **Test query**: Grafana → Explore → Run simple query like `up`

### Alerts Not Firing

1. **Check Prometheus evaluation**:
   - Visit http://localhost:9090/alerts
   - Verify rules loaded and evaluating

2. **Check expression syntax**:
   ```bash
   promtool check rules ops/monitoring/alerts/elohimos_alerts.yml
   ```

3. **Test alert manually**:
   - Visit Prometheus → Graph
   - Paste alert expression
   - Verify it returns data when threshold exceeded

---

## Support

- **ElohimOS Issues**: https://github.com/hipps-joshua/ElohimOS/issues
- **Prometheus Docs**: https://prometheus.io/docs/
- **Grafana Docs**: https://grafana.com/docs/
- **Alert Rules**: `ops/monitoring/alerts/README.md`
