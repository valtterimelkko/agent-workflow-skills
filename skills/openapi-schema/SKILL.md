---
name: openapi-schema
description: Create OpenAPI 3.1.0 schema files for OpenAI Custom GPTs Actions. Use when the user needs to (1) Generate OpenAPI schemas for GPT actions/API integrations, (2) Convert API documentation to OpenAPI format, (3) Validate or fix existing OpenAPI schemas for GPT compatibility, (4) Add authentication configurations (API Key, OAuth 2.0), (5) Create schemas for specific HTTP methods (GET, POST, PUT, DELETE), (6) Structure request/response models for GPT consumption.
---

# OpenAPI Schema Creator for OpenAI Actions

Create OpenAPI 3.1.0 schemas that enable Custom GPTs to call external REST APIs via the Actions protocol.

## Quick Start

To create a schema, you need:
1. **API endpoint(s)** - URL, method, parameters
2. **Authentication type** - None, API Key, or OAuth 2.0
3. **Request/response structure** - JSON models

## Core Requirements

- **OpenAPI Version**: Must use `3.1.0` (not 3.0.x or 2.0)
- **File Formats**: YAML (preferred) or JSON - both fully supported
- **Max File Size**: 1 MB
- **Max Endpoints**: 30 per action slot, 10 slots per GPT

## Schema Structure

### Minimal Valid Schema

```yaml
openapi: 3.1.0
info:
  title: My API
  description: What this API does
  version: 1.0.0
servers:
  - url: https://api.example.com
paths:
  /endpoint:
    get:
      operationId: uniqueOperationName
      summary: Brief description
      description: Detailed description for GPT
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                type: object
```

### Critical Elements for GPT Actions

| Element | Purpose | Tips |
|---------|---------|------|
| `operationId` | Unique identifier | Use camelCase, no spaces |
| `description` | GPT decision guidance | Be specific about when to use |
| `summary` | Brief context | Max 300 characters |
| `parameters` | Input collection | Use enums for fixed values |

## Authentication Patterns

### No Authentication
```yaml
# Simply omit security sections
paths:
  /public/data:
    get:
      operationId: getPublicData
      security: []  # Explicitly no auth
```

### API Key
```yaml
components:
  securitySchemes:
    ApiKeyAuth:
      type: apiKey
      in: header  # or query
      name: X-API-Key

security:
  - ApiKeyAuth: []

paths:
  /private/data:
    get:
      operationId: getPrivateData
      security:
        - ApiKeyAuth: []
```

### OAuth 2.0
```yaml
components:
  securitySchemes:
    OAuth2:
      type: oauth2
      flows:
        authorizationCode:
          authorizationUrl: https://auth.example.com/authorize
          tokenUrl: https://auth.example.com/token
          scopes:
            read: Read access
            write: Write access
```

**OAuth Requirements:**
- Must use Authorization Code Grant with PKCE
- Redirect URLs to register: `https://chat.openai.com/aip/{g-YOUR-GPT-ID}/oauth/callback` and `https://chatgpt.com/aip/{g-YOUR-GPT-ID}/oauth/callback`
- TLS 1.2+ required on port 443

## Common Patterns

### GET with Query Parameters
```yaml
paths:
  /search:
    get:
      operationId: searchItems
      parameters:
        - name: query
          in: query
          required: true
          schema:
            type: string
          description: Search term
        - name: limit
          in: query
          schema:
            type: integer
            default: 10
          description: Max results to return
      responses:
        '200':
          description: Search results
```

### POST with JSON Body
```yaml
paths:
  /items:
    post:
      operationId: createItem
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - name
              properties:
                name:
                  type: string
                description:
                  type: string
                tags:
                  type: array
                  items:
                    type: string
      responses:
        '201':
          description: Item created
```

### File Upload
```yaml
paths:
  /upload:
    post:
      operationId: uploadFile
      requestBody:
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                file:
                  type: string
                  format: binary
                description:
                  type: string
      responses:
        '200':
          description: Upload successful
```

### Returning Files to GPT
```yaml
paths:
  /documents/{id}:
    get:
      operationId: getDocument
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Document data
          content:
            application/json:
              schema:
                type: object
                properties:
                  openaiFileResponse:
                    type: array
                    items:
                      type: object
                      properties:
                        name:
                          type: string
                        mime_type:
                          type: string
                        content:
                          type: string
                          format: byte  # Base64-encoded
```

## Best Practices

### 1. Description Writing
Descriptions are **critical** - GPT uses them to decide when to call actions:

```yaml
# Good - specific and actionable
description: Fetches current weather conditions for a given city. Use when the user asks about temperature, precipitation, or weather forecasts.

# Bad - vague
description: Gets weather data
```

### 2. Response Design
Return raw data, NOT natural language:

```yaml
# Good - structured data
{
  "temperature": 72,
  "condition": "sunny",
  "humidity": 45
}

# Bad - pre-formatted text
{
  "message": "The weather is sunny with 72 degrees and 45% humidity"
}
```

### 3. Use Enums for Fixed Values
```yaml
parameters:
  - name: unit
    in: query
    schema:
      type: string
      enum: ["celsius", "fahrenheit", "kelvin"]
    description: Temperature unit
```

### 4. Consequential Actions
Control confirmation behavior with extension:

```yaml
paths:
  /delete-account:
    post:
      operationId: deleteAccount
      x-openai-isConsequential: true  # Always prompts
```

Default behavior:
- GET: `false` (shows "Always allow")
- POST/PUT/DELETE: `true` (always prompts)

## Limitations & Constraints

| Limit | Value |
|-------|-------|
| Description/summary per endpoint | 300 chars |
| Parameter description | 700 chars |
| Endpoints per action slot | 30 |
| Action slots per GPT | 10 |
| OpenAPI file size | 1 MB |
| Request/Response payload | < 100K chars |
| Request timeout | 45 seconds |
| Max files per request | 10 |
| Max file size | 10 MB |
| TLS Version | 1.2+ |
| Port | 443 only |

## Data Types & Formats

OpenAPI 3.1.0 supports these formats:

```yaml
type: string
format: date-time  # ISO 8601
type: string
format: date       # YYYY-MM-DD
type: string
format: email
type: string
format: uri
type: string
format: uuid
type: number
format: float
type: number
format: double
type: integer
format: int32
type: integer
format: int64
```

## Complex Schema Examples

See [references/examples.md](references/examples.md) for complete working examples of:
- Weather API with nested endpoints
- CRUD operations with authentication
- File upload/download
- Pagination patterns
- Error response handling

## Validation Checklist

Before using a schema:
- [ ] Uses `openapi: 3.1.0`
- [ ] All `operationId` values are unique
- [ ] All path parameters have `required: true`
- [ ] Descriptions are specific and actionable
- [ ] Authentication is properly configured
- [ ] Response schemas match actual API responses
- [ ] File size is under 1 MB

## Testing

Test schemas before deployment:
1. Validate syntax with Swagger Editor or similar
2. Test API calls in Postman/Insomnia
3. Use OpenAI's "Actions GPT" to help validate
4. Test each endpoint individually in GPT editor
