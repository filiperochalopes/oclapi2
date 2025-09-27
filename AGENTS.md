# AGENTS.md - Coding Guidelines for OCLAPI2

## Project Structure
```
oclapi2/
├── .github/                    # GitHub configuration
│   └── workflows/             # CI/CD workflows
├── .well-known/               # Well-known URIs for service discovery
├── core/                      # Main application code
│   ├── bundles/              # FHIR Bundle support
│   ├── client_configs/       # Client configuration management
│   ├── code_systems/         # FHIR CodeSystem resources
│   ├── collections/          # Collection management (versioning, references)
│   ├── common/               # Shared utilities and base classes
│   ├── concept_maps/         # FHIR ConceptMap resources
│   ├── concepts/             # Concept management
│   ├── events/               # Event tracking and audit logs
│   ├── fhir/                 # FHIR API endpoints
│   ├── fixtures/             # Initial data fixtures
│   ├── importers/            # Data import utilities
│   ├── indexes/              # Search indexing
│   ├── integration_tests/    # Integration test suite
│   ├── lookup_fixtures/      # Reference data (locales, datatypes)
│   ├── map_projects/         # Mapping project management
│   ├── mappings/             # Concept mappings
│   ├── middlewares/          # Custom Django middlewares
│   ├── operation_outcome/    # FHIR OperationOutcome support
│   ├── orgs/                 # Organization management
│   ├── parameters/           # FHIR Parameters support
│   ├── pins/                 # Resource pinning functionality
│   ├── reports/              # Reporting functionality
│   ├── repos/                # Repository management
│   ├── samples/              # Sample data files
│   ├── services/             # Business logic services
│   │   ├── auth/            # Authentication services
│   │   └── storages/        # Storage backends
│   ├── sources/              # Source management
│   ├── tasks/                # Celery async tasks
│   ├── toggles/              # Feature toggles
│   ├── url_registry/         # URL registry for resources
│   ├── users/                # User management
│   ├── value_sets/           # FHIR ValueSet resources
│   ├── settings.py           # Django settings
│   ├── urls.py               # Main URL configuration
│   ├── celery.py             # Celery configuration
│   └── wsgi.py               # WSGI application
├── tools/                     # Utility scripts
├── docker-compose.yml         # Docker development setup
├── docker-compose.prod.yml    # Production Docker setup
├── Dockerfile                 # Docker image definition
├── requirements.txt           # Python dependencies
├── manage.py                  # Django management script
└── startup.sh                 # Application startup script
```

## Build/Test Commands
- **Run all tests:** `docker exec -it oclapi2-api-1 python manage.py test --keepdb -v3`
- **Run single test:** `docker exec -it oclapi2-api-1 python manage.py test --keepdb -v3 -- core.sources.tests.tests.SourceTest`
- **Run module tests:** `docker exec -it oclapi2-api-1 python manage.py test --keepdb -v3 core.sources`
- **Lint check:** `docker exec -it oclapi2-api-1 pylint -j2 core`
- **Coverage:** `docker exec -it oclapi2-api-1 bash coverage.sh` (min 89% required, target ≥80% for critical modules)
- **DB migrations:** `docker compose run --rm api python manage.py makemigrations`

## Code Quality Principles
- **KISS (Keep It Simple, Stupid):** Write simple, clear code. Avoid over-engineering. Functions should do one thing well.
- **DRY (Don't Repeat Yourself):** Extract common logic into reusable functions/mixins. Use Django's built-in features.
- **YAGNI (You Aren't Gonna Need It):** Don't add functionality until it's needed. Remove dead code and obsolete feature flags.
- **SOLID:** Single responsibility, Open/closed, Liskov substitution, Interface segregation, Dependency inversion.
- **Fail-fast:** Validate inputs early, raise exceptions for invalid states, use Django's validators.

## Code Style & Standards
- **Max line length:** 120 characters
- **Max function length:** 60 lines (refactor longer functions)
- **Imports:** Django imports first, then third-party, then local (organized alphabetically within groups)
- **Type hints:** Use type hints for function parameters and return values where it improves clarity
- **Docstrings:** Required for services/use cases (describe purpose, inputs/outputs, invariants, side-effects)
- **Comments:** Only for business logic/design decisions, not for obvious code
- **Naming:** snake_case for functions/variables, CamelCase for classes, UPPER_CASE for constants
- **No print statements:** Use proper logging (logger.debug, logger.info, logger.error)

## Testing Standards
- **Test coverage:** ≥80% for critical modules (models, views, serializers)
- **Test structure:** Use factory_boy for test data, mock external dependencies, inherit from `OCLTestCase`
- **Test naming:** test_<method>_<condition>_<expected_result> (e.g., test_create_concept_with_invalid_parent_raises_error)
- **Test scope:** Unit tests for business logic, integration tests for API endpoints
- **Assertions:** Use specific assertions (assertEqual, assertRaises) with meaningful error messages

## Django/DRF Best Practices
- **Models:** Inherit from appropriate base classes, use Django's built-in validators, define Meta class properly
- **Serializers:** Use DRF ModelSerializers, define fields explicitly, use SerializerMethodField for computed values
- **Views:** Use ViewSets where appropriate, implement proper permission classes, handle exceptions gracefully
- **Error handling:** Use Django's ValidationError for model validation, DRF's exceptions for API responses
- **Queries:** Use select_related/prefetch_related to avoid N+1 queries, use only() for field selection

## Git Workflow & Commits
- **Branch naming:** feature/<ticket>-<description>, bugfix/<ticket>-<description>, hotfix/<description>
- **Commit messages:** Follow Conventional Commits (feat:, fix:, docs:, style:, refactor:, test:, chore:)
- **PR requirements:** All tests passing, coverage maintained/improved, code reviewed, no linter warnings
- **Commit size:** Keep commits atomic and focused on a single change

## Security & Performance
- **Never commit secrets:** Use environment variables for sensitive data
- **Input validation:** Sanitize all user inputs, use Django's built-in protections
- **Query optimization:** Profile queries, add appropriate indexes, use Django Debug Toolbar in development
- **Caching:** Use Redis for frequently accessed data, implement cache invalidation properly
- **Async tasks:** Use Celery for long-running operations, implement proper retry logic