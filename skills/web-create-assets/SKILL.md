---
name: web-create-assets
description: "Create net-new UI assets that match an existing web application's design system, including icons, hero art, feature graphics, mockups, and branded visuals. Use when the project needs additional visual assets that fit the current product style. Do not use this for replacing all existing site imagery at scale, or for generating favicons/Open Graph images; prefer web-replace-assets or web-asset-generator for those."
---

# Web Create Assets

Create professional UI assets that perfectly match your existing web application's design system.

## Quick Start

```bash
# 1. Capture screenshots of your existing UI (optional - uses webapp-testing skill first)
# 2. Analyze screenshots and extract style
python3 scripts/analyze_style.py --screenshots ./screenshots --output style_guide.json

# 3. Create UI asset plan
python3 scripts/create_asset_plan.py --style style_guide.json --requirements requirements.json --output asset_plan.json

# 4. Generate assets
python3 scripts/generate_assets.py --plan asset_plan.json --output ./new_assets
```

## Workflow Overview

```
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ 1. ANALYZE       │ →  │ 2. PLAN          │ →  │ 3. GENERATE      │
│ Extract style    │    │ Define assets    │    │ Create matching  │
│ from screenshots │    │ with specs       │    │ professional     │
│                  │    │                  │    │ assets           │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

## Phase 1: Style Analysis

### Extract Style from Screenshots

Analyze existing UI screenshots to extract:
- **Color Palette**: Primary, secondary, accent, background, text colors
- **Typography Style**: Font characteristics, weight preferences, sizing patterns
- **Visual Patterns**: Shadows, borders, corner radii, spacing
- **Component Aesthetics**: Button styles, card treatments, input fields

```bash
python3 scripts/analyze_style.py \
  --screenshots ./screenshots \
  --output style_guide.json \
  --extract-colors \
  --extract-typography \
  --extract-patterns
```

### Style Guide Output Format

```json
{
  "project_name": "MyApp",
  "extracted_from": ["screenshot1.png", "screenshot2.png"],
  "color_palette": {
    "primary": "#0066FF",
    "secondary": "#00D9FF",
    "accent": "#FF6B35",
    "background": "#0F172A",
    "surface": "#1E293B",
    "text_primary": "#F8FAFC",
    "text_secondary": "#94A3B8"
  },
  "typography": {
    "style": "modern sans-serif",
    "weights": ["400", "600", "700"],
    "characteristics": "clean, geometric, high readability"
  },
  "visual_patterns": {
    "shadows": "subtle drop shadows, 4-8px blur",
    "borders": "1px solid with low opacity",
    "corner_radius": "8-12px for cards, 4-6px for buttons",
    "spacing": "8px base grid, generous whitespace"
  },
  "style_summary": "Modern minimalist tech aesthetic with dark mode, blue primary accent"
}
```

## Phase 2: Asset Planning

### Create Comprehensive UI Asset Plan

Define what assets to create with specifications:

```bash
python3 scripts/create_asset_plan.py \
  --style style_guide.json \
  --requirements asset_requirements.json \
  --output asset_plan.json
```

### Asset Requirements Input

```json
{
  "assets": [
    {
      "type": "icon",
      "name": "dashboard_icon",
      "concept": "Analytics dashboard",
      "size": 24,
      "transparent": true
    },
    {
      "type": "hero_banner",
      "name": "homepage_hero",
      "concept": "Productivity workspace",
      "aspect_ratio": "16:9",
      "text_overlay_area": "left"
    },
    {
      "type": "product_mockup",
      "name": "app_mockup",
      "concept": "Mobile app on iPhone",
      "environment": "modern desk setup"
    }
  ]
}
```

### Asset Plan Output

```json
{
  "style_guide": { /* reference to style */ },
  "assets": [
    {
      "id": "dashboard_icon",
      "type": "icon",
      "name": "Dashboard Analytics Icon",
      "specifications": {
        "size": "24x24px",
        "format": "SVG/PNG",
        "style": "outlined, 1.5px stroke",
        "colors": ["#0066FF"]
      },
      "prompt": "Minimalist vector icon of analytics dashboard with bar chart...",
      "model": "google:4@2",
      "transparent": true
    }
  ]
}
```

## Phase 3: Asset Generation

### Runware Model Configuration

| Model | Runware ID | Best For | Transparency |
|-------|------------|----------|--------------|
| **Nano Banana 2** | `google:4@2` | Icons, heroes, mockups, marketing | ❌ No native support |
| **GPT Image 1.5** | `openai:4@1` | Background removal, transparent PNGs | ✅ Native support |

### Generate Assets

```bash
python3 scripts/generate_assets.py \
  --plan asset_plan.json \
  --output ./generated_assets \
  --iterations 3
```

### Model Auto-Selection

The script automatically selects the appropriate model:
- **Requires transparency** → GPT Image 1.5 (`openai:4@1`)
- **All other assets** → Nano Banana 2 (`google:4@2`)

Force specific model:
```bash
python3 scripts/generate_assets.py --plan asset_plan.json --model nano
python3 scripts/generate_assets.py --plan asset_plan.json --model gpt
```

## Asset Type Specifications

### 1. Icons (UI Iconography)

**Size Standards:**
| Size | Use Case |
|------|----------|
| 16px | Dense layouts, inline text |
| 24px | Standard interface (default) |
| 32px | Touch targets, high-emphasis |
| 48px | Display purposes |

**Specifications:**
- Style: Outlined or filled (consistent across set)
- Stroke weight: 1.5-2px
- Corner radius: 2px for rounded elements
- Format: SVG (preferred) or PNG with transparency
- Grid: 24x24px base with 2px padding

**Prompt Template:**
```
Minimalist vector icon of [subject], [outlined/filled] style, 
[stroke weight] stroke, [primary color], clean geometric shapes, 
professional UI design, 24px optimized, simple and recognizable, 
[transparent/white] background
```

### 2. Hero Banners

**Dimension Standards:**
| Breakpoint | Dimensions | Aspect Ratio |
|------------|------------|--------------|
| Desktop | 1920×1080px | 16:9 |
| High-Res | 2560×1440px | 16:9 |
| Mobile | 1080×1920px | 9:16 |

**Specifications:**
- Composition: Rule of thirds, text safe zone (center 60%)
- Lighting: Professional, consistent direction
- Negative space: Ample room for text overlay
- Format: JPG (photographic) or PNG (with graphics)

**Prompt Template:**
```
[Aspect ratio] hero banner for [industry], [subject] in [setting], 
[lighting condition], ample negative space on [side] for text overlay, 
[style descriptor], [color palette from brand], professional commercial 
photography quality, shallow depth of field
```

### 3. Feature Icons

**Specifications:**
- Size: 48-128px (larger than UI icons)
- Style: Illustrative, storytelling
- Detail: Medium-high (more than UI icons)
- Metaphor: Universal, immediately recognizable

**Prompt Template:**
```
Flat vector illustration representing [concept], [style descriptor], 
[color palette], simple geometric shapes, metaphor showing [visual metaphor], 
clean composition with white background, professional tech aesthetic
```

### 4. Backgrounds

**Types:**
- **Solid/Gradient**: CSS-first approach
- **Textured**: Seamless patterns, subtle grain
- **Photographic**: Abstract, defocused scenes

**Specifications:**
- Seamless tiling for patterns (power-of-2 dimensions)
- Low contrast for text readability
- Format: JPG for photos, PNG for transparent elements
- Performance: Target <200KB for full-screen

**Prompt Template:**
```
[Abstract/textured/gradient] background for website, [color palette], 
[texture type], [subtle/dramatic] visual interest, professional web design 
quality, suitable for text overlay, seamless tileable pattern
```

### 5. Product Mockups

**Types:**
- **Device**: Phone, laptop, tablet mockups
- **Packaging**: Boxes, bottles, bags
- **Apparel**: Clothing, accessories
- **Lifestyle**: Products in real environments

**Specifications:**
- Lighting: Consistent direction, natural or studio
- Shadows: Realistic contact shadows
- Reflections: Environmental on glossy surfaces
- Resolution: 2K-4K for detail

**Prompt Template:**
```
Product mockup of [product] on [surface], [lighting condition] from [direction], 
[material properties], professional product photography, realistic shadows 
and reflections, commercial quality, shallow depth of field, premium aesthetic
```

### 6. Marketing Materials

**Social Media Dimensions:**
| Platform | Post Size | Story Size |
|----------|-----------|------------|
| Instagram | 1080×1080px (1:1) | 1080×1920px (9:16) |
| Facebook | 1200×630px | 1080×1920px |
| Twitter/X | 1280×720px (16:9) | N/A |
| LinkedIn | 1200×627px | N/A |
| Pinterest | 1000×1500px (2:3) | N/A |

**Specifications:**
- Text: Within safe zones, hierarchical
- Contrast: WCAG AA compliant (4.5:1)
- Branding: Consistent colors, fonts, logo placement
- Format: JPG for photos, PNG for graphics with text

**Multi-Image Fusion for Product Placement:**
```bash
# Place product in real environment
python3 scripts/generate_assets.py \
  --fusion-mode \
  --product-image product.png \
  --environment-image office.jpg \
  --output marketing_scene.png
```

## Professional Prompting Techniques

### Six Essential Prompt Elements

1. **Subject**: Who/what is the main focus
2. **Composition**: Camera angle, framing
3. **Action**: What is happening
4. **Setting/Location**: Environment context
5. **Style**: Visual aesthetic
6. **Technical Specs**: Quality, format, constraints

### Quality Markers (Use Instead of "8K/Ultra")

**Photography:**
- `professional studio photography`
- `cinematic composition`
- `shallow depth of field`
- `film grain`
- `natural lighting`

**Design:**
- `flat vector illustration`
- `geometric precision`
- `limited color palette`
- `clean typography`
- `minimalist design`

**3D/Rendering:**
- `physically based rendering (PBR)`
- `ray-traced reflections`
- `realistic materials`
- `studio lighting setup`

### Style Consistency Techniques

**1. Master Style Anchor:**
Create one reference image that embodies all desired attributes, then use it as primary reference for all subsequent generations.

**2. Multi-Reference Workflow (Nano Banana 2):**
```json
{
  "referenceImages": [
    "master-style-anchor-uuid",    // Primary style reference
    "color-palette-uuid",          // Color scheme reference
    "lighting-reference-uuid"      // Lighting style reference
  ]
}
```

**3. Prompt Locking:**
Document successful prompts and reuse core style descriptors across all assets.

## Iterative Refinement Workflow

### 4-Step Process

**Step 1: Foundation**
Generate 3-5 variations at medium quality to establish direction

**Step 2: Refinement**
Add specific constraints to promising direction

**Step 3: Detail Polish**
Make targeted edits with explicit preservation instructions

**Step 4: Final Production**
Generate at high quality with optimized comprehensive prompt

### Edit Prompt Template

```
Change only [specific element] to [new state]. Keep everything else exactly 
the same: [list elements to preserve]. Do not change [specific exclusions].
```

## API Configuration

Requires `RUNWARE_API_KEY` environment variable:

```bash
export RUNWARE_API_KEY="your-runware-api-key"
```

### Background Removal

```bash
python3 scripts/generate_assets.py --remove-bg <image-uuid>
```

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `analyze_style.py` | Extract style from UI screenshots |
| `create_asset_plan.py` | Create comprehensive asset plan |
| `generate_assets.py` | Generate assets with Runware API |
| `style_validator.py` | Verify asset consistency |

## References

- **runware_api.md** - Complete Runware API documentation
- **prompting_guide.md** - Professional prompting techniques
- **style_extraction.md** - Style analysis methodology
- **asset_specifications.md** - Detailed asset type specs
