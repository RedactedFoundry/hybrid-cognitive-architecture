# 🔒 Security Configuration Guide

## Database Password Security

### Development Environment
- Default TigerGraph password `tigergraph` is allowed with warnings
- Security warnings will appear in logs to remind you to set secure passwords

### Production Environment
**CRITICAL**: Set secure passwords via environment variables:

```bash
# Required for production deployment
export ENVIRONMENT=production
export TIGERGRAPH_PASSWORD=your_strong_password_here

# Password requirements for production:
# - Minimum 8 characters
# - Cannot be "tigergraph" default
# - Unique and complex recommended
```

### Environment Variables

| Variable | Required | Default | Production Notes |
|----------|----------|---------|------------------|
| `ENVIRONMENT` | No | `development` | Set to `production` for prod deployment |
| `TIGERGRAPH_PASSWORD` | Production only | `tigergraph` (dev) | **REQUIRED** in production |
| `TIGERGRAPH_USERNAME` | No | `tigergraph` | Change for production |

### Security Validation

The system will:
- ✅ **Allow** weak passwords in development (with warnings)
- ❌ **Block** weak passwords in production (with errors)
- ❌ **Block** default passwords in production
- 📝 **Log** security warnings for audit trails

### Cloud Deployment Checklist

Before deploying to cloud:

1. ✅ Set `ENVIRONMENT=production`
2. ✅ Set strong `TIGERGRAPH_PASSWORD` 
3. ✅ Change default `TIGERGRAPH_USERNAME`
4. ✅ Verify no hardcoded credentials in code
5. ✅ Test configuration loading

### Example Production Setup

```bash
# Render.com, AWS, or other cloud provider
ENVIRONMENT=production
TIGERGRAPH_USERNAME=hybrid_ai_admin
TIGERGRAPH_PASSWORD=SecureP@ssw0rd123!
TIGERGRAPH_HOST=https://your-tigergraph.cloud
```

**⚠️ Never commit credentials to version control!**