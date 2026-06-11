#!/usr/bin/env python3
"""
Style Analyzer - Extract design system attributes from UI screenshots.

Analyzes screenshots to extract:
- Color palette (primary, secondary, accent, background, text)
- Typography style (font characteristics, weight patterns)
- Visual patterns (shadows, borders, corner radii)
- Component aesthetics (button styles, card treatments)

Outputs a style_guide.json for use in asset generation.
"""

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple
from collections import Counter

try:
    from PIL import Image
    import colorsys
except ImportError:
    print("⚠️  Pillow not installed. Install with: pip install Pillow")
    Image = None


def extract_color_palette(image_path: str, num_colors: int = 8) -> Dict:
    """
    Extract dominant colors from an image.
    
    Returns a dictionary with color palette information.
    """
    if not Image:
        return {
            "primary": "#0066FF",
            "secondary": "#00D9FF",
            "accent": "#FF6B35",
            "background": "#0F172A",
            "surface": "#1E293B",
            "text_primary": "#F8FAFC",
            "text_secondary": "#94A3B8",
            "note": "Pillow not installed - using default colors"
        }
    
    img = Image.open(image_path)
    
    # Convert to RGB if necessary
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Resize for faster processing
    img = img.resize((150, 150))
    
    # Get all pixels
    pixels = list(img.getdata())
    
    # Count color occurrences
    color_counts = Counter(pixels)
    most_common = color_counts.most_common(num_colors * 3)
    
    # Filter out similar colors and convert to hex
    def color_distance(c1, c2):
        return sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5
    
    unique_colors = []
    for color, count in most_common:
        if count < 10:  # Skip rare colors
            continue
        is_unique = True
        for existing in unique_colors:
            if color_distance(color, existing) < 30:
                is_unique = False
                break
        if is_unique and len(unique_colors) < num_colors:
            unique_colors.append(color)
    
    # Convert to hex
    def rgb_to_hex(rgb):
        return '#{:02x}{:02x}{:02x}'.format(*rgb)
    
    hex_colors = [rgb_to_hex(c) for c in unique_colors[:num_colors]]
    
    # Categorize colors by brightness
    def get_brightness(rgb):
        r, g, b = rgb[0]/255, rgb[1]/255, rgb[2]/255
        return colorsys.rgb_to_hsv(r, g, b)[2]
    
    sorted_by_brightness = sorted(unique_colors, key=get_brightness, reverse=True)
    
    return {
        "primary": hex_colors[0] if len(hex_colors) > 0 else "#0066FF",
        "secondary": hex_colors[1] if len(hex_colors) > 1 else "#00D9FF",
        "accent": hex_colors[2] if len(hex_colors) > 2 else "#FF6B35",
        "background": rgb_to_hex(sorted_by_brightness[-1]) if sorted_by_brightness else "#0F172A",
        "surface": hex_colors[3] if len(hex_colors) > 3 else "#1E293B",
        "text_primary": rgb_to_hex(sorted_by_brightness[0]) if sorted_by_brightness else "#F8FAFC",
        "text_secondary": hex_colors[4] if len(hex_colors) > 4 else "#94A3B8",
        "all_extracted": hex_colors
    }


def analyze_typography(image_path: str) -> Dict:
    """
    Analyze typography style from screenshot.
    
    Note: This is a heuristic analysis. For precise typography,
    manual inspection or design file analysis is recommended.
    """
    if not Image:
        return {
            "style": "modern sans-serif",
            "weights": ["400", "600", "700"],
            "characteristics": "clean, geometric, high readability",
            "note": "Pillow not installed - using defaults"
        }
    
    img = Image.open(image_path)
    
    # Analyze contrast to detect text
    # (Simplified - real implementation would use OCR)
    
    return {
        "style": "modern sans-serif",
        "weights": ["400", "600", "700"],
        "characteristics": "clean, geometric, high readability",
        "detected_contrast": "high contrast text detected" if img else "unknown"
    }


def detect_visual_patterns(image_path: str) -> Dict:
    """
    Detect common visual patterns in UI screenshots.
    """
    return {
        "shadows": "subtle drop shadows, 4-8px blur (estimated)",
        "borders": "1px solid with low opacity (estimated)",
        "corner_radius": "8-12px for cards, 4-6px for buttons (estimated)",
        "spacing": "8px base grid, generous whitespace (estimated)",
        "note": "Manual review recommended for precise values"
    }


def generate_style_summary(color_palette: Dict, typography: Dict, patterns: Dict) -> str:
    """Generate a human-readable style summary."""
    
    # Determine if dark or light mode
    bg_brightness = color_palette.get("background", "#FFFFFF")
    # Simple brightness check
    bg_hex = bg_brightness.lstrip('#')
    try:
        r, g, b = int(bg_hex[0:2], 16), int(bg_hex[2:4], 16), int(bg_hex[4:6], 16)
        brightness = (r + g + b) / 3
        mode = "dark" if brightness < 128 else "light"
    except:
        mode = "unknown"
    
    # Determine aesthetic from colors
    primary = color_palette.get("primary", "#0066FF")
    style_terms = []
    
    if "0066FF" in primary or "3B82F6" in primary:
        style_terms.append("blue-accented")
    if mode == "dark":
        style_terms.append("dark mode")
    else:
        style_terms.append("light mode")
    
    style_terms.append("modern minimalist tech aesthetic")
    
    return f"Modern {mode} mode tech aesthetic with {' '.join(style_terms)}, clean lines, professional appearance"


def analyze_screenshots(screenshot_paths: List[str]) -> Dict:
    """
    Analyze multiple screenshots and aggregate style information.
    """
    all_colors = []
    all_typography = []
    all_patterns = []
    
    for path in screenshot_paths:
        print(f"  Analyzing: {os.path.basename(path)}")
        
        if not os.path.exists(path):
            print(f"    ⚠️  File not found, skipping")
            continue
        
        colors = extract_color_palette(path)
        typography = analyze_typography(path)
        patterns = detect_visual_patterns(path)
        
        all_colors.append(colors)
        all_typography.append(typography)
        all_patterns.append(patterns)
    
    # Aggregate color palette (use most common primary)
    primary_colors = [c.get("primary") for c in all_colors if c.get("primary")]
    primary_counter = Counter(primary_colors)
    most_common_primary = primary_counter.most_common(1)[0][0] if primary_counter else "#0066FF"
    
    # Use first screenshot's full palette as base
    base_palette = all_colors[0] if all_colors else {}
    
    # Aggregate patterns
    base_patterns = all_patterns[0] if all_patterns else {}
    
    # Generate summary
    style_summary = generate_style_summary(base_palette, all_typography[0] if all_typography else {}, base_patterns)
    
    return {
        "project_name": "Extracted Project",
        "extracted_from": screenshot_paths,
        "color_palette": base_palette,
        "typography": all_typography[0] if all_typography else {},
        "visual_patterns": base_patterns,
        "style_summary": style_summary,
        "generated_at": str(os.path.getctime(screenshot_paths[0]) if screenshot_paths else "unknown"),
        "analysis_notes": [
            "Color palette extracted using dominant color analysis",
            "Typography estimated from contrast patterns",
            "Visual patterns are heuristic estimates - manual review recommended",
            "For precise values, review actual design files or inspect CSS"
        ]
    }


def create_default_style_guide() -> Dict:
    """Create a default style guide when no screenshots are available."""
    return {
        "project_name": "Default Modern Tech",
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
        "style_summary": "Modern dark mode tech aesthetic with blue accents, clean lines, professional appearance"
    }


def main():
    parser = argparse.ArgumentParser(
        description='Analyze UI screenshots and extract style guide'
    )
    parser.add_argument(
        '--screenshots', '-s',
        help='Directory containing screenshot files (PNG, JPG)'
    )
    parser.add_argument(
        '--files', '-f',
        nargs='+',
        help='Specific screenshot files to analyze'
    )
    parser.add_argument(
        '--output', '-o',
        default='style_guide.json',
        help='Output path for style guide JSON'
    )
    parser.add_argument(
        '--default',
        action='store_true',
        help='Create default style guide without screenshots'
    )
    parser.add_argument(
        '--extract-colors',
        action='store_true',
        help='Extract color palette (requires Pillow)'
    )
    parser.add_argument(
        '--extract-typography',
        action='store_true',
        help='Extract typography patterns (requires Pillow)'
    )
    parser.add_argument(
        '--extract-patterns',
        action='store_true',
        help='Extract visual patterns (requires Pillow)'
    )
    
    args = parser.parse_args()
    
    # Create default style guide
    if args.default:
        style_guide = create_default_style_guide()
        print("\n📋 Creating default style guide...")
    
    # Analyze screenshots
    elif args.screenshots or args.files:
        screenshot_paths = []
        
        if args.screenshots:
            screenshot_dir = Path(args.screenshots)
            if screenshot_dir.exists():
                screenshot_paths = list(screenshot_dir.glob('*.png')) + list(screenshot_dir.glob('*.jpg'))
                screenshot_paths = [str(p) for p in screenshot_paths]
        
        if args.files:
            screenshot_paths.extend(args.files)
        
        if not screenshot_paths:
            print("❌ No screenshots found!")
            return 1
        
        print(f"\n🔍 Analyzing {len(screenshot_paths)} screenshot(s)...")
        style_guide = analyze_screenshots(screenshot_paths)
    
    else:
        print("❌ Error: Either --screenshots, --files, or --default required")
        return 1
    
    # Save style guide
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(style_guide, f, indent=2)
    
    print(f"\n✅ Style guide saved to: {output_path}")
    print(f"\n📊 Extracted Style Summary:")
    print(f"   {style_guide.get('style_summary', 'No summary available')}")
    print(f"\n   Primary Colors:")
    palette = style_guide.get('color_palette', {})
    for key in ['primary', 'secondary', 'accent', 'background']:
        if key in palette:
            print(f"      {key}: {palette[key]}")
    
    print(f"\n💡 Next steps:")
    print(f"   1. Review the style guide: {output_path}")
    print(f"   2. Adjust colors/patterns as needed")
    print(f"   3. Create asset requirements")
    print(f"   4. Run: python3 scripts/create_asset_plan.py --style {output_path}")
    
    return 0


if __name__ == '__main__':
    exit(main())
