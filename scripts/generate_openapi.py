"""
Script to generate openapi.yaml from the FastAPI application.
"""

import os
import sys
import yaml
import json
from fastapi.openapi.utils import get_openapi

# Add src to path to allow imports
sys.path.append(os.getcwd())

from main import app

def generate_openapi_yaml():
    """Generates openapi.yaml file."""
    if not app.openapi_schema:
        # Generate the schema if not already generated
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            description=app.description,
            routes=app.routes,
        )
        app.openapi_schema = openapi_schema
    else:
        openapi_schema = app.openapi_schema

    # Write to file
    output_file = "openapi.yaml"
    with open(output_file, "w") as f:
        yaml.dump(openapi_schema, f, sort_keys=False)
    
    print(f"Successfully generated {output_file}")

if __name__ == "__main__":
    generate_openapi_yaml()
