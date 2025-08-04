# Environment Variables Reference

This document lists all environment variables used by the Hybrid AI Council system for configuration. These variables enable cloud deployment and local development flexibility.

## 🔗 **Core API Configuration**

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | Host address for the FastAPI server |
| `API_PORT` | `8000` | Port for the FastAPI server |
| `PUBLIC_URL` | `None` | Full public URL for production deployment (overrides host/port) |
| `API_BASE_URL` | `http://localhost:8000` | Base URL for API requests (used by test scripts and demos) |
| `ENVIRONMENT` | `development` | Deployment environment (`development`, `production`, `staging`) |

## 🗄️ **Database Services**

### Redis Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `localhost` | Redis server hostname |
| `REDIS_PORT` | `6379` | Redis server port |

### TigerGraph Configuration  
| Variable | Default | Description |
|----------|---------|-------------|
| `TIGERGRAPH_HOST` | `http://localhost` | TigerGraph server URL |
| `TIGERGRAPH_PORT` | `14240` | TigerGraph server port |
| `TIGERGRAPH_USERNAME` | `tigergraph` | TigerGraph username |
| `TIGERGRAPH_PASSWORD` | `tigergraph` | TigerGraph password |

### Ollama Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | `localhost` | Ollama server hostname |
| `OLLAMA_PORT` | `11434` | Ollama server port |

## 🔒 **Security Configuration**

| Variable | Default | Description |
|----------|---------|-------------|
| `SECURITY_ENABLED` | `true` | Enable/disable security middleware |
| `RATE_LIMITING_ENABLED` | `true` | Enable/disable rate limiting |
| `SECURITY_HEADERS_ENABLED` | `true` | Enable/disable security headers |
| `REQUEST_VALIDATION_ENABLED` | `true` | Enable/disable input validation |

### Rate Limiting
| Variable | Default | Description |
|----------|---------|-------------|
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | `100` | General requests per minute limit |
| `RATE_LIMIT_REQUESTS_PER_HOUR` | `1000` | General requests per hour limit |
| `RATE_LIMIT_CHAT_PER_MINUTE` | `10` | Chat requests per minute limit |
| `RATE_LIMIT_VOICE_PER_MINUTE` | `5` | Voice requests per minute limit |
| `RATE_LIMIT_WEBSOCKET_CONNECTIONS` | `5` | Max WebSocket connections per IP |

### CORS Configuration
| Variable | Default | Description |
|----------|---------|-------------|
| `CORS_ALLOWED_ORIGINS` | `*` | Comma-separated list of allowed origins |
| `CORS_ALLOW_CREDENTIALS` | `false` | Allow credentials in CORS requests |
| `CORS_ALLOWED_METHODS` | `GET,POST,PUT,DELETE,OPTIONS` | Allowed HTTP methods |
| `CORS_ALLOWED_HEADERS` | `*` | Allowed headers |

### Security Headers
| Variable | Default | Description |
|----------|---------|-------------|
| `CSP_POLICY` | `default-src 'self'; script-src 'self' 'unsafe-inline'...` | Content Security Policy |
| `HSTS_MAX_AGE` | `31536000` | HSTS max age in seconds |

### Request Validation
| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_REQUEST_SIZE_MB` | `10` | Maximum request size in MB |
| `MAX_JSON_SIZE_MB` | `1` | Maximum JSON size in MB |
| `MAX_QUERY_PARAMS` | `50` | Maximum query parameters |

## 💾 **Caching Configuration**

| Variable | Default | Description |
|----------|---------|-------------|
| `CACHE_ENABLED` | `true` | Enable/disable prompt caching |
| `CACHE_TTL_HOURS` | `24` | Cache time-to-live in hours |
| `CACHE_MAX_PROMPT_LENGTH` | `1000` | Maximum prompt length to cache |
| `CACHE_SIMILARITY_THRESHOLD` | `0.95` | Similarity threshold for cache hits |

## 📝 **Logging Configuration**

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

## 🧠 **Pheromind Configuration**

| Variable | Default | Description |
|----------|---------|-------------|
| `PHEROMIND_TTL` | `12` | Pheromind signal TTL in seconds |

## 🚀 **Cloud Deployment Examples**

### Production Environment
```bash
# Production API Configuration
export ENVIRONMENT=production
export PUBLIC_URL=https://your-domain.com
export API_HOST=0.0.0.0
export API_PORT=8000

# Database Services (use your cloud providers)
export REDIS_HOST=your-redis-instance.cache.amazonaws.com
export REDIS_PORT=6379
export TIGERGRAPH_HOST=https://your-tigergraph-instance.com
export TIGERGRAPH_PORT=443

# Security (production-ready settings)
export CORS_ALLOWED_ORIGINS=https://your-domain.com,https://api.your-domain.com
export CORS_ALLOW_CREDENTIALS=true
export RATE_LIMIT_REQUESTS_PER_MINUTE=60
export RATE_LIMIT_REQUESTS_PER_HOUR=500
```

### Development Environment
```bash
# Development API Configuration
export ENVIRONMENT=development
export API_HOST=localhost
export API_PORT=8000
export API_BASE_URL=http://localhost:8000

# Local services
export REDIS_HOST=localhost
export TIGERGRAPH_HOST=http://localhost
export OLLAMA_HOST=localhost

# Relaxed security for development
export CORS_ALLOWED_ORIGINS=*
export RATE_LIMIT_REQUESTS_PER_MINUTE=1000
```

### Staging Environment
```bash
# Staging configuration (between dev and prod)
export ENVIRONMENT=staging
export PUBLIC_URL=https://staging.your-domain.com
export CORS_ALLOWED_ORIGINS=https://staging.your-domain.com
export RATE_LIMIT_REQUESTS_PER_MINUTE=80
```

## 🔧 **Migration Notes**

This system has been migrated from hardcoded localhost URLs to fully configurable environment variables. Key benefits:

- **Cloud-ready**: Easy deployment to any cloud provider
- **Environment isolation**: Different settings for dev/staging/prod
- **Security flexibility**: Configurable rate limits and CORS per environment
- **Service flexibility**: Easy to use managed services or different hosts

**Previous hardcoded patterns removed:**
- `http://localhost:8000` → `${API_BASE_URL}` or `${PUBLIC_URL}`
- `localhost:6379` → `${REDIS_HOST}:${REDIS_PORT}`
- `http://localhost:14240` → `${TIGERGRAPH_HOST}:${TIGERGRAPH_PORT}`
- `localhost:11434` → `${OLLAMA_HOST}:${OLLAMA_PORT}`