# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

SmartQueue is a Django REST Framework backend for intelligent queue management tailored for Senegal. The project follows a modular app architecture with business domains clearly separated.

### Core Architecture Principles
- **Business-oriented apps**: Apps are organized around business domains rather than technical layers
- **Model separation**: Each app uses separate model files in `models/` subdirectories
- **Unified APIs**: Related functionality is grouped under unified API endpoints
- **Senegal-specific features**: Built-in support for Senegalese phone numbers, languages (French/Wolof), regions, and mobile payment providers

### Recent Restructuring
The project underwent a major restructuring that consolidated related apps:
- `organizations` + `services` → `apps/business/`
- `queues` + `tickets` → `apps/queue_management/`

This creates more cohesive business domains while maintaining model separation.

## App Structure

### Core Applications
- **`apps/core/`**: Base models, middleware, utilities, and shared components
- **`apps/accounts/`**: Custom user model with Senegalese phone validation and multilingual support
- **`apps/business/`**: Organizations (businesses, banks, hospitals) and their services
- **`apps/queue_management/`**: Queue management system with tickets and status tracking
- **`apps/locations/`**: Intelligent geolocation with Senegal-specific data
- **`apps/appointments/`**: Appointment scheduling system
- **`apps/notifications/`**: Multi-channel notifications (SMS, email, push)
- **`apps/payments/`**: Mobile money integration (Wave, Orange Money, Free Money)
- **`apps/analytics/`**: Metrics and reporting system

### Model Architecture
Each major app uses the pattern:
```
app_name/
├── models/
│   ├── __init__.py     # Centralized imports
│   ├── model1.py       # Individual model files
│   └── model2.py
├── serializers/        # DRF serializers (may also be split)
├── views.py           # API ViewSets
├── urls.py            # URL routing
└── admin.py           # Django admin configuration
```

### Base Model Classes
All models inherit from `apps.core.models.BaseSmartQueueModel` which provides:
- Automatic timestamps (`TimestampedModel`)
- UUID fields for security (`UUIDModel`) 
- Audit trail tracking (`AuditModel`)
- Soft delete functionality (`ActiveModel`)

### Senegal-Specific Features
- **Phone validation**: `+221XXXXXXXXX` format enforced
- **Regions**: All 14 Senegalese regions supported
- **Languages**: French (primary), Wolof, English
- **Timezone**: `Africa/Dakar`
- **Payment providers**: Wave, Orange Money, Free Money APIs configured

## Development Commands

### Environment Setup
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Database Operations
```bash
# Create and apply migrations
python manage.py makemigrations
python manage.py migrate

# Create test data
python create_test_data.py
python create_test_user.py

# Database shell
python manage.py dbshell
```

### Server Operations
```bash
# Development server (default port 8000)
python manage.py runserver

# With custom port
python manage.py runserver 8001

# Show all URLs
python manage.py show_urls
```

### Testing
```bash
# Run tests
python manage.py test

# Test specific app
python manage.py test apps.business

# Test with pytest (configured in requirements.txt)
pytest

# Test with coverage
coverage run manage.py test
coverage report

# Test SMS service
python test_sms.py
```

### API Documentation
```bash
# Generate API schema
python manage.py spectacular --color --file schema.yml

# Access interactive documentation at:
# http://localhost:8000/api/docs/
```

### Utilities
```bash
# Django shell with models loaded
python manage.py shell

# Check for issues
python manage.py check

# Collect static files
python manage.py collectstatic
```

## Settings Configuration

The project uses a hierarchical settings structure:
- `config/settings/base.py`: Common settings for all environments
- `config/settings/development.py`: Development-specific settings
- Main `config/settings.py`: Simple fallback configuration

### Environment Variables
Create `.env` file in project root for local development:
```
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
```

### Current Configuration
- **Database**: SQLite for development, PostgreSQL configured for production
- **Authentication**: JWT tokens with refresh token rotation
- **API Documentation**: Spectacular (Swagger/OpenAPI)
- **Cache**: Local memory for development, Redis configured for production
- **File Storage**: Local file system with media served at `/media/`

## API Endpoints

### Business APIs
- `GET /api/business/organizations/` - List organizations
- `GET /api/business/services/` - List services  
- Authentication required for mutations

### Queue Management APIs  
- `GET /api/queue-management/queues/` - List queues (auth required)
- `GET /api/queue-management/tickets/` - List tickets (auth required)

### Documentation
- `GET /api/docs/` - Interactive Swagger documentation
- `GET /api/schema/` - OpenAPI schema

## Common Patterns

### Model Relationships
- Organizations have many Services
- Services have many Queues  
- Queues have many Tickets
- Users can have many Tickets
- Most models use soft delete (`is_active` field)

### API Authentication
- JWT tokens required for authenticated endpoints
- Token format: `Authorization: Bearer <token>`
- Tokens expire after 2 hours with 7-day refresh tokens

### Phone Number Handling
Always validate Senegalese phone numbers with the regex: `^\+221[0-9]{9}$`

### SMS Configuration
SmartQueue supports multiple SMS providers for Senegal:
- **Orange Sénégal** (Primary): Official Orange SMS API with OAuth 2.0
- **SMS.to** (Fallback): International gateway supporting Senegal
- **eSMS Africa** (Alternative): Africa-focused SMS provider

#### SMS Provider Setup
1. Copy `.env.example` to `.env`
2. Add your API keys:
   ```
   ORANGE_SMS_CLIENT_ID=your_client_id
   ORANGE_SMS_CLIENT_SECRET=your_client_secret
   SMS_TO_API_KEY=your_sms_to_key
   ESMS_AFRICA_API_KEY=your_esms_key
   ```
3. Test with: `python test_sms.py`

#### SMS Usage
```python
from apps.notifications.sms_service import sms_service

# Send SMS
result = sms_service.send_sms('+221781234567', 'Your message')

# Send OTP
result = sms_service.send_otp('+221781234567', '123456')

# Check provider status
status = sms_service.get_provider_status()
```

### Error Handling  
- Use DRF's standard error responses
- Activity logging is automatically handled by middleware
- Soft deletes preferred over hard deletes

## Troubleshooting

### Common Issues
- **ImportError for Django**: Ensure virtual environment is activated
- **Migration conflicts**: May occur after recent restructuring; resolve by reviewing migration dependencies
- **Missing static files**: Run `python manage.py collectstatic`
- **Database locked**: SQLite database may lock during concurrent operations

### Import Paths After Restructuring
If encountering import errors, update references:
- `apps.organizations.models.Organization` → `apps.business.models.Organization`
- `apps.services.models.Service` → `apps.business.models.Service`  
- `apps.queues.models.Queue` → `apps.queue_management.models.Queue`
- `apps.tickets.models.Ticket` → `apps.queue_management.models.Ticket`