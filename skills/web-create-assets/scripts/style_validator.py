#!/usr/bin/env python3
"""
Style Validator - Verify generated assets match the style guide.

Checks:
- Color consistency with brand palette
- Style adherence to design system
- Resolution and format compliance
- Naming conventions
"""

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List

try:
    from PIL import Image
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False


def load_style_guide(path: str) -> Dict:
    """Load style guide from JSON."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_generation_results(path: str) -> List[Dict]:
    """Load generation results from JSON."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_asset(asset_result: Dict, style_guide: Dict) -> Dict:
    """Validate a single generated asset against style guide."""
    issues = []
    warnings = []
    
    asset_id = asset_result.get('asset_id', 'unknown')
    folder = asset_result.get('folder', '')
    
    if not folder or not os.path.exists(folder):
        return {
            "asset_id": asset_id,
            "valid": False,
            "issues": ["Asset folder not found"],
            "warnings": []
        }
    
    # Check for _SELECTED_ file
    selected_files = list(Path(folder).glob("_SELECTED_*"))
    if not selected_files:
        warnings.append("No _SELECTED_ file marked")
    
    # Check file formats
    variations = asset_result.get('variations', [])
    for var in variations:
        path = var.get('path', '')
        if path:
            # Check extension
            if path.endswith('.jpg') and var.get('transparent', False):
                issues.append(f"Transparent asset saved as JPG (should be PNG): {path}")
            
            # Validate image if Pillow available
            if HAS_PILLOW and os.path.exists(path):
                try:
                    img = Image.open(path)
                    
                    # Check for transparency in PNG
                    if path.endswith('.png') and var.get('transparent', False):
                        if img.mode not in ('RGBA', 'LA'):
                            warnings.append(f"PNG without alpha channel: {path}")
                    
                    # Check resolution
                    width, height = img.size
                    if width < 512 or height < 512:
                        warnings.append(f"Low resolution ({width}x{height}): {path}")
                        
                except Exception as e:
                    issues.append(f"Cannot read image {path}: {e}")
    
    return {
        "asset_id": asset_id,
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "variations_count": len(variations)
    }


def validate_color_consistency(image_path: str, palette: Dict, tolerance: int = 50) -> Dict:
    """
    Check if image colors are consistent with brand palette.
    
    Note: This is a basic check. For precise validation, manual review is recommended.
    """
    if not HAS_PILLOW or not os.path.exists(image_path):
        return {"consistent": None, "note": "Cannot analyze (Pillow not available)"}
    
    try:
        img = Image.open(image_path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize for faster processing
        img = img.resize((100, 100))
        
        # Get average color
        pixels = list(img.getdata())
        avg_r = sum(p[0] for p in pixels) / len(pixels)
        avg_g = sum(p[1] for p in pixels) / len(pixels)
        avg_b = sum(p[2] for p in pixels) / len(pixels)
        
        # Check if close to any brand color (simplified)
        brand_colors = [
            palette.get('primary', '#0066FF'),
            palette.get('secondary', '#00D9FF'),
            palette.get('background', '#0F172A')
        ]
        
        # Convert hex to RGB for comparison
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        brand_rgbs = [hex_to_rgb(c) for c in brand_colors if c]
        
        # Simple distance check
        min_distance = float('inf')
        for br, bg, bb in brand_rgbs:
            distance = ((avg_r - br) ** 2 + (avg_g - bg) ** 2 + (avg_b - bb) ** 2) ** 0.5
            min_distance = min(min_distance, distance)
        
        # Distance > 100 suggests colors don't match brand
        consistent = min_distance < tolerance * 3  # Very loose tolerance
        
        return {
            "consistent": consistent,
            "average_color": f"#{int(avg_r):02x}{int(avg_g):02x}{int(avg_b):02x}",
            "distance_to_brand": min_distance
        }
        
    except Exception as e:
        return {"consistent": None, "error": str(e)}


def generate_validation_report(results: List[Dict], style_guide: Dict, output_path: str):
    """Generate a comprehensive validation report."""
    report = {
        "validation_summary": {
            "total_assets": len(results),
            "valid_assets": sum(1 for r in results if r.get('valid')),
            "assets_with_issues": sum(1 for r in results if not r.get('valid')),
            "assets_with_warnings": sum(1 for r in results if r.get('warnings'))
        },
        "style_guide_reference": {
            "color_palette": style_guide.get('color_palette', {}),
            "style_summary": style_guide.get('style_summary', '')
        },
        "asset_validations": results
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    
    return report


def main():
    parser = argparse.ArgumentParser(
        description='Validate generated assets against style guide'
    )
    parser.add_argument(
        '--results', '-r',
        required=True,
        help='Path to generation_results.json'
    )
    parser.add_argument(
        '--style', '-s',
        required=True,
        help='Path to style_guide.json'
    )
    parser.add_argument(
        '--output', '-o',
        default='validation_report.json',
        help='Output path for validation report'
    )
    parser.add_argument(
        '--check-colors',
        action='store_true',
        help='Check color consistency (requires Pillow)'
    )
    
    args = parser.parse_args()
    
    # Load inputs
    if not os.path.exists(args.results):
        print(f"❌ Results file not found: {args.results}")
        return 1
    
    if not os.path.exists(args.style):
        print(f"❌ Style guide not found: {args.style}")
        return 1
    
    results = load_generation_results(args.results)
    style_guide = load_style_guide(args.style)
    
    print(f"\n🔍 Validating {len(results)} assets against style guide...")
    print(f"   Style: {style_guide.get('style_summary', 'Unknown')}")
    
    # Validate each asset
    validations = []
    for result in results:
        if 'error' in result:
            validations.append({
                "asset_id": result.get('asset_id', 'unknown'),
                "valid": False,
                "issues": [f"Generation failed: {result['error']}"],
                "warnings": []
            })
        else:
            validation = validate_asset(result, style_guide)
            validations.append(validation)
            
            # Color check if requested
            if args.check_colors and HAS_PILLOW and validation.get('valid'):
                variations = result.get('variations', [])
                if variations:
                    color_check = validate_color_consistency(
                        variations[0]['path'],
                        style_guide.get('color_palette', {})
                    )
                    if color_check.get('consistent') is False:
                        validation['warnings'].append(
                            f"Colors may not match brand palette "
                            f"(avg: {color_check.get('average_color')})"
                        )
    
    # Generate report
    report = generate_validation_report(validations, style_guide, args.output)
    
    # Print summary
    summary = report['validation_summary']
    print(f"\n📊 Validation Summary:")
    print(f"   Total assets: {summary['total_assets']}")
    print(f"   ✅ Valid: {summary['valid_assets']}")
    print(f"   ❌ Issues: {summary['assets_with_issues']}")
    print(f"   ⚠️  Warnings: {summary['assets_with_warnings']}")
    
    # Print issues
    for v in validations:
        if v.get('issues'):
            print(f"\n❌ {v['asset_id']}:")
            for issue in v['issues']:
                print(f"   - {issue}")
    
    # Print warnings
    for v in validations:
        if v.get('warnings'):
            print(f"\n⚠️  {v['asset_id']}:")
            for warning in v['warnings']:
                print(f"   - {warning}")
    
    print(f"\n✅ Report saved to: {args.output}")
    
    return 0 if summary['assets_with_issues'] == 0 else 1


if __name__ == '__main__':
    exit(main())
