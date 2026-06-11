#!/usr/bin/env python3
"""
Asset Plan Creator - Generate comprehensive UI asset plans based on style guide.

Takes a style guide and asset requirements, then creates a detailed plan
with specifications and prompts for each asset to be generated.
"""

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List


def load_style_guide(path: str) -> Dict:
    """Load style guide from JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_requirements(path: str) -> Dict:
    """Load asset requirements from JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_icon_prompt(asset: Dict, style: Dict) -> str:
    """Create prompt for icon generation."""
    concept = asset.get('concept', 'generic')
    size = asset.get('size', 24)
    
    palette = style.get('color_palette', {})
    primary_color = palette.get('primary', '#0066FF')
    
    patterns = style.get('visual_patterns', {})
    style_summary = style.get('style_summary', 'modern tech aesthetic')
    
    # Determine icon style from overall aesthetic
    if 'minimal' in style_summary.lower() or 'clean' in style_summary.lower():
        icon_style = 'minimalist'
        stroke_desc = 'clean geometric lines'
    else:
        icon_style = 'modern'
        stroke_desc = 'bold confident strokes'
    
    prompt = (
        f"{icon_style.capitalize()} vector icon of {concept}, "
        f"outlined style, {stroke_desc}, "
        f"primary color {primary_color}, "
        f"simple geometric shapes, professional UI design, "
        f"{size}px optimized, clear silhouette, "
        f"recognizable at small sizes, "
        f"transparent background"
    )
    
    return prompt


def create_hero_banner_prompt(asset: Dict, style: Dict) -> str:
    """Create prompt for hero banner generation."""
    concept = asset.get('concept', 'product showcase')
    aspect_ratio = asset.get('aspect_ratio', '16:9')
    text_area = asset.get('text_overlay_area', 'left')
    
    palette = style.get('color_palette', {})
    primary = palette.get('primary', '#0066FF')
    background = palette.get('background', '#0F172A')
    
    style_summary = style.get('style_summary', 'modern tech aesthetic')
    
    # Map aspect ratio to dimensions
    aspect_map = {
        '16:9': '16:9 widescreen',
        '21:9': 'ultra-wide 21:9',
        '4:3': '4:3 standard',
        '1:1': 'square 1:1',
        '9:16': 'vertical 9:16'
    }
    aspect_desc = aspect_map.get(aspect_ratio, f'{aspect_ratio} aspect ratio')
    
    prompt = (
        f"{aspect_desc} hero banner for tech website, "
        f"{concept}, professional commercial photography, "
        f"{style_summary}, "
        f"color palette {primary} and {background}, "
        f"ample negative space on {text_area} for text overlay, "
        f"shallow depth of field, "
        f"modern composition, high-end aesthetic"
    )
    
    return prompt


def create_feature_icon_prompt(asset: Dict, style: Dict) -> str:
    """Create prompt for feature icon/illustration."""
    concept = asset.get('concept', 'feature')
    
    palette = style.get('color_palette', {})
    primary = palette.get('primary', '#0066FF')
    secondary = palette.get('secondary', '#00D9FF')
    accent = palette.get('accent', '#FF6B35')
    
    style_summary = style.get('style_summary', 'modern tech aesthetic')
    
    prompt = (
        f"Flat vector illustration representing {concept}, "
        f"{style_summary}, "
        f"color palette {primary}, {secondary}, {accent}, "
        f"simple geometric shapes, metaphor visual, "
        f"clean composition, professional SaaS aesthetic, "
        f"suitable for feature highlight section, "
        f"white background"
    )
    
    return prompt


def create_background_prompt(asset: Dict, style: Dict) -> str:
    """Create prompt for background generation."""
    bg_type = asset.get('background_type', 'abstract')
    
    palette = style.get('color_palette', {})
    primary = palette.get('primary', '#0066FF')
    background = palette.get('background', '#0F172A')
    surface = palette.get('surface', '#1E293B')
    
    style_summary = style.get('style_summary', 'modern tech aesthetic')
    
    if bg_type == 'gradient':
        prompt = (
            f"Abstract gradient background for website hero section, "
            f"flowing from {background} to {surface}, "
            f"subtle {primary} accent highlights, "
            f"soft organic shapes, modern blur effect, "
            f"{style_summary}, suitable for text overlay, "
            f"no objects, no text"
        )
    elif bg_type == 'texture':
        prompt = (
            f"Subtle textured background, {surface} base color, "
            f"minimal grain texture, {style_summary}, "
            f"soft lighting, elegant and premium feel, "
            f"suitable for text overlay, seamless tileable"
        )
    else:  # abstract
        prompt = (
            f"Abstract background for website, {style_summary}, "
            f"color palette {background}, {surface}, {primary}, "
            f"subtle geometric patterns, soft gradients, "
            f"modern professional design, "
            f"low contrast for text readability"
        )
    
    return prompt


def create_product_mockup_prompt(asset: Dict, style: Dict) -> str:
    """Create prompt for product mockup generation."""
    product = asset.get('concept', 'digital product')
    environment = asset.get('environment', 'modern workspace')
    
    palette = style.get('color_palette', {})
    primary = palette.get('primary', '#0066FF')
    
    style_summary = style.get('style_summary', 'modern tech aesthetic')
    
    prompt = (
        f"Product mockup of {product} in {environment}, "
        f"{style_summary}, "
        f"professional product photography, "
        f"soft directional lighting from upper left, "
        f"realistic shadows and reflections, "
        f"{primary} accent color touches, "
        f"commercial quality, shallow depth of field, "
        f"premium tech aesthetic, photorealistic materials"
    )
    
    return prompt


def create_marketing_material_prompt(asset: Dict, style: Dict) -> str:
    """Create prompt for marketing material generation."""
    material_type = asset.get('material_type', 'social_post')
    concept = asset.get('concept', 'product promotion')
    
    palette = style.get('color_palette', {})
    primary = palette.get('primary', '#0066FF')
    accent = palette.get('accent', '#FF6B35')
    background = palette.get('background', '#0F172A')
    
    style_summary = style.get('style_summary', 'modern tech aesthetic')
    
    # Platform-specific dimensions
    platform_sizes = {
        'instagram_post': '1:1 square',
        'instagram_story': '9:16 vertical',
        'facebook_post': 'landscape',
        'twitter_post': 'landscape 16:9',
        'linkedin_post': 'landscape',
        'pinterest_pin': '2:3 vertical'
    }
    
    size_desc = platform_sizes.get(material_type, 'standard')
    
    prompt = (
        f"{size_desc} marketing {material_type} for {concept}, "
        f"{style_summary}, "
        f"color scheme {primary} and {accent} on {background}, "
        f"professional graphic design, "
        f"clear visual hierarchy, "
        f"modern layout with ample whitespace, "
        f"eye-catching and professional"
    )
    
    return prompt


def determine_model(asset_type: str, requires_transparency: bool) -> str:
    """Determine which model to use based on asset requirements."""
    if requires_transparency:
        return "openai:4@1"  # GPT Image 1.5 for transparency
    
    # All other assets use Nano Banana 2 for better quality
    return "google:4@2"


def determine_dimensions(asset_type: str, asset: Dict) -> Dict:
    """Determine output dimensions based on asset type."""
    dimensions = {
        "icon": {"width": 1024, "height": 1024, "target_size": asset.get('size', 24)},
        "hero_banner": {"width": 1536, "height": 1024, "aspect_ratio": asset.get('aspect_ratio', '16:9')},
        "feature_icon": {"width": 1024, "height": 1024, "target_size": 128},
        "background": {"width": 1920, "height": 1080, "aspect_ratio": "16:9"},
        "product_mockup": {"width": 1536, "height": 1024, "aspect_ratio": "3:2"},
        "marketing_material": {"width": 1024, "height": 1024, "platform": asset.get('material_type', 'generic')}
    }
    
    return dimensions.get(asset_type, {"width": 1024, "height": 1024})


def create_asset_plan(style_guide: Dict, requirements: Dict) -> Dict:
    """Create comprehensive asset plan."""
    assets = []
    
    for req in requirements.get('assets', []):
        asset_type = req.get('type', 'icon')
        asset_id = req.get('name', f'asset_{len(assets)}')
        
        # Generate appropriate prompt
        prompt_creators = {
            'icon': create_icon_prompt,
            'hero_banner': create_hero_banner_prompt,
            'feature_icon': create_feature_icon_prompt,
            'background': create_background_prompt,
            'product_mockup': create_product_mockup_prompt,
            'marketing_material': create_marketing_material_prompt
        }
        
        creator = prompt_creators.get(asset_type, create_icon_prompt)
        prompt = creator(req, style_guide)
        
        # Determine model and dimensions
        requires_transparency = req.get('transparent', asset_type in ['icon', 'feature_icon'])
        model = determine_model(asset_type, requires_transparency)
        dimensions = determine_dimensions(asset_type, req)
        
        # Create specifications
        specifications = {
            "type": asset_type,
            "concept": req.get('concept'),
            "dimensions": dimensions,
            "transparent": requires_transparency,
            "format": "PNG" if requires_transparency else "JPG"
        }
        
        # Add type-specific specs
        if asset_type == 'icon':
            specifications["target_size"] = req.get('size', 24)
            specifications["style"] = "outlined"
        elif asset_type == 'hero_banner':
            specifications["text_overlay_area"] = req.get('text_overlay_area', 'left')
        
        asset_plan = {
            "id": asset_id,
            "name": req.get('name', asset_id).replace('_', ' ').title(),
            "type": asset_type,
            "specifications": specifications,
            "prompt": prompt,
            "model": model,
            "model_name": "GPT Image 1.5" if model == "openai:4@1" else "Nano Banana 2",
            "iterations": req.get('iterations', 3),
            "variations_per_iteration": req.get('variations', 3)
        }
        
        assets.append(asset_plan)
    
    return {
        "style_guide": style_guide,
        "assets": assets,
        "total_assets": len(assets),
        "generation_summary": {
            "nano_banana_2_assets": sum(1 for a in assets if a['model'] == 'google:4@2'),
            "gpt_image_15_assets": sum(1 for a in assets if a['model'] == 'openai:4@1')
        }
    }


def create_default_requirements() -> Dict:
    """Create default asset requirements."""
    return {
        "assets": [
            {
                "type": "icon",
                "name": "dashboard_icon",
                "concept": "analytics dashboard with charts",
                "size": 24,
                "transparent": True
            },
            {
                "type": "icon",
                "name": "settings_icon",
                "concept": "gear or cog for settings",
                "size": 24,
                "transparent": True
            },
            {
                "type": "hero_banner",
                "name": "homepage_hero",
                "concept": "modern workspace with technology",
                "aspect_ratio": "16:9",
                "text_overlay_area": "left"
            },
            {
                "type": "feature_icon",
                "name": "security_feature",
                "concept": "security shield with checkmark",
                "transparent": True
            },
            {
                "type": "product_mockup",
                "name": "app_mockup",
                "concept": "mobile application on smartphone",
                "environment": "modern minimalist desk"
            }
        ]
    }


def main():
    parser = argparse.ArgumentParser(
        description='Create comprehensive UI asset plan from style guide'
    )
    parser.add_argument(
        '--style', '-s',
        required=True,
        help='Path to style guide JSON'
    )
    parser.add_argument(
        '--requirements', '-r',
        help='Path to asset requirements JSON (optional)'
    )
    parser.add_argument(
        '--output', '-o',
        default='asset_plan.json',
        help='Output path for asset plan JSON'
    )
    parser.add_argument(
        '--create-template',
        action='store_true',
        help='Create default requirements template and exit'
    )
    
    args = parser.parse_args()
    
    # Create template mode
    if args.create_template:
        requirements = create_default_requirements()
        template_path = 'asset_requirements_template.json'
        
        with open(template_path, 'w', encoding='utf-8') as f:
            json.dump(requirements, f, indent=2)
        
        print(f"✅ Created requirements template: {template_path}")
        print("\nEdit this file to define your assets, then run:")
        print(f"  python3 scripts/create_asset_plan.py --style style_guide.json --requirements {template_path}")
        return 0
    
    # Load style guide
    if not os.path.exists(args.style):
        print(f"❌ Style guide not found: {args.style}")
        return 1
    
    style_guide = load_style_guide(args.style)
    print(f"\n📋 Loaded style guide: {args.style}")
    print(f"   Style: {style_guide.get('style_summary', 'Unknown')}")
    
    # Load or create requirements
    if args.requirements:
        if not os.path.exists(args.requirements):
            print(f"❌ Requirements file not found: {args.requirements}")
            return 1
        requirements = load_requirements(args.requirements)
        print(f"   Requirements: {args.requirements}")
    else:
        requirements = create_default_requirements()
        print("   Using default requirements (5 sample assets)")
    
    # Create asset plan
    print("\n🎨 Creating asset plan...")
    asset_plan = create_asset_plan(style_guide, requirements)
    
    # Save asset plan
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(asset_plan, f, indent=2)
    
    print(f"\n✅ Asset plan saved to: {output_path}")
    
    # Summary
    print(f"\n📊 Plan Summary:")
    print(f"   Total assets: {asset_plan['total_assets']}")
    print(f"   Nano Banana 2 assets: {asset_plan['generation_summary']['nano_banana_2_assets']}")
    print(f"   GPT Image 1.5 assets: {asset_plan['generation_summary']['gpt_image_15_assets']}")
    
    print(f"\n📦 Asset Types:")
    type_counts = {}
    for asset in asset_plan['assets']:
        t = asset['type']
        type_counts[t] = type_counts.get(t, 0) + 1
    for t, count in type_counts.items():
        print(f"   - {t}: {count}")
    
    print(f"\n💡 Next steps:")
    print(f"   1. Review the asset plan: {output_path}")
    print(f"   2. Adjust prompts as needed")
    print(f"   3. Generate assets:")
    print(f"      python3 scripts/generate_assets.py --plan {output_path}")
    
    return 0


if __name__ == '__main__':
    exit(main())
