---
name: socialmedia-optimization
description: "Implement and validate Open Graph, Twitter Card, and social preview metadata for websites. Use when the task is about preview cards, meta tags, social sharing behaviour, or fixing broken previews. Do not use this for generating the image assets themselves unless paired with web-asset-generator."
---

# Social Media Optimization Skill

Guide for implementing social media sharing optimization including Open Graph Protocol, Twitter Cards, image dimensions, and validation tools.

## Quick Reference

### Essential Meta Tags (Minimum Required)

```html
<!-- Open Graph -->
<meta property="og:title" content="Compelling Headline (60-90 chars)">
<meta property="og:type" content="article">
<meta property="og:image" content="https://yoursite.com/og-image.jpg">
<meta property="og:url" content="https://yoursite.com/page">

<!-- Twitter -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Compelling Headline">
<meta name="twitter:description" content="Description under 200 chars">
<meta name="twitter:image" content="https://yoursite.com/og-image.jpg">
```

### Image Dimensions by Platform

| Platform | Size | Aspect Ratio | File Max |
|----------|------|--------------|----------|
| **Universal** | 1200 × 630 px | 1.91:1 | < 1 MB |
| Facebook | 1200 × 630 px | 1.91:1 | 8 MB |
| LinkedIn | 1200 × 627 px | 1.91:1 | 8 MB |
| Twitter/X | 1200 × 628 px | 1.91:1 | 5 MB |
| Pinterest | 1000 × 1500 px | 2:3 | 20 MB |

**Absolute minimum:** 200 × 200 px (below this, no image displays)

## Complete Implementation Template

```html
<!-- Essential Meta -->
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Page Title</title>
<meta name="description" content="SEO description">

<!-- Open Graph / Facebook / LinkedIn -->
<meta property="og:type" content="article">
<meta property="og:url" content="https://yoursite.com/page">
<meta property="og:title" content="Compelling Social Headline">
<meta property="og:description" content="Enticing description under 200 chars">
<meta property="og:image" content="https://yoursite.com/og-image-1200x630.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:site_name" content="Your Brand">
<meta property="og:locale" content="en_US">

<!-- Twitter / X -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:url" content="https://yoursite.com/page">
<meta name="twitter:title" content="Compelling Social Headline">
<meta name="twitter:description" content="Enticing description under 200 chars">
<meta name="twitter:image" content="https://yoursite.com/og-image.jpg">
<meta name="twitter:image:alt" content="Descriptive alt text">
<meta name="twitter:site" content="@YourHandle">

<!-- Analytics (optional) -->
<meta property="fb:app_id" content="your_app_id">
```

## Tag Reference

### Open Graph Required Tags

| Tag | Purpose | Example |
|-----|---------|---------|
| `og:title` | Headline in preview | "10 Ways to Improve SEO" |
| `og:type` | Content type | `article`, `website`, `video` |
| `og:image` | Preview image URL | Absolute URL required |
| `og:url` | Canonical URL | `https://example.com/page` |

### Open Graph Recommended Tags

| Tag | Purpose | Best Practice |
|-----|---------|---------------|
| `og:description` | Summary text | Under 200 characters |
| `og:site_name` | Brand name | Consistent across pages |
| `og:locale` | Language/region | `en_US`, `de_DE` |
| `og:image:width` | Image width | Include for immediate display |
| `og:image:height` | Image height | Include for immediate display |

### Twitter Card Tags

| Tag | Purpose | Values |
|-----|---------|--------|
| `twitter:card` | Card type | `summary`, `summary_large_image` |
| `twitter:title` | Card title | Max 70 chars |
| `twitter:description` | Card description | Max 200 chars |
| `twitter:image` | Image URL | Min 300×157 px |
| `twitter:image:alt` | Alt text | Accessibility |
| `twitter:site` | Site handle | `@BrandHandle` |

**Card Types:**
- `summary` — Small square image + text
- `summary_large_image` — Large featured image (best engagement)
- `app` — Mobile app promotion
- `player` — Video/audio embed

## Image Best Practices

### Design Guidelines

1. **Use 1.91:1 aspect ratio** — Fits most platforms without cropping
2. **Center important content** — Edges may be cropped on mobile
3. **Minimum 1200 px width** — High resolution for Retina displays
4. **Keep file size under 1 MB** — Faster loading
5. **High contrast** — Ensure readability on mobile
6. **Include branding** — Logo visible but not dominant

### Common Mistakes to Avoid

| Mistake | Problem | Solution |
|---------|---------|----------|
| Relative image URLs | Image won't display | Use absolute URLs (`https://...`) |
| Image too small | Tiny/no thumbnail | Minimum 600 × 315 px |
| Wrong aspect ratio | Awkward cropping | Stick to 1.91:1 |
| File too large | Slow/timeout | Compress to < 1 MB |
| Missing `og:type` | Platform confusion | Always include type |

## Character Limits

| Element | Recommended | Maximum | Notes |
|---------|-------------|---------|-------|
| Title | 55-60 chars | 95 chars | Facebook truncates at ~88 |
| Description | 150-160 chars | 300 chars | Keep under 200 for safety |
| Twitter title | 70 chars | — | Concise works best |

## Testing & Validation Tools

Always test implementation before deploying:

| Tool | Platform | URL |
|------|----------|-----|
| Facebook Sharing Debugger | Facebook | `developers.facebook.com/tools/debug/` |
| LinkedIn Post Inspector | LinkedIn | `linkedin.com/post-inspector/` |
| Twitter Card Validator | Twitter/X | `cards-dev.twitter.com/validator` |
| OpenGraph.xyz | Universal | `opengraph.xyz` |
| Check Yo Meta | Universal | `checkyometa.com` |

**Important:** After updating tags, use these tools to force a fresh scrape. Social platforms cache aggressively.

## Platform-Specific Notes

### Facebook
- Supports images up to 8 MB
- Caches images aggressively—use debugger to refresh
- Include `og:image:width` and `og:image:height` for immediate display
- First share without these dimensions may not show image immediately

### LinkedIn
- Caches even more aggressively than Facebook
- Same 1.91:1 ratio preferred
- Minimum width: 200 px

### Twitter/X
- Falls back to OG tags if Twitter Cards absent
- Implement both for optimal control
- `summary_large_image` cards perform best

### Pinterest
- **Vertical images win:** 2:3 aspect ratio
- Uses only `og:image` from OG tags
- Minimum 600 px width recommended

### WhatsApp / Messaging Apps
- Uses OG tags for previews
- Smaller preview cards—test cropping

## Dynamic Generation

For CMS-driven sites, generate tags dynamically:

```html
<meta property="og:title" content="{{ post.title }}">
<meta property="og:description" content="{{ post.excerpt|truncate(160) }}">
<meta property="og:image" content="{{ post.featured_image.url }}">
<meta property="og:type" content="article">
<meta property="article:published_time" content="{{ post.published_at }}">
```

## Implementation Checklist

- [ ] Add essential OG tags (`title`, `type`, `image`, `url`)
- [ ] Add Twitter Card tags (`card`, `title`, `description`, `image`)
- [ ] Create 1200 × 630 px image
- [ ] Use absolute URLs for images
- [ ] Test with Facebook Sharing Debugger
- [ ] Test with LinkedIn Post Inspector
- [ ] Test with Twitter Card Validator
- [ ] Clear cache and re-test after changes
- [ ] Verify mobile preview appearance

## Business Impact

Studies show significant benefits from proper social optimization:

- Posts with images: **150% more engagement**
- Facebook posts with images: **100% more engagement**, **114% more impressions**
- Proper OG implementation: **78-250% increase** in social traffic
- Optimized previews: **2-3x higher click-through rates**
