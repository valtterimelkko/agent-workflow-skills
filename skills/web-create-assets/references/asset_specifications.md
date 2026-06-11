# Asset Type Specifications

Professional specifications for each asset type.

## 1. Icons (UI Iconography)

### Size Standards

| Size | Use Case | Format |
|------|----------|--------|
| 16px | Dense layouts, inline text | SVG |
| 24px | Standard interface (default) | SVG |
| 32px | Touch targets, high-emphasis | SVG/PNG |
| 48px | Display purposes | PNG |
| 64px | Large displays, onboarding | PNG |

### Grid Systems

**Material Design Grid:**
- Base: 24dp × 24dp
- Live area: 20dp × 20dp (2dp padding)
- Keyline shapes:
  - Square: 18dp × 18dp
  - Circle: 20dp diameter
  - Vertical rectangle: 20dp × 16dp
  - Horizontal rectangle: 16dp × 20dp

**Apple HIG:**
- Uses superellipse (squircle)
- 15-20% corner curvature
- Optical center alignment

### Visual Specifications

| Attribute | Specification |
|-----------|---------------|
| Stroke weight | 1.5-2px |
| Corner radius | 2px (for rounded elements) |
| Color | Single color or brand palette |
| Background | Transparent |
| Accessibility | WCAG AA 3:1 contrast |

### Filled vs Outlined

- **Filled:** Active states, high-emphasis (recognized faster)
- **Outlined:** Inactive states, secondary actions (reduces clutter)

## 2. Hero Banners

### Dimension Standards

| Breakpoint | Dimensions | Aspect Ratio | Use Case |
|------------|------------|--------------|----------|
| Desktop | 1920×1080px | 16:9 | Standard desktop |
| High-Res | 2560×1440px | 16:9 | Retina displays |
| Mobile | 1080×1920px | 9:16 | Mobile hero |
| Tablet | 1080×1350px | 4:5 | Tablet/portrait |

### Composition Rules

- **Rule of Thirds:** Place key elements at intersection points
- **Text Safe Zone:** Center 60% for text/CTAs
- **Focal Point:** Center or golden ratio position
- **Visual Hierarchy:** Oversized fonts + minimal content

### Technical Specifications

| Attribute | Specification |
|-----------|---------------|
| Format | JPG (photographic), PNG (graphics) |
| Color space | sRGB |
| Resolution | 72 DPI (web) |
| File size | Target <500KB |
| Text overlay | Ensure 4.5:1 contrast ratio |

## 3. Feature Icons

### Differentiation from UI Icons

| Aspect | UI Icons | Feature Icons |
|--------|----------|---------------|
| Size | 16-32px | 48-128px |
| Style | Minimal, functional | Illustrative, storytelling |
| Detail | Low | Medium-high |
| Purpose | Navigation/actions | Value proposition |

### Specifications

| Attribute | Specification |
|-----------|---------------|
| Size range | 48-128px |
| Style | Consistent with brand illustration style |
| Metaphor | Universal, immediately recognizable |
| Background | White or transparent |
| Format | SVG preferred, PNG fallback |

## 4. Backgrounds

### Types

| Type | Use Case | Implementation |
|------|----------|----------------|
| Solid/Gradient | Simple, modern | CSS preferred |
| Textured | Depth, realism | Image asset |
| Photographic | Rich, immersive | Image asset |
| Pattern | Brand consistency | Tileable image |

### Specifications

| Attribute | Specification |
|-----------|---------------|
| Seamless tiling | Power-of-2 dimensions (256×256, 512×512) |
| Contrast | Low for text readability |
| Format | WebP (photos), PNG (transparency) |
| File size | Target <200KB for full-screen |
| Responsive | Consider dark/light variants |

### Gradient Best Practices

- Use CSS for simple gradients (no HTTP request)
- Ensure text contrast in both modes
- Test with actual content overlay
- Consider animation potential

## 5. Product Mockups

### Common Types

| Type | Key Considerations |
|------|-------------------|
| **Device** | Precise bezels, screen reflections, latest specs |
| **Packaging** | Dieline accuracy, material textures, print standards |
| **Apparel** | Fabric draping, 3D folding, fit visualization |
| **Lifestyle** | Environmental context, natural lighting |

### Specifications

| Attribute | Specification |
|-----------|---------------|
| Lighting | Consistent direction, natural or studio |
| Shadows | Realistic contact shadows |
| Reflections | Environmental on glossy surfaces |
| Resolution | 2K-4K for detail |
| Format | PNG (transparency), JPG (photographic) |

### Realism Factors

- **Lighting:** Top-left most natural; single light direction
- **Shadows:** Consistent direction, use Multiply/Overlay blending
- **Materials:** Accurate texture representation
- **Reflections:** Simulate ambient light for glass/screen

## 6. Marketing Materials

### Social Media Dimensions

| Platform | Post | Story/Reel |
|----------|------|------------|
| **Instagram** | 1080×1080px (1:1) | 1080×1920px (9:16) |
| **Facebook** | 1200×630px | 1080×1920px |
| **Twitter/X** | 1280×720px (16:9) | N/A |
| **LinkedIn** | 1200×627px | N/A |
| **Pinterest** | 1000×1500px (2:3) | N/A |

### Specifications

| Attribute | Specification |
|-----------|---------------|
| Text | Within safe zones (avoid edges) |
| Hierarchy | Headline > Subhead > CTA |
| Fonts | Brand fonts consistently |
| Contrast | WCAG AA 4.5:1 minimum |
| Accessibility | Avoid text in images when possible |

### Print vs Digital

| Aspect | Print | Digital |
|--------|-------|---------|
| Resolution | 300 DPI | 72 DPI |
| Color mode | CMYK | RGB |
| Bleed | 3mm standard | N/A |
| File format | PDF, TIFF | JPG, PNG, WebP |

## Multi-Image Fusion for Marketing

### Product Placement Scenarios

**Product on Desk:**
- Reference: Product + desk surface + lighting
- Prompt: Natural placement, contact shadows, environmental reflections

**Product in Hand:**
- Reference: Product + hand pose + environment
- Prompt: Natural grip, skin texture, lifestyle context

**Product in Environment:**
- Reference: Product + scene + lighting
- Prompt: Scale appropriate, environmental interaction, lifestyle aesthetic

### Quality Checklist

- [ ] Lighting direction consistent
- [ ] Shadows match light source
- [ ] Scale proportional to environment
- [ ] Reflections realistic
- [ ] Contact shadows present
- [ ] Color temperature harmony

## Format Selection Guide

| Asset Type | Primary | Fallback | Notes |
|------------|---------|----------|-------|
| Icons | SVG | PNG | Scale infinitely |
| Hero banners | WebP | JPG | Modern browsers |
| Backgrounds | CSS/Gradient | WebP | Performance |
| Mockups | PNG | JPG | Transparency needs |
| Marketing | PNG | JPG | Text quality |

## Naming Conventions

```
[asset_type]_[purpose]_[variant].[ext]

Examples:
- icon_dashboard_24px.svg
- hero_homepage_desktop.jpg
- mockup_app_iphone.png
- feature_security_outline.svg
```
