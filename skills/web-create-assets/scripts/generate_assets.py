#!/usr/bin/env python3
"""
Asset Generator - Create professional UI assets using Runware API.

Generates assets based on a comprehensive asset plan:
- Uses Nano Banana 2 (google:4@2) for most assets (better quality, 4K, text)
- Uses GPT Image 1.5 (openai:4@1) for background removal/transparency
- Supports iterative refinement
- Validates style consistency
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

import requests

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'shared'))
from credentials import load_credential

# Runware API Configuration
RUNWARE_API_URL = "https://api.runware.ai/v1"
RUNWARE_API_KEY = load_credential("RUNWARE_API_KEY", required=False) or ""

# Model IDs (AIR format)
NANO_BANANA_2_MODEL = "google:4@2"      # Primary model - better quality, 4K, text
GPT_IMAGE_15_MODEL = "openai:4@1"       # For transparency/background removal

# Valid dimensions for each model
VALID_DIMENSIONS_GPT = [
    (1024, 1024),  # 1:1
    (1536, 1024),  # 3:2 landscape
    (1024, 1536),  # 2:3 portrait
]

VALID_DIMENSIONS_NANO = [
    # 1K resolutions
    (1024, 1024),    # 1:1
    (1264, 848),     # 3:2
    (848, 1264),     # 2:3
    (1376, 768),     # 16:9
    (768, 1376),     # 9:16
    # 2K resolutions
    (2048, 2048),    # 1:1
    (2528, 1696),    # 3:2
    (1696, 2528),    # 2:3
    (2752, 1536),    # 16:9
    (1536, 2752),    # 9:16
    # 4K resolutions
    (4096, 4096),    # 1:1
    (5056, 3392),    # 3:2
    (3392, 5056),    # 2:3
    (5504, 3072),    # 16:9
    (3072, 5504),    # 9:16
]


def get_api_headers() -> Dict[str, str]:
    """Get API headers with authentication."""
    if not RUNWARE_API_KEY:
        raise ValueError(
            "RUNWARE_API_KEY not set. Make RUNWARE_API_KEY available in your environment or shell startup file"
        )
    return {
        "Authorization": f"Bearer {RUNWARE_API_KEY}",
        "Content-Type": "application/json",
    }


def find_closest_dimensions(width: int, height: int, model: str = NANO_BANANA_2_MODEL) -> Tuple[int, int]:
    """Find closest valid dimensions for the specified model."""
    target_ratio = width / height
    
    valid_dims = VALID_DIMENSIONS_NANO if model == NANO_BANANA_2_MODEL else VALID_DIMENSIONS_GPT
    
    closest = valid_dims[0]
    closest_diff = abs((closest[0] / closest[1]) - target_ratio)
    
    for w, h in valid_dims:
        ratio = w / h
        diff = abs(ratio - target_ratio)
        if diff < closest_diff:
            closest_diff = diff
            closest = (w, h)
    
    return closest


def generate_image(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    model: str = NANO_BANANA_2_MODEL,
    transparent: bool = False,
    quality: str = "high",
    output_format: str = "png",
    number_of_images: int = 3,
    reference_images: List[str] = None,
) -> List[Dict]:
    """
    Generate images using Runware API.
    
    Args:
        prompt: Image generation prompt
        width: Image width
        height: Image height
        model: Model ID (google:4@2 or openai:4@1)
        transparent: Whether to use transparent background
        quality: "low", "medium", or "high"
        output_format: "png", "jpeg", or "webp"
        number_of_images: Number of variations (1-10)
        reference_images: List of image UUIDs for style consistency
    
    Returns:
        List of result dicts with imageURL, imageUUID, etc.
    """
    task_uuid = str(uuid4())
    
    # Build base payload
    payload = {
        "taskType": "imageInference",
        "taskUUID": task_uuid,
        "model": model,
        "positivePrompt": prompt,
        "width": width,
        "height": height,
        "numberResults": number_of_images,
        "outputType": "URL",
        "outputFormat": output_format,
    }
    
    # Add reference images if provided (for style consistency)
    if reference_images:
        payload["referenceImages"] = reference_images
    
    # Add model-specific settings
    if model == GPT_IMAGE_15_MODEL:
        # GPT Image 1.5 supports native transparency
        payload["providerSettings"] = {
            "openai": {
                "quality": quality,
                "background": "transparent" if transparent else "opaque"
            }
        }
    # Nano Banana 2 doesn't have provider settings for transparency
    
    response = requests.post(
        RUNWARE_API_URL,
        headers=get_api_headers(),
        json=[payload],
        timeout=120
    )
    response.raise_for_status()
    
    data = response.json()
    
    if "errors" in data and data["errors"]:
        raise Exception(f"API Error: {data['errors']}")
    
    if "data" not in data or not data["data"]:
        raise Exception(f"No data in response: {data}")
    
    return data["data"]


def download_image(url: str, filepath: str) -> str:
    """Download image from URL to filepath."""
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    with open(filepath, "wb") as f:
        f.write(response.content)
    
    return filepath


def generate_asset_variations(
    asset_id: str,
    asset_name: str,
    prompt: str,
    width: int,
    height: int,
    model: str,
    transparent: bool,
    output_folder: str,
    max_iterations: int = 3,
    variations_per_iter: int = 3,
    reference_images: List[str] = None,
) -> Dict:
    """
    Generate variations for a single asset with iteration support.
    """
    model_name = "Nano Banana 2" if model == NANO_BANANA_2_MODEL else "GPT Image 1.5"
    
    print(f"\n🎨 Generating: {asset_name} ({asset_id})")
    print(f"   Model: {model_name} ({model})")
    print(f"   Size: {width}x{height}")
    print(f"   Transparent: {transparent}")
    print(f"   Prompt: {prompt[:80]}...")
    
    # Find closest valid dimensions
    gen_width, gen_height = find_closest_dimensions(width, height, model)
    print(f"   Generating at: {gen_width}x{gen_height}")
    
    # Determine output format
    output_format = "png" if transparent else "jpg"
    
    # Create asset folder
    asset_folder = os.path.join(output_folder, asset_id)
    os.makedirs(asset_folder, exist_ok=True)
    
    all_variations = []
    
    for iteration in range(max_iterations):
        print(f"\n   Iteration {iteration + 1}/{max_iterations}")
        
        try:
            results = generate_image(
                prompt=prompt,
                width=gen_width,
                height=gen_height,
                model=model,
                transparent=transparent,
                quality="high",
                output_format=output_format,
                number_of_images=variations_per_iter,
                reference_images=reference_images,
            )
            
            # Download results
            iteration_variations = []
            for i, result in enumerate(results):
                if "imageURL" in result:
                    ext = output_format
                    filepath = os.path.join(
                        asset_folder,
                        f"{asset_id}_iter{iteration + 1}_var{i + 1}.{ext}"
                    )
                    download_image(result["imageURL"], filepath)
                    iteration_variations.append({
                        "path": filepath,
                        "iteration": iteration + 1,
                        "variation": i + 1,
                        "imageUUID": result.get("imageUUID"),
                        "cost": result.get("cost"),
                    })
                    print(f"      ✅ Downloaded: {os.path.basename(filepath)}")
            
            all_variations.extend(iteration_variations)
            
        except Exception as e:
            print(f"      ❌ Error: {e}")
            if iteration < max_iterations - 1:
                print(f"      Retrying...")
                time.sleep(2)
            else:
                print(f"      Failed after {max_iterations} iterations")
                raise
        
        # Small delay between iterations
        if iteration < max_iterations - 1:
            time.sleep(1)
    
    return {
        "asset_id": asset_id,
        "asset_name": asset_name,
        "folder": asset_folder,
        "variations": all_variations,
        "total_generated": len(all_variations),
        "model_used": model,
    }


def mark_best_variation(asset_folder: str, asset_id: str, variation_path: str):
    """Mark the best variation by copying it with _SELECTED_ prefix."""
    ext = Path(variation_path).suffix
    selected_path = os.path.join(asset_folder, f"_SELECTED_{asset_id}{ext}")
    
    # Read and write to create a new copy
    with open(variation_path, 'rb') as src:
        with open(selected_path, 'wb') as dst:
            dst.write(src.read())
    
    print(f"   ⭐ Marked as selected: {os.path.basename(selected_path)}")
    return selected_path


def load_asset_plan(plan_path: str) -> Dict:
    """Load asset plan from JSON."""
    with open(plan_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(
        description='Generate UI assets using Runware API'
    )
    parser.add_argument(
        '--plan', '-p',
        required=True,
        help='Path to asset plan JSON'
    )
    parser.add_argument(
        '--output', '-o',
        default='generated_assets',
        help='Output directory for generated assets'
    )
    parser.add_argument(
        '--asset-id',
        help='Generate only for specific asset ID'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be generated without calling API'
    )
    parser.add_argument(
        '--iterations', '-i',
        type=int,
        default=3,
        help='Max iterations per asset (default: 3)'
    )
    parser.add_argument(
        '--variations', '-v',
        type=int,
        default=3,
        help='Variations per iteration (default: 3)'
    )
    parser.add_argument(
        '--model',
        choices=['nano', 'gpt', 'auto'],
        default='auto',
        help='Model to use: nano (Nano Banana 2), gpt (GPT Image 1.5), or auto (default)'
    )
    parser.add_argument(
        '--with-style-refs',
        action='store_true',
        help='Use style reference images for consistency (if available)'
    )
    
    args = parser.parse_args()
    
    # Load asset plan
    if not os.path.exists(args.plan):
        print(f"❌ Asset plan not found: {args.plan}")
        return 1
    
    asset_plan = load_asset_plan(args.plan)
    print(f"\n📋 Loaded asset plan: {args.plan}")
    print(f"   Total assets: {asset_plan.get('total_assets', 0)}")
    
    # Get assets to generate
    assets_to_generate = asset_plan.get("assets", [])
    
    # Filter by asset ID if specified
    if args.asset_id:
        assets_to_generate = [a for a in assets_to_generate if a.get("id") == args.asset_id]
        if not assets_to_generate:
            print(f"❌ Asset ID not found: {args.asset_id}")
            return 1
        print(f"   Filtered to: {args.asset_id}")
    
    # Map model argument to model ID
    force_model = None
    if args.model == 'nano':
        force_model = NANO_BANANA_2_MODEL
    elif args.model == 'gpt':
        force_model = GPT_IMAGE_15_MODEL
    
    print(f"\n🚀 Generating {len(assets_to_generate)} assets")
    print(f"   Output: {args.output}")
    if force_model:
        model_name = "Nano Banana 2" if force_model == NANO_BANANA_2_MODEL else "GPT Image 1.5"
        print(f"   Forced model: {model_name}")
    else:
        print("   Model: Auto-selected based on asset requirements")
    print(f"   Iterations: {args.iterations}")
    print(f"   Variations per iteration: {args.variations}")
    
    if args.dry_run:
        print("\n📋 DRY RUN - Would generate:")
        for asset in assets_to_generate:
            specs = asset.get('specifications', {})
            print(f"\n   {asset['name']} ({asset['id']}):")
            print(f"      Type: {asset['type']}")
            print(f"      Model: {asset.get('model_name', 'Auto')}")
            print(f"      Dimensions: {specs.get('dimensions', {})}")
            print(f"      Transparent: {specs.get('transparent', False)}")
            print(f"      Prompt: {asset['prompt'][:100]}...")
        return 0
    
    # Check API key
    if not RUNWARE_API_KEY:
        print("\n❌ RUNWARE_API_KEY not set!")
        print("   Set RUNWARE_API_KEY in your environment or shell startup file")
        return 1
    
    # Generate assets
    results = []
    for asset in assets_to_generate:
        try:
            specs = asset.get('specifications', {})
            dims = specs.get('dimensions', {})
            
            # Determine model
            model = force_model if force_model else asset.get('model', NANO_BANANA_2_MODEL)
            
            result = generate_asset_variations(
                asset_id=asset["id"],
                asset_name=asset["name"],
                prompt=asset["prompt"],
                width=dims.get("width", 1024),
                height=dims.get("height", 1024),
                model=model,
                transparent=specs.get("transparent", False),
                output_folder=args.output,
                max_iterations=args.iterations,
                variations_per_iter=args.variations,
            )
            results.append(result)
            
            print(f"\n   Generated {result['total_generated']} variations")
            print(f"   Model used: {result['model_used']}")
            print(f"   Location: {result['folder']}")
            
            # Auto-mark first variation as selected
            if result['variations']:
                mark_best_variation(
                    result['folder'],
                    asset["id"],
                    result['variations'][0]['path']
                )
            
        except Exception as e:
            print(f"\n   ❌ Failed to generate {asset['name']}: {e}")
            results.append({
                "asset_id": asset["id"],
                "asset_name": asset["name"],
                "error": str(e)
            })
        
        # Delay between assets to avoid rate limiting
        time.sleep(1)
    
    # Save results
    results_path = os.path.join(args.output, 'generation_results.json')
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    # Summary
    successful = sum(1 for r in results if 'error' not in r)
    failed = len(results) - successful
    
    print(f"\n✅ Generation complete!")
    print(f"   Successful: {successful}")
    print(f"   Failed: {failed}")
    print(f"   Results saved to: {results_path}")
    print("\nNext steps:")
    print("   1. Review variations in each asset folder")
    print("   2. Rename preferred variations to _SELECTED_<name>.<ext>")
    print("   3. Integrate assets into your project")
    
    return 0


if __name__ == '__main__':
    exit(main())
