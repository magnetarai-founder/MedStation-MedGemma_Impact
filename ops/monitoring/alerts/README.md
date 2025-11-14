# ElohimOS Prometheus Alert Rules

This directory contains Prometheus alert rules for ElohimOS production monitoring.

---

## Alert Rules

**File**: `elohimos_alerts.yml`

### SLO-Aligned Alerts

| Alert | Threshold | Duration | Severity | Description |
|-------|-----------|----------|----------|-------------|
| `ElohimOSHighErrorRate` | 5xx > 1% | 5m | page | High error rate (service degradation) |
| `ElohimOSHighLatency` | P95 > 1s | 5m | page | Slow response times |
| `ElohimOSRateLimitSpike` | 429 > 10/s | 5m | warn | Excessive rate limiting |
| `ElohimOSShareLinkErrors` | Errors > 5/s | 5m | warn | Share endpoint failures |
| `ElohimOSHighMemory` | Memory > 5GB | 10m | warn | Memory usage high |
| `ElohimOSDatabaseLockWait` | Locks > 1/s | 5m | warn | SQLite contention |
| `ElohimOSVaultUploadFailures` | Failures > 0.5/s | 5m | warn | Upload failures |
| `ElohimOSHighDownloadRate` | Downloads > 100/s | 5m | info | Potential abuse |
| `ElohimOSAuthFailureSpike` | Failures > 5/s | 5m | warn | Brute force or misconfiguration |
| `ElohimOSModelPreloaderErrors` | Errors > 0.1/s | 5m | warn | Model loading issues |

---

## Setup

### 1. Include in Prometheus Config

Add to your `prometheus.yml`:

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

# Alert manager configuration
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['localhost:9093']

# Load alert rules
rule_files:
  - 'ops/monitoring/alerts/elohimos_alerts.yml'

# Scrape ElohimOS metrics
scrape_configs:
  - job_name: 'elohimos'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### 2. Verify Alert Rules

```bash
# Check syntax
promtool check rules ops/monitoring/alerts/elohimos_alerts.yml

# Test alert rules
promtool test rules ops/monitoring/alerts/elohimos_alerts.yml
```

### 3. Reload Prometheus

```bash
# Send SIGHUP to reload config
kill -HUP $(pgrep prometheus)

# Or use API
curl -X POST http://localhost:9090/-/reload
```

---

## Metric Name Assumptions

The alert rules assume the following metric names are exported by ElohimOS:

### HTTP Metrics
- `http_requests_total{status, path}` - Total HTTP requests with status code and path labels
- `http_request_duration_seconds_bucket{le}` - Histogram of request durations

### Process Metrics
- `process_resident_memory_bytes{job}` - Process memory usage

### Custom Metrics (Optional)
- `sqlite_lock_wait_total` - SQLite lock wait events
- `model_preload_errors_total` - Model preloader errors

---

## Adjusting for Your Metrics

### If Using Summary Instead of Histogram

Replace the latency alert expression:

```yaml
# For histogram (default)
expr: |
  histogram_quantile(0.95,
    sum by (le) (rate(http_request_duration_seconds_bucket[5m]))
  ) > 1

# For summary with quantiles
expr: |
  http_request_duration_seconds{quantile="0.95"} > 1
```

### If Metric Names Differ

Update the `expr` fields to match your actual metric names. Common variations:

- `http_requests_total` → `requests_total` or `api_requests_total`
- `http_request_duration_seconds` → `request_duration_seconds`
- `process_resident_memory_bytes` → `process_memory_bytes`

---

## Testing Alerts

### Trigger Test Alerts

```bash
# Simulate high error rate
for i in {1..100}; do
  curl http://localhost:8000/api/v1/invalid-endpoint
  sleep 0.1
done

# Simulate high load
ab -n 10000 -c 100 http://localhost:8000/api/v1/vault/search?query=test

# Check pending/firing alerts
curl http://localhost:9090/api/v1/alerts | jq
```

### Using amtool

```bash
# Install amtool
go install github.com/prometheus/alertmanager/cmd/amtool@latest

# Check active alerts
amtool alert query

# Silence an alert
amtool silence add alertname=ElohimOSHighMemory
```

---

## Runbooks

### High Error Rate (5xx)
1. Check ElohimOS logs: `tail -f logs/elohimos.log`
2. Verify database connectivity
3. Check disk space: `df -h`
4. Review recent deployments

### High Latency
1. Check active database queries
2. Verify model preloader status (3 models should be <5s)
3. Check CPU usage: `top -pid $(pgrep uvicorn)`
4. Review vault file sizes (large files slow down operations)

### Rate Limit Spike
1. Identify client IPs hitting rate limits
2. Check if legitimate traffic (expected bulk operations)
3. Adjust rate limits if needed in `rate_limiter.py`
4. Consider IP allowlisting for trusted clients

### Memory High
1. Check model preloader: 3 models ≈ 4.5GB is normal
2. If >5GB sustained, investigate memory leaks
3. Restart uvicorn workers: `kill -HUP $(pgrep uvicorn)`
4. Monitor memory trend in Grafana

---

## Integration with Alertmanager

Example Alertmanager config for Slack notifications:

```yaml
# alertmanager.yml
global:
  slack_api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'

route:
  receiver: 'slack-alerts'
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

receivers:
  - name: 'slack-alerts'
    slack_configs:
      - channel: '#elohimos-alerts'
        title: '{{ .GroupLabels.severity | toUpper }}: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}\n{{ end }}'
```

---

## Support

For issues with alert rules:
- GitHub Issues: https://github.com/hipps-joshua/ElohimOS/issues
- Documentation: `docs/monitoring/`
