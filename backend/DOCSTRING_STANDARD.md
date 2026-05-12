# OpenHack Backend Docstring Standard

Based on the existing codebase patterns in `routes/checks.py`, `routes/judging.py`, and `routes/hackathons.py`.

## Route Handlers and Complex Functions

Every route handler and every non-trivial function (more than 3 lines of logic, raises exceptions, or mutates state) MUST use this exact format:

```python
"""Short description of what the function/endpoint does.

Behavior:
1. First step.
2. Second step.
3. Third step.

Raises: ExceptionName(code) if condition. ExceptionName(code) if condition.
Side Effects: What gets modified/created/deleted/spawned.
Dependencies: module.function, module.Class.
Consumers: GET|POST /api/..., description of caller.
"""
```

Sections:
- **Behavior**: Numbered steps describing the algorithm. Be specific about what gets queried, what gets validated, what gets created/updated/deleted.
- **Raises**: List every exception that can be raised, with HTTP status code if applicable. Write `Raises: None` if no exceptions.
- **Side Effects**: Describe DB inserts/updates/deletes, cache invalidations, background tasks spawned. Write `Side Effects: None (read-only).` if pure.
- **Dependencies**: List key imported functions/classes this function depends on.
- **Consumers**: The endpoint path and a brief description of who calls it.

## Simple Helpers (read-only, no side effects, <5 lines)

Simple helpers that just query and return can use a shorter version, but still substantive:

```python
"""Load the judging session for a hackathon with rubric and criteria eagerly loaded.

Behavior:
1. Query JudgingSession by hackathon_id with selectinload for rubric and criteria.
2. Return 404 if no session exists.

Raises: HTTPException(404) if no judging session configured.
Side Effects: None (read-only).
Dependencies: app.models.JudgingSession, app.models.Rubric, app.models.RubricCriterion.
Consumers: Internal helper used by assignment and scoring routes.
"""
```

## Module-Level Docstrings

```python
"""One-line description of the module's purpose."""
```

## Class-Level Docstrings

```python
"""Description of what the class represents or manages."""
```

## Pydantic Request/Response Models

```python
class CreateTeamRequest(BaseModel):
    """Request body for creating a new team."""
    hackathon_id: str
    name: str
```

## SQLAlchemy Model Classes

```python
class Team(Base):
    """A hackathon team with join code and captain."""
```

## Enum Classes

```python
class UserRole(enum.Enum):
    """Roles available to users in the platform."""
```

## Examples from the Codebase

### Complex route (from checks.py)

```python
async def submit_for_check(...):
    """Submit a Devpost or GitHub URL for automated integrity analysis.

    Behavior:
    1. Extract client IP and enforce rate limiting (10/min).
    2. Validate the URL is a Devpost or GitHub link.
    3. Auto-link to the existing hackathon if none specified.
    4. Create a pending Submission with an anonymous access token.
    5. Persist the submission to the database.
    6. Trigger background analysis via analyze_submission.

    Raises: HTTPException(429) if rate limited, HTTPException(400) if URL invalid.
    Side Effects: Inserts Submission row; spawns background asyncio task.
    Dependencies: app.analyzer.analyze_submission, app.auth.create_anonymous_token, app.scraper.is_devpost_url, app.scraper.is_github_url.
    Consumers: POST /api/check, public submission form.
    """
```

### Simple route (from hackathons.py)

```python
async def list_hackathons(db: AsyncSession = Depends(get_db)):
    """List all hackathons with caching.

    Behavior:
    1. Query all Hackathon records ordered by created_at descending.
    2. Return serialized summaries with participant counts and deadlines.

    Raises: None
    Side Effects: None (read-only, cached).
    Dependencies: app.models.Hackathon, app.cache.cached.
    Consumers: GET /api/hackathons, public hackathon listing.
    """
```

### Helper with time window validation (from judging.py)

```python
def _enforce_time_window(session: JudgingSession):
    """Enforce that the judging session is within its active time window.

    Behavior:
    1. Get current UTC time.
    2. Normalize session start and end times to UTC.
    3. Raise 403 if judging has not opened yet (pending and now < start).
    4. Raise 403 if judging window has closed (status closed or now > end).

    Raises: HTTPException(403) if outside the active judging window.
    Side Effects: None (pure validation).
    Dependencies: app.models.JudgingSession, app.models.JudgingSessionStatus.
    Consumers: Internal helper used by assignment opening, scoring, and detail routes.
    """
```

## Rules

1. Every module gets a docstring at line 1.
2. Every class gets a docstring.
3. Every function gets a docstring.
4. `__repr__` methods are skipped.
5. Trivial Pydantic Field declarations with `description=` inline don't need separate docstrings.
6. Type info is NOT repeated in docstrings (type hints already present).
7. The Behavior section is required for any function with >3 lines of logic.
8. The description line must be substantive — NOT just `"""Foo."""` or `"""Do foo."""`.
