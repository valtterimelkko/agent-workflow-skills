# Runware API Reference

Complete API documentation for image generation with Runware.

## Base Configuration

```python
API_URL = "https://api.runware.ai/v1"
API_KEY = os.environ.get("RUNWARE_API_KEY")
```

## Authentication

```python
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}
```

## Model IDs

| Model | Runware ID | Best For | Max Resolution |
|-------|------------|----------|----------------|
| **Nano Banana 2** | `google:4@2` | Icons, heroes, mockups, marketing | 4K (4096×4096) |
| **GPT Image 1.5** | `openai:4@1` | Background removal, transparent PNGs | 1536×1024 |

## Valid Dimensions

### Nano Banana 2 (`google:4@2`)

Supports extensive resolutions up to 4K:

| Resolution | Dimensions | Aspect Ratio |
|------------|------------|--------------|
| 1K | 1024×1024 | 1:1 |
| 1K | 1376×768, 768×1376 | 16:9, 9:16 |
| 2K | 2048×2048 | 1:1 |
| 2K | 2752×1536, 1536×2752 | 16:9, 9:16 |
| 4K | 4096×4096 | 1:1 |
| 4K | 5504×3072, 3072×5504 | 16:9, 9:16 |

Plus: 3:2, 2:3, 4:3, 3:4, 4:5, 5:4, 21:9

### GPT Image 1.5 (`openai:4@1`)

Limited to:

| Width | Height | Aspect Ratio |
|-------|--------|--------------|
| 1024 | 1024 | 1:1 |
| 1536 | 1024 | 3:2 |
| 1024 | 1536 | 2:3 |

## Request Format

### Nano Banana 2 - Basic Generation

```json
{
  "taskType": "imageInference",
  "taskUUID": "uuid-v4-string",
  "model": "google:4@2",
  "positivePrompt": "detailed description here",
  "width": 1024,
  "height": 1024,
  "numberResults": 3,
  "outputType": "URL",
  "outputFormat": "png"
}
```

### Nano Banana 2 - With Style References

```json
{
  "taskType": "imageInference",
  "taskUUID": "uuid-v4-string",
  "model": "google:4@2",
  "positivePrompt": "Create icon matching the style of references",
  "width": 1024,
  "height": 1024,
  "numberResults": 3,
  "outputType": "URL",
  "outputFormat": "png",
  "referenceImages": [
    "style-anchor-uuid",
    "color-reference-uuid"
  ]
}
```

### GPT Image 1.5 - With Transparency

```json
{
  "taskType": "imageInference",
  "taskUUID": "uuid-v4-string",
  "model": "openai:4@1",
  "positivePrompt": "detailed description here",
  "width": 1024,
  "height": 1024,
  "numberResults": 3,
  "outputType": "URL",
  "outputFormat": "png",
  "providerSettings": {
    "openai": {
      "quality": "high",
      "background": "transparent"
    }
  }
}
```

## Parameters

### Required

| Parameter | Type | Description |
|-----------|------|-------------|
| `taskType` | string | `"imageInference"` |
| `taskUUID` | string | Unique UUID v4 |
| `model` | string | `"google:4@2"` or `"openai:4@1"` |
| `positivePrompt` | string | Main generation prompt |

### Output Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `outputType` | string | `"URL"` | `"URL"`, `"base64Data"` |
| `outputFormat` | string | `"png"` | `"png"`, `"jpeg"`, `"webp"` |
| `numberResults` | int | 1 | 1-10 images |
| `referenceImages` | array | [] | UUIDs for style consistency |

### GPT Image 1.5 Provider Settings

| Parameter | Values | Description |
|-----------|--------|-------------|
| `quality` | `"low"`, `"medium"`, `"high"` | Rendering quality |
| `background` | `"transparent"`, `"opaque"` | Background type |
| `input_fidelity` | `"low"`, `"high"` | Preserve input details |

**Transparency:** Set `background: "transparent"` AND `outputFormat: "png"`

## Response Format

**Success:**
```json
{
  "data": [
    {
      "taskType": "imageInference",
      "taskUUID": "uuid-string",
      "imageUUID": "uuid-string",
      "imageURL": "https://im.runware.ai/image/...",
      "cost": 0.0095
    }
  ],
  "errors": []
}
```

**Error:**
```json
{
  "data": [],
  "errors": [
    {
      "code": "invalidWidth",
      "message": "Invalid value for 'width' parameter",
      "parameter": "width"
    }
  ]
}
```

## Error Codes

| Code | Meaning | Solution |
|------|---------|----------|
| `invalidWidth` | Width not valid | Use supported dimensions |
| `invalidHeight` | Height not valid | Use supported dimensions |
| `invalidApiKey` | Auth failed | Check RUNWARE_API_KEY |
| `rateLimit` | Too many requests | Add delays |

## Python Example

```python
import requests
import os
from uuid import uuid4

API_KEY = os.environ["RUNWARE_API_KEY"]
API_URL = "https://api.runware.ai/v1"

def generate_with_style(prompt, style_refs=None):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "taskType": "imageInference",
        "taskUUID": str(uuid4()),
        "model": "google:4@2",
        "positivePrompt": prompt,
        "width": 1024,
        "height": 1024,
        "numberResults": 3,
        "outputType": "URL",
        "outputFormat": "png"
    }
    
    if style_refs:
        payload["referenceImages"] = style_refs
    
    response = requests.post(API_URL, headers=headers, json=[payload], timeout=120)
    return response.json()["data"]
```

## Cost Estimation

### Nano Banana 2
- 1K/2K: ~$0.05-0.07 per image
- 4K: ~$0.13-0.15 per image

### GPT Image 1.5
- Low: ~$0.005-0.01 per image
- Medium: ~$0.01-0.03 per image  
- High: ~$0.02-0.05 per image

## Best Practices

1. **Choose Right Model:**
   - Nano Banana 2: Quality, 4K, text rendering
   - GPT Image 1.5: Transparency, editing

2. **Transparency:**
   - GPT Image 1.5: Native support
   - Nano Banana 2: No native alpha

3. **Style Consistency:**
   - Use reference images
   - Create style anchors
   - Document successful prompts

4. **Performance:**
   - Add 1-second delay between calls
   - Use 120s timeout
   - Download images promptly
