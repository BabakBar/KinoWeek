# Architecture Document: Astor Kino Notifier (KinoWeek)

## Executive Summary

This document outlines the complete technical architecture for the Astor Kino Notifier system, a production-grade web scraping and notification service that automatically extracts Original Version (OV) movie schedules from Astor Grand Cinema Hannover and delivers formatted reports via Telegram.

## System Overview

The system follows a microservices architecture with clear separation of concerns:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Scheduler     │───▶│   Scraper        │───▶│   Notifier      │
│  (GitHub/Cron)  │    │  (httpx/API)     │    │  (Telegram)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Cron Job      │    │   Direct API     │    │   Bot API       │
│   (Weekly)      │    │   Calls (HTTP)   │    │   Integration   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

**Architecture Note**: Current implementation uses direct API calls via httpx (not browser automation). This is faster, more reliable, and requires no headless browser infrastructure.

## Component Architecture

### 1. Core Scraper Module (`scraper.py`)

**Purpose**: Extract movie schedule data directly from PremiumKino API

**Key Components**:
- **MovieInfo**: Data class for movie metadata (duration, rating, year, country, genres)
- **Showtime**: Data class for individual showtime (datetime, time_str, version)
- **is_original_version()**: Filter logic for OV vs dubbed content
- **scrape_movies()**: Main API client using httpx

**Data Flow**:
```
API Request (httpx) → JSON Response → Parse Movies & Genres →
Filter OV Performances → Build MovieInfo Objects →
Chronological Sort → Return Structured Schedule
```

**Implementation Details**:
```python
# Direct API access - no browser needed
api_url = "https://backend.premiumkino.de/v1/de/hannover/program"
with httpx.Client() as client:
    response = client.get(api_url, headers=headers)
    data = response.json()
```

### 2. Container Layer (`Dockerfile`)

**Multi-stage Build Strategy**:
- **Stage 1**: Build environment with Python and dependencies
- **Stage 2**: Runtime environment with only necessary components
- **Security**: Non-root user, minimal attack surface
- **Optimization**: Layer caching, minimal final image size

### 3. Deployment Layer (Coolify)

**Components**:
- **Scheduled Task Service**: Cron-based execution
- **Environment Management**: Secure secret handling
- **Resource Monitoring**: Logs and execution tracking
- **Auto-recovery**: Retry logic and failure handling

## Data Architecture

### Input Data Sources
```
Primary Source: https://backend.premiumkino.de/v1/de/hannover/program
├── movies[]          # Metadata: title, duration, rating, year, country, genreIds
├── performances[]    # Showtimes: begin ISO timestamp, language information
└── genres[]          # Lookup table for genre IDs → names
```

### Internal Data Structure
```python
schedule_data = {
    "Mon 24.11.": {
        "Wicked: Part 2": {
            "info": MovieInfo(
                title="Wicked: Part 2",
                duration=113,
                rating=12,
                year=2024,
                country="US",
                genres=["Fantasy", "Adventure"],
            ),
            "showtimes": [
                Showtime(
                    datetime=datetime(2024, 11, 24, 19, 30),
                    time_str="19:30",
                    version="Sprache: Englisch, Untertitel: Deutsch",
                )
            ],
        }
    }
}
```

### Output Formats
1. **Telegram Message**: Human-readable text with length limits
2. **JSON Backup**: Machine-readable for historical analysis
3. **Log Files**: Structured logging for monitoring

## Error Handling Strategy

### Failure Categories and Responses

#### 1. Network Failures
- **Detection**: Timeout, connection errors, HTTP status codes
- **Response**: Exponential backoff retry (max 3 attempts)
- **Fallback**: Send error notification via Telegram

#### 2. API Schema Changes
- **Detection**: Missing JSON fields, unexpected data structure, KeyError exceptions
- **Response**: Graceful degradation, log schema changes, partial data extraction
- **Notification**: Alert about potential API updates requiring code changes

#### 3. HTTP Request Failures
- **Detection**: httpx timeout, connection errors, HTTP status codes
- **Response**: Retry with exponential backoff (recommended enhancement)
- **Logging**: Detailed error context for debugging

#### 4. Telegram API Failures
- **Detection**: API error responses, rate limiting
- **Response**: Retry with backoff, queue message for later
- **Fallback**: Log message content for manual review

#### 5. Data Validation Failures
- **Detection**: Empty datasets, malformed data patterns
- **Response**: Skip invalid entries, continue processing
- **Reporting**: Include validation summary in logs

### Error Recovery Hierarchy
```
Level 1: Retry with same configuration (immediate)
Level 2: Retry with backoff (exponential)
Level 3: Restart component (HTTP client, connection)
Level 4: Graceful failure with notification
```

## Testing Strategy

### Test Pyramid Structure

#### 1. Unit Tests (70%)
- **Data Extraction Logic**: Mock httpx responses with representative JSON payloads
- **Data Formatting**: Input/output validation
- **Telegram Integration**: API call mocking
- **Error Handling**: Exception scenarios

#### 2. Integration Tests (20%)
- **API Integration**: End-to-end flow with recorded API fixtures
- **Data Parsing**: JSON schema handling and OV filtering
- **End-to-End Flow**: Complete scraping cycle
- **Telegram Communication**: Real Telegram bot integration

#### 3. System Tests (10%)
- **Container Execution**: Docker environment testing
- **Scheduled Execution**: Cron job simulation
- **Resource Limits**: Memory and time constraints
- **Failure Scenarios**: Network interruption testing

### Test Data Management
- **Mock API Payloads**: Captured JSON responses for deterministic tests
- **Test Fixtures**: Known movie metadata and performance combinations
- **Environment Isolation**: Separate test database/chat
- **CI/CD Integration**: Automated test execution

## Security Architecture

### Threat Mitigation

#### 1. Secret Management
- **Environment Variables**: All sensitive data in env vars
- **No Hardcoded Values**: Tokens, URLs, credentials externalized
- **Access Control**: Principle of least privilege
- **Audit Trail**: Log access to sensitive operations

#### 2. Container Security
- **Non-root User**: Limited filesystem permissions
- **Minimal Base Image**: Reduced attack surface
- **Dependency Scanning**: Vulnerability assessment
- **Resource Limits**: CPU/memory constraints

#### 3. Network Security
- **HTTPS Only**: Encrypted communication
- **Certificate Validation**: Proper SSL verification
- **Rate Limiting**: Respect website policies
- **User Agent Headers**: Standard browser identification for API calls

#### 4. Data Protection
- **Input Validation**: Sanitize all extracted data
- **Output Sanitization**: Prevent injection attacks
- **Log Redaction**: Remove sensitive information from logs
- **Data Retention**: Limited storage of historical data

## Performance Architecture

### Optimization Strategies

#### 1. Scraping Performance
- **Efficient API Calls**: Single API request fetches all data (no pagination needed)
- **In-Memory Processing**: Fast JSON parsing and data transformation
- **Resource Management**: Efficient HTTP client usage via context managers
- **Connection Reuse**: HTTP connection pooling via httpx.Client context manager

#### 2. Container Performance
- **Layer Caching**: Optimize Docker build times
- **Image Size**: Minimize runtime footprint
- **Startup Time**: Fast container initialization
- **Memory Efficiency**: Optimize Python runtime

#### 3. Network Performance
- **Connection Pooling**: Reuse HTTP connections
- **Compression**: Enable response compression
- **Timeout Management**: Appropriate timeout values
- **Retry Logic**: Intelligent backoff strategies

### Monitoring Metrics
```
Performance Indicators:
├── Execution Time (target: < 5 minutes)
├── Memory Usage (target: < 512MB)
├── Success Rate (target: > 95%)
├── Data Accuracy (target: 100% validation)
└── Error Recovery Time (target: < 1 minute)
```

## Deployment Architecture

### Coolify Integration

#### 1. Resource Configuration
```
Service Type: Scheduled Task
Repository: GitHub (KinoWeek)
Branch: main
Schedule: Cron expression (0 20 * * 1)
Environment: Production
```

#### 2. Environment Variables
```
Required:
├── TELEGRAM_BOT_TOKEN: Bot authentication token
├── TELEGRAM_CHAT_ID: Target chat identifier
└── LOG_LEVEL: Logging verbosity (INFO/DEBUG)

Optional:
├── RETRY_ATTEMPTS: Maximum retry count (default: 3)
├── TIMEOUT_SECONDS: Operation timeout (default: 300)
└── DRY_RUN: Test mode without sending (default: false)
```

#### 3. Resource Limits
```
Memory: 512MB limit
CPU: 0.5 core limit
Storage: 1GB ephemeral
Network: Outbound HTTPS only
Timeout: 10 minutes execution limit
```

### Deployment Pipeline
```
Git Push → Coolify Webhook → Docker Build → 
Container Registry → Scheduled Execution → 
Log Collection → Monitoring Alert
```

## Monitoring and Observability

### Logging Strategy
```
Log Levels:
├── ERROR: Failures requiring attention
├── WARN: Unexpected but recoverable situations
├── INFO: Normal operation milestones
└── DEBUG: Detailed execution tracing
```

### Key Metrics
1. **Business Metrics**
   - Movies extracted per run
   - Data accuracy validation
   - Notification delivery success

2. **Technical Metrics**
   - Script execution duration
   - Memory usage patterns
   - Network request counts
   - Error rates by category

3. **Operational Metrics**
   - Scheduled execution adherence
   - Container restart frequency
   - Resource utilization trends

### Alerting Strategy
```
Alert Conditions:
├── Script execution failure
├── Data extraction below threshold
├── Telegram notification failure
├── Container resource exhaustion
└── Scheduled job missed execution
```

## Scalability Considerations

### Current Scale (Single Cinema)
- **Weekly Execution**: One scrape per week
- **Data Volume**: ~50 movies, ~200 showtimes
- **Resource Needs**: Minimal (single container)

### Future Expansion Paths
1. **Multi-Cinema Support**: Add city/cinema parameters
2. **Increased Frequency**: Daily instead of weekly execution
3. **Additional Channels**: Email, Slack, webhook notifications
4. **Historical Analysis**: Database storage for trend analysis
5. **API Service**: RESTful endpoint for on-demand queries

### Architectural Adaptations
- **Configuration Management**: External config for multiple sources
- **Database Integration**: Persistent storage for historical data
- **Message Queue**: Async processing for multiple notifications
- **Load Balancing**: Container orchestration for high availability

## Risk Assessment and Mitigation

### High-Risk Areas
1. **API Schema Changes**: Backend contract shifts may break parsing
   - **Mitigation**: Schema validation, monitoring alerts, quick updates

2. **Third-party APIs**: Telegram Bot API reliability
   - **Mitigation**: Retry logic, fallback notifications, API monitoring

3. **Scheduled Execution**: Cron job reliability
   - **Mitigation**: Health checks, manual trigger capability, logging

4. **Data Accuracy**: Parsing errors or missed content
   - **Mitigation**: Validation rules, sample comparisons, manual review

### Business Continuity
- **Backup Communication**: Alternative notification channels
- **Manual Override**: Direct script execution capability
- **Data Recovery**: Historical data preservation
- **Documentation**: Comprehensive troubleshooting guides

## Technology Stack Justification

### Core Choices
- **Python 3.13+**: Modern features, strong ecosystem, type hints, performance
- **httpx**: Modern HTTP client with HTTP/2 support, async capability, clean API
- **Direct API Access**: Backend API discovered, eliminating need for browser automation
- **GitHub Actions / Coolify**: Flexible deployment options, cron scheduling
- **Telegram**: Immediate notification, mobile-friendly, reliable Bot API
- **uv**: Fast, modern Python package installer and environment manager

### Architecture Evolution
- **Initial Plan**: Playwright-based browser automation for scraping HTML
- **Current Implementation**: Direct API calls to `backend.premiumkino.de`
- **Rationale**: API access is faster, more reliable, requires less infrastructure (no headless browser)
- **Benefits**: Reduced dependencies, faster execution, simpler deployment, easier testing

### Alternative Considerations
- **Scrapy/Selenium**: Not needed - direct API access available
- **requests**: Rejected in favor of httpx (modern, better features)
- **Kubernetes**: Overkill for current scale requirements
- **Email Notifications**: Less immediate than mobile messaging
- **Serverless Functions**: Viable option but GitHub Actions simpler for weekly cron

## Implementation Roadmap

### Phase 1: Foundation (Current)
- Architecture documentation
- Test suite development
- Core scraper implementation

### Phase 2: Production Readiness
- Container optimization
- Error handling refinement
- Performance tuning

### Phase 3: Deployment
- Coolify integration
- Monitoring setup
- Documentation completion

### Phase 4: Enhancement
- Feature additions based on usage
- Performance optimizations
- Scalability improvements

## Conclusion

This architecture provides a robust, maintainable, and scalable foundation for the Astor Kino Notifier system. The design prioritizes reliability, observability, and operational simplicity while ensuring the system can evolve with changing requirements.

The modular approach allows for independent testing and deployment of components, while the comprehensive error handling and monitoring strategies ensure production-grade reliability.
