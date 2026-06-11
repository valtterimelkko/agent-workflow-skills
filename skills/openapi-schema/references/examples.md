# OpenAPI Schema Examples for GPT Actions

Complete working examples for common API patterns.

---

## Example 1: Weather API (Simple GET)

```yaml
openapi: 3.1.0
info:
  title: Weather Service API
  description: Provides weather forecasts by location coordinates
  version: 1.0.0
servers:
  - url: https://api.weather.gov
    description: National Weather Service API

paths:
  /points/{latitude},{longitude}:
    get:
      operationId: getPointData
      summary: Get forecast grid endpoints
      description: Converts lat/long coordinates to grid points used by the forecast API. Call this first to get gridId, gridX, and gridY.
      parameters:
        - name: latitude
          in: path
          required: true
          schema:
            type: number
            format: float
            minimum: -90
            maximum: 90
          description: Latitude coordinate
        - name: longitude
          in: path
          required: true
          schema:
            type: number
            format: float
            minimum: -180
            maximum: 180
          description: Longitude coordinate
      responses:
        '200':
          description: Grid point data with forecast URLs
          content:
            application/json:
              schema:
                type: object
                properties:
                  properties:
                    type: object
                    properties:
                      gridId:
                        type: string
                        description: Grid identifier
                      gridX:
                        type: integer
                        description: Grid X coordinate
                      gridY:
                        type: integer
                        description: Grid Y coordinate
                      forecast:
                        type: string
                        format: uri
                        description: URL for forecast data

  /gridpoints/{gridId}/{gridX},{gridY}/forecast:
    get:
      operationId: getGridpointForecast
      summary: Get detailed forecast
      description: Retrieves detailed weather forecast for a specific grid point.
      parameters:
        - name: gridId
          in: path
          required: true
          schema:
            type: string
          description: Grid identifier from getPointData
        - name: gridX
          in: path
          required: true
          schema:
            type: integer
          description: Grid X coordinate
        - name: gridY
          in: path
          required: true
          schema:
            type: integer
          description: Grid Y coordinate
        - name: units
          in: query
          schema:
            type: string
            enum: ["us", "si"]
            default: "us"
          description: Unit system - us (imperial) or si (metric)
      responses:
        '200':
          description: Detailed forecast periods
          content:
            application/json:
              schema:
                type: object
                properties:
                  properties:
                    type: object
                    properties:
                      periods:
                        type: array
                        items:
                          type: object
                          properties:
                            name:
                              type: string
                              description: Period name (e.g., "Tonight")
                            temperature:
                              type: integer
                            temperatureUnit:
                              type: string
                            shortForecast:
                              type: string
                            detailedForecast:
                              type: string
```

---

## Example 2: Database Query API with API Key

```yaml
openapi: 3.1.0
info:
  title: PostgreSQL Query API
  description: Execute SQL queries against PostgreSQL database via secure middleware
  version: 1.0.0
servers:
  - url: https://db-api.example.com/v1

paths:
  /query:
    post:
      operationId: executeQuery
      summary: Execute SQL query
      description: Executes a read-only SQL query against the database. Only SELECT statements are allowed.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - query
              properties:
                query:
                  type: string
                  description: SQL SELECT query
                  example: SELECT * FROM users LIMIT 10
                params:
                  type: array
                  items:
                    type: string
                  description: Query parameters for prepared statements
      responses:
        '200':
          description: Query results
          content:
            application/json:
              schema:
                type: object
                properties:
                  rows:
                    type: array
                    items:
                      type: object
                    description: Query result rows
                  rowCount:
                    type: integer
                    description: Number of rows returned
                  fields:
                    type: array
                    items:
                      type: object
                      properties:
                        name:
                          type: string
                        dataType:
                          type: string
        '400':
          description: Invalid query
          content:
            application/json:
              schema:
                type: object
                properties:
                  error:
                    type: string
                  message:
                    type: string
        '401':
          description: Unauthorized
      security:
        - ApiKey: []

components:
  securitySchemes:
    ApiKey:
      type: apiKey
      in: header
      name: X-API-Key
```

---

## Example 3: CRUD API with Mixed Auth

```yaml
openapi: 3.1.0
info:
  title: Task Management API
  description: Create, read, update, and delete tasks
  version: 1.0.0
servers:
  - url: https://tasks.example.com/api

paths:
  /tasks:
    get:
      operationId: listTasks
      summary: List all tasks
      description: Retrieves a paginated list of tasks for the authenticated user.
      parameters:
        - name: status
          in: query
          schema:
            type: string
            enum: ["pending", "in_progress", "completed", "all"]
            default: "all"
          description: Filter by task status
        - name: page
          in: query
          schema:
            type: integer
            default: 1
            minimum: 1
          description: Page number
        - name: limit
          in: query
          schema:
            type: integer
            default: 20
            maximum: 100
          description: Items per page
      responses:
        '200':
          description: List of tasks
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/Task'
                  pagination:
                    type: object
                    properties:
                      currentPage:
                        type: integer
                      totalPages:
                        type: integer
                      totalItems:
                        type: integer
      security:
        - BearerAuth: []

    post:
      operationId: createTask
      summary: Create a new task
      description: Creates a new task and returns the created object.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - title
              properties:
                title:
                  type: string
                  maxLength: 200
                description:
                  type: string
                  maxLength: 2000
                dueDate:
                  type: string
                  format: date
                priority:
                  type: string
                  enum: ["low", "medium", "high"]
                  default: "medium"
                tags:
                  type: array
                  items:
                    type: string
      responses:
        '201':
          description: Task created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Task'
        '400':
          description: Validation error
      security:
        - BearerAuth: []

  /tasks/{taskId}:
    get:
      operationId: getTask
      summary: Get task by ID
      parameters:
        - name: taskId
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Task details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Task'
        '404':
          description: Task not found
      security:
        - BearerAuth: []

    put:
      operationId: updateTask
      summary: Update task
      description: Updates all fields of a task.
      parameters:
        - name: taskId
          in: path
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TaskInput'
      responses:
        '200':
          description: Task updated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Task'
      security:
        - BearerAuth: []

    patch:
      operationId: patchTask
      summary: Partially update task
      description: Updates only provided fields of a task.
      parameters:
        - name: taskId
          in: path
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/TaskInput'
      responses:
        '200':
          description: Task updated
      security:
        - BearerAuth: []

    delete:
      operationId: deleteTask
      summary: Delete task
      x-openai-isConsequential: true
      parameters:
        - name: taskId
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '204':
          description: Task deleted
        '404':
          description: Task not found
      security:
        - BearerAuth: []

components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

  schemas:
    Task:
      type: object
      properties:
        id:
          type: string
          format: uuid
        title:
          type: string
        description:
          type: string
        status:
          type: string
          enum: ["pending", "in_progress", "completed"]
        priority:
          type: string
          enum: ["low", "medium", "high"]
        dueDate:
          type: string
          format: date
        tags:
          type: array
          items:
            type: string
        createdAt:
          type: string
          format: date-time
        updatedAt:
          type: string
          format: date-time

    TaskInput:
      type: object
      properties:
        title:
          type: string
        description:
          type: string
        status:
          type: string
          enum: ["pending", "in_progress", "completed"]
        priority:
          type: string
          enum: ["low", "medium", "high"]
        dueDate:
          type: string
          format: date
        tags:
          type: array
          items:
            type: string
```

---

## Example 4: File Upload API

```yaml
openapi: 3.1.0
info:
  title: File Storage API
  description: Upload and manage files
  version: 1.0.0
servers:
  - url: https://storage.example.com/v1

paths:
  /upload:
    post:
      operationId: uploadFile
      summary: Upload a file
      description: Uploads a file and returns metadata including the file ID.
      requestBody:
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              required:
                - file
              properties:
                file:
                  type: string
                  format: binary
                  description: File to upload (max 10MB)
                folder:
                  type: string
                  description: Destination folder path
                description:
                  type: string
                  maxLength: 500
                  description: File description
                tags:
                  type: string
                  description: Comma-separated tags
      responses:
        '200':
          description: File uploaded successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  id:
                    type: string
                    format: uuid
                  filename:
                    type: string
                  size:
                    type: integer
                    description: File size in bytes
                  mimeType:
                    type: string
                  url:
                    type: string
                    format: uri
                  uploadedAt:
                    type: string
                    format: date-time
        '400':
          description: Invalid file or too large
        '413':
          description: File exceeds size limit
      security:
        - ApiKey: []

  /files:
    get:
      operationId: listFiles
      summary: List uploaded files
      parameters:
        - name: folder
          in: query
          schema:
            type: string
          description: Filter by folder
        - name: mimeType
          in: query
          schema:
            type: string
          description: Filter by MIME type (e.g., 'image/*')
      responses:
        '200':
          description: List of files
          content:
            application/json:
              schema:
                type: object
                properties:
                  files:
                    type: array
                    items:
                      type: object
                      properties:
                        id:
                          type: string
                        filename:
                          type: string
                        size:
                          type: integer
                        mimeType:
                          type: string
                        uploadedAt:
                          type: string
                          format: date-time
      security:
        - ApiKey: []

components:
  securitySchemes:
    ApiKey:
      type: apiKey
      in: header
      name: X-API-Key
```

---

## Example 5: Returning Files to GPT

```yaml
openapi: 3.1.0
info:
  title: Document Generation API
  description: Generate and retrieve documents
  version: 1.0.0
servers:
  - url: https://docs.example.com/v1

paths:
  /generate:
    post:
      operationId: generateDocument
      summary: Generate a document
      description: Generates a document (PDF, DOCX, etc.) based on provided data. Returns the file in a format GPT can display.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - template
                - data
              properties:
                template:
                  type: string
                  enum: ["report", "invoice", "letter", "resume"]
                  description: Document template to use
                data:
                  type: object
                  description: Data to populate the template
                format:
                  type: string
                  enum: ["pdf", "docx", "txt"]
                  default: "pdf"
                  description: Output file format
      responses:
        '200':
          description: Generated document
          content:
            application/json:
              schema:
                type: object
                properties:
                  openaiFileResponse:
                    type: array
                    description: Files for GPT to display to user
                    items:
                      type: object
                      required:
                        - name
                        - mime_type
                        - content
                      properties:
                        name:
                          type: string
                          description: Filename with extension
                        mime_type:
                          type: string
                          description: MIME type (e.g., application/pdf)
                        content:
                          type: string
                          format: byte
                          description: Base64-encoded file content
        '400':
          description: Invalid template or data
      security:
        - BearerAuth: []

  /documents/{id}:
    get:
      operationId: getDocument
      summary: Retrieve a document
      description: Retrieves a previously generated document by ID.
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Document data with file content
          content:
            application/json:
              schema:
                type: object
                properties:
                  id:
                    type: string
                  name:
                    type: string
                  mimeType:
                    type: string
                  size:
                    type: integer
                  createdAt:
                    type: string
                    format: date-time
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
                          format: byte
        '404':
          description: Document not found
      security:
        - BearerAuth: []

components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
```

---

## Example 6: E-commerce API

```yaml
openapi: 3.1.0
info:
  title: E-commerce API
  description: Product catalog and orders
  version: 1.0.0
servers:
  - url: https://shop.example.com/api/v1

paths:
  /products:
    get:
      operationId: searchProducts
      summary: Search products
      description: Search products by keyword, category, or filter criteria.
      parameters:
        - name: q
          in: query
          schema:
            type: string
          description: Search query
        - name: category
          in: query
          schema:
            type: string
          description: Category slug
        - name: minPrice
          in: query
          schema:
            type: number
            minimum: 0
          description: Minimum price filter
        - name: maxPrice
          in: query
          schema:
            type: number
            minimum: 0
          description: Maximum price filter
        - name: sort
          in: query
          schema:
            type: string
            enum: ["price_asc", "price_desc", "newest", "popular"]
            default: "popular"
          description: Sort order
      responses:
        '200':
          description: Search results
          content:
            application/json:
              schema:
                type: object
                properties:
                  products:
                    type: array
                    items:
                      $ref: '#/components/schemas/Product'
                  total:
                    type: integer
                  filters:
                    type: object
                    properties:
                      categories:
                        type: array
                        items:
                          type: object
                          properties:
                            id:
                              type: string
                            name:
                              type: string
                            count:
                              type: integer
      security: []

  /products/{productId}:
    get:
      operationId: getProduct
      summary: Get product details
      parameters:
        - name: productId
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Product details
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Product'
      security: []

  /cart:
    get:
      operationId: getCart
      summary: Get current cart
      responses:
        '200':
          description: Cart contents
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Cart'
      security:
        - BearerAuth: []

    post:
      operationId: addToCart
      summary: Add item to cart
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - productId
                - quantity
              properties:
                productId:
                  type: string
                quantity:
                  type: integer
                  minimum: 1
                variantId:
                  type: string
                  description: Product variant (size, color, etc.)
      responses:
        '200':
          description: Updated cart
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Cart'
      security:
        - BearerAuth: []

  /orders:
    post:
      operationId: createOrder
      summary: Place an order
      x-openai-isConsequential: true
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - shippingAddress
                - paymentMethod
              properties:
                shippingAddress:
                  $ref: '#/components/schemas/Address'
                paymentMethod:
                  type: string
                  enum: ["card", "paypal", "bank_transfer"]
                couponCode:
                  type: string
                notes:
                  type: string
      responses:
        '201':
          description: Order created
          content:
            application/json:
              schema:
                type: object
                properties:
                  orderId:
                    type: string
                    format: uuid
                  status:
                    type: string
                    enum: ["pending", "confirmed", "processing"]
                  total:
                    type: number
                  estimatedDelivery:
                    type: string
                    format: date
        '400':
          description: Invalid order data
        '402':
          description: Payment required
      security:
        - BearerAuth: []

components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer

  schemas:
    Product:
      type: object
      properties:
        id:
          type: string
        name:
          type: string
        description:
          type: string
        price:
          type: number
        currency:
          type: string
          default: "USD"
        images:
          type: array
          items:
            type: string
            format: uri
        category:
          type: object
          properties:
            id:
              type: string
            name:
              type: string
        variants:
          type: array
          items:
            type: object
            properties:
              id:
                type: string
              name:
                type: string
              options:
                type: array
                items:
                  type: string
        inStock:
          type: boolean
        rating:
          type: number
          minimum: 0
          maximum: 5

    Cart:
      type: object
      properties:
        items:
          type: array
          items:
            type: object
            properties:
              productId:
                type: string
              name:
                type: string
              quantity:
                type: integer
              unitPrice:
                type: number
              totalPrice:
                type: number
              image:
                type: string
        subtotal:
          type: number
        tax:
          type: number
        shipping:
          type: number
        total:
          type: number
        itemCount:
          type: integer

    Address:
      type: object
      required:
        - street
        - city
        - postalCode
        - country
      properties:
        street:
          type: string
        city:
          type: string
        state:
          type: string
        postalCode:
          type: string
        country:
          type: string
          minLength: 2
          maxLength: 2
```

---

## Example 7: OAuth 2.0 Configuration

```yaml
openapi: 3.1.0
info:
  title: Google Workspace API
  description: Access Google Calendar and Gmail
  version: 1.0.0
servers:
  - url: https://www.googleapis.com

paths:
  /calendar/v3/calendars/primary/events:
    get:
      operationId: listCalendarEvents
      summary: List calendar events
      description: Retrieves upcoming events from the user's primary calendar.
      parameters:
        - name: timeMin
          in: query
          schema:
            type: string
            format: date-time
          description: Start time (ISO 8601)
        - name: timeMax
          in: query
          schema:
            type: string
            format: date-time
          description: End time (ISO 8601)
        - name: maxResults
          in: query
          schema:
            type: integer
            default: 10
            maximum: 2500
          description: Maximum events to return
        - name: q
          in: query
          schema:
            type: string
          description: Free text search
      responses:
        '200':
          description: Calendar events
          content:
            application/json:
              schema:
                type: object
                properties:
                  items:
                    type: array
                    items:
                      type: object
                      properties:
                        id:
                          type: string
                        summary:
                          type: string
                        description:
                          type: string
                        start:
                          type: object
                          properties:
                            dateTime:
                              type: string
                              format: date-time
                        end:
                          type: object
                          properties:
                            dateTime:
                              type: string
                              format: date-time
                        location:
                          type: string
      security:
        - GoogleOAuth: ["https://www.googleapis.com/auth/calendar.readonly"]

    post:
      operationId: createCalendarEvent
      summary: Create calendar event
      description: Creates a new event on the user's primary calendar.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - summary
                - start
                - end
              properties:
                summary:
                  type: string
                description:
                  type: string
                location:
                  type: string
                start:
                  type: object
                  required:
                    - dateTime
                  properties:
                    dateTime:
                      type: string
                      format: date-time
                    timeZone:
                      type: string
                      default: "UTC"
                end:
                  type: object
                  required:
                    - dateTime
                  properties:
                    dateTime:
                      type: string
                      format: date-time
                    timeZone:
                      type: string
                attendees:
                  type: array
                  items:
                    type: object
                    properties:
                      email:
                        type: string
                        format: email
      responses:
        '200':
          description: Event created
      security:
        - GoogleOAuth: ["https://www.googleapis.com/auth/calendar.events"]

components:
  securitySchemes:
    GoogleOAuth:
      type: oauth2
      flows:
        authorizationCode:
          authorizationUrl: https://accounts.google.com/o/oauth2/v2/auth
          tokenUrl: https://oauth2.googleapis.com/token
          scopes:
            https://www.googleapis.com/auth/calendar.readonly: Read calendar events
            https://www.googleapis.com/auth/calendar.events: Create calendar events
```

---

## Tips for Using These Examples

1. **Copy and modify** - Start with the example closest to your use case
2. **Update server URLs** - Replace `example.com` with your actual API domain
3. **Add your schemas** - Define request/response models in `components/schemas`
4. **Configure auth** - Choose the right security scheme for your API
5. **Write good descriptions** - These guide GPT's decision-making
