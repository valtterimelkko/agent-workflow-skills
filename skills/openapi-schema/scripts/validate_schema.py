#!/usr/bin/env python3
"""
Validate OpenAPI schema for OpenAI Actions compatibility.

Usage:
    python validate_schema.py <path_to_schema.yaml|json>

Checks:
    - OpenAPI version is 3.1.0
    - All operationIds are unique
    - Path parameters are marked required
    - Required fields are present
    - File size under 1MB
"""

import json
import sys
import yaml
from pathlib import Path


def load_schema(filepath):
    """Load schema from YAML or JSON file."""
    path = Path(filepath)
    content = path.read_text()
    
    if path.suffix in ['.yaml', '.yml']:
        return yaml.safe_load(content)
    elif path.suffix == '.json':
        return json.loads(content)
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}")


def validate_openapi_version(schema):
    """Check OpenAPI version is 3.1.0."""
    version = schema.get('openapi', '')
    if version != '3.1.0':
        return False, f"OpenAPI version must be 3.1.0, got: {version}"
    return True, "✓ OpenAPI version is 3.1.0"


def validate_info(schema):
    """Check required info fields."""
    info = schema.get('info', {})
    errors = []
    
    if not info.get('title'):
        errors.append("Missing info.title")
    if not info.get('version'):
        errors.append("Missing info.version")
    
    if errors:
        return False, "; ".join(errors)
    return True, "✓ Info section valid"


def validate_operation_ids(schema):
    """Check all operationIds are unique."""
    paths = schema.get('paths', {})
    operation_ids = []
    
    for path, methods in paths.items():
        for method, operation in methods.items():
            if method in ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']:
                op_id = operation.get('operationId')
                if op_id:
                    operation_ids.append(op_id)
    
    duplicates = set([x for x in operation_ids if operation_ids.count(x) > 1])
    if duplicates:
        return False, f"Duplicate operationIds found: {duplicates}"
    return True, f"✓ All {len(operation_ids)} operationIds are unique"


def validate_path_parameters(schema):
    """Check path parameters are marked required."""
    paths = schema.get('paths', {})
    errors = []
    
    for path, methods in paths.items():
        # Extract path parameters from URL
        import re
        url_params = set(re.findall(r'\{(\w+)\}', path))
        
        for method, operation in methods.items():
            if method not in ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']:
                continue
                
            params = operation.get('parameters', [])
            param_names = {p['name'] for p in params if p.get('in') == 'path'}
            
            # Check all URL params are defined
            missing = url_params - param_names
            if missing:
                errors.append(f"{path} {method}: Missing path parameter definitions for {missing}")
            
            # Check path params are required
            for param in params:
                if param.get('in') == 'path' and not param.get('required'):
                    errors.append(f"{path} {method}: Path parameter '{param['name']}' must be required: true")
    
    if errors:
        return False, "Path parameter errors:\n  - " + "\n  - ".join(errors)
    return True, "✓ All path parameters valid"


def validate_file_size(filepath):
    """Check file size is under 1MB."""
    size = Path(filepath).stat().st_size
    if size > 1_048_576:  # 1 MB
        return False, f"File size {size} bytes exceeds 1MB limit"
    return True, f"✓ File size {size} bytes (< 1MB)"


def validate_endpoints_count(schema):
    """Check endpoint count is under 30 per action slot."""
    paths = schema.get('paths', {})
    count = 0
    
    for path_methods in paths.values():
        for method in path_methods.keys():
            if method in ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']:
                count += 1
    
    if count > 30:
        return False, f"Too many endpoints: {count} (max 30 per action slot)"
    return True, f"✓ Endpoint count: {count}/30"


def validate_descriptions(schema):
    """Check descriptions are present and reasonable length."""
    paths = schema.get('paths', {})
    warnings = []
    
    for path, methods in paths.items():
        for method, operation in methods.items():
            if method not in ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']:
                continue
                
            desc = operation.get('description', '')
            summary = operation.get('summary', '')
            
            if not desc and not summary:
                warnings.append(f"{path} {method}: Missing both description and summary")
            elif len(desc) > 300:
                warnings.append(f"{path} {method}: Description too long ({len(desc)} chars, max 300)")
            
            # Check parameter descriptions
            for param in operation.get('parameters', []):
                if not param.get('description'):
                    warnings.append(f"{path} {method}: Parameter '{param.get('name')}' missing description")
                elif len(param.get('description', '')) > 700:
                    warnings.append(f"{path} {method}: Param '{param.get('name')}' description too long")
    
    if warnings:
        return True, "⚠ Description warnings:\n  - " + "\n  - ".join(warnings)
    return True, "✓ All descriptions valid"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    try:
        schema = load_schema(filepath)
    except Exception as e:
        print(f"❌ Error loading schema: {e}")
        sys.exit(1)
    
    validators = [
        validate_file_size(filepath),
        validate_openapi_version(schema),
        validate_info(schema),
        validate_operation_ids(schema),
        validate_path_parameters(schema),
        validate_endpoints_count(schema),
        validate_descriptions(schema),
    ]
    
    all_passed = True
    for passed, message in validators:
        status = "✅" if passed else "❌"
        print(f"{status} {message}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("✅ Schema validation passed!")
        sys.exit(0)
    else:
        print("❌ Schema validation failed. Please fix the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
