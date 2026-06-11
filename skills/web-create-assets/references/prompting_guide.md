# Professional Prompting Guide for UI Asset Generation

## Prompt Structure Formula

Effective prompts follow this structure:

```
[Image Type] + [Subject] + [Background/Setting] + [Style] + [Technical Specs] + [Constraints]
```

## Six Essential Elements

1. **Subject** - Who/what is the main focus (be specific)
2. **Composition** - Camera angle, framing (close-up, wide shot, low angle)
3. **Action** - What is happening
4. **Setting/Location** - Environment context
5. **Style** - Visual aesthetic (photorealistic, flat vector, 3D render)
6. **Technical Specs** - Quality, format, constraints

## Quality Markers (Use Instead of Generic Terms)

**Instead of:** "beautiful," "amazing," "stunning," "high quality," "8K"

**Use:**
- `film grain` - for cinematic texture
- `textured brushstrokes` - for painterly quality
- `macro detail` - for extreme close-ups
- `professional studio photography` - for commercial polish
- `shallow depth of field` - for photographic realism
- `soft diffuse lighting` - for even, professional illumination

## Asset-Specific Prompting Patterns

### Icons

**Structure:**
```
[Style] vector icon of [subject], [outlined/filled] style, [stroke description], 
[primary color], [geometric description], professional UI design, 
[size]px optimized, [background type]
```

**Example:**
```
Minimalist vector icon of cloud upload, outlined style, clean geometric lines, 
primary color #0066FF, simple geometric shapes, professional UI design, 
24px optimized, transparent background
```

### Hero Banners

**Structure:**
```
[Aspect ratio] hero banner for [industry], [subject] in [setting], 
[lighting condition], ample negative space on [side] for text overlay, 
[style descriptor], [color palette], professional quality, [mood]
```

**Example:**
```
16:9 hero banner for SaaS website, modern workspace with laptop and coffee, 
morning sunlight from side window, ample negative space on left for text overlay, 
clean Scandinavian aesthetic, warm neutral tones, professional commercial 
photography quality, productive and calm mood
```

### Feature Icons

**Structure:**
```
Flat vector illustration representing [concept], [style descriptor], 
[color palette], [shape description], metaphor showing [visual metaphor], 
clean composition, professional aesthetic, [use case]
```

**Example:**
```
Flat vector illustration representing secure cloud storage, modern tech style, 
purple and cyan gradient, simple geometric shapes, metaphor showing a cloud 
with protective shield, clean composition with white background, professional 
SaaS aesthetic, suitable for feature section
```

### Backgrounds

**Structure:**
```
[Type] background for website [section], [color palette], 
[texture/pattern description], [style], professional quality, 
[suitable for use case]
```

**Examples:**

**Gradient:**
```
Abstract gradient background for website hero section, flowing from #0F172A 
to #1E293B with subtle #0066FF highlights, soft organic shapes, modern blur 
effect, professional web design quality, suitable for text overlay
```

**Textured:**
```
Subtle noise texture background, #1E293B base color, minimal grain, 
professional web design, soft lighting, elegant and premium feel, 
suitable for text overlay
```

### Product Mockups

**Structure:**
```
Product mockup of [product] on [surface], [lighting condition] from [direction], 
[material properties], professional product photography, 
[shadow/reflection details], commercial quality, [aesthetic]
```

**Example:**
```
Product mockup of premium wireless earbuds on matte black marble surface, 
soft directional lighting from upper left, metallic accents catching highlights, 
professional studio photography, realistic contact shadows, commercial quality, 
shallow depth of field, premium tech aesthetic
```

### Marketing Materials

**Structure:**
```
[Size] marketing [type] for [concept], [style], [color scheme], 
professional graphic design, [layout characteristics], [mood]
```

**Example:**
```
1:1 square Instagram post for product launch, modern tech aesthetic, 
color scheme #0066FF and #FF6B35 on dark background, professional social media 
design quality, clean layout with ample whitespace, modern and eye-catching
```

## Style Consistency Techniques

### Master Style Anchor Method

1. Create one reference image embodying all desired attributes
2. Document the prompt used to create it
3. Use as primary reference for all subsequent generations
4. Include in multi-reference workflows

### Multi-Reference Workflow (Nano Banana 2)

```json
{
  "referenceImages": [
    "master-style-anchor-uuid",    // Primary style reference
    "color-palette-uuid",          // Color scheme reference  
    "lighting-reference-uuid"      // Lighting style reference
  ]
}
```

### Prompt Locking

Document successful prompts and reuse core style descriptors:

```python
# Master style descriptor
STYLE_CORE = "modern minimalist tech aesthetic, clean geometric forms, professional quality"

# Icon prompt
icon_prompt = f"Minimalist vector icon of {subject}, {STYLE_CORE}, {color}, transparent background"

# Hero prompt  
hero_prompt = f"16:9 hero banner, {subject}, {STYLE_CORE}, {lighting}, ample negative space"
```

## Iterative Refinement Workflow

### 4-Step Process

**Step 1: Foundation (Low/Medium Quality)**
Generate 3-5 variations to establish direction

**Step 2: Refinement (Medium Quality)**
Add specific constraints to promising direction

**Step 3: Detail Polish (High Quality)**
Make targeted edits with explicit preservation instructions

**Step 4: Final Production (High Quality)**
Regenerate with optimized comprehensive prompt

### Edit Prompt Template

```
Change only [specific element] to [new state]. Keep everything else exactly 
the same: [list elements to preserve]. Do not change [specific exclusions].
```

**Example:**
```
Change only the jacket color to forest green. Keep everything else exactly 
the same: the model's face, lighting direction, background composition, and 
overall color grading. Do not change the pants or shoes.
```

## Negative Prompting (Positive Phrasing)

| Instead of | Use |
|------------|-----|
| "No cluttered background" | "Clean, minimal background with negative space" |
| "No unrealistic lighting" | "Natural, realistic lighting with consistent shadows" |
| "No cartoon style" | "Photorealistic, professional photography style" |
| "No watermark" | "Plain background, no text overlays" |

## Model-Specific Best Practices

### Nano Banana 2 (`google:4@2`)

- Keep prompts concise and precise
- Use double quotes for exact text: `"Fresh Roast"`
- Upload references and explicitly state what to copy vs. change
- Leverage 14-reference-image capability for complex scenes
- Supports up to 4K resolution

### GPT Image 1.5 (`openai:4@1`)

- Use natural, conversational language
- Break complex scenes into separate elements
- Leverage multi-turn editing for refinement
- Put exact text in **quotes** for text rendering
- Use `quality: "high"` for final production
- Native transparency support with `background: "transparent"`

## Universal One-Liner Template

```
"[Subject], [medium], [style], [lighting], [framing], [mood], [palette]."
```

**Example:**
```
"Portrait of a barista, film photo, soft rim light, 50mm close-up, 
warm mood, teal-orange palette."
```

## Copy-Paste Templates

### Professional Product Photography
```
"Professional product photo of [product] on [surface], [lighting condition], 
[camera angle], [style descriptor], [color palette], commercial photography 
quality, [additional details]."
```

### UI/Icon Template
```
"Minimalist [subject] icon, flat vector style, [color] on white, 
clean geometric lines, professional UI design, 24px optimized, 
simple and recognizable."
```

### Hero Banner Template
```
"Wide hero banner for [use case], [subject] in [setting], [lighting], 
ample negative space for text on [side], [style], [colors], 
professional web design quality."
```

### Brand Logo Template
```
"Modern logo for [industry] brand, [symbol description], [color scheme], 
[style - flat/minimal/gradient], vector style, clean lines, 
centered composition, scalable design."
```
