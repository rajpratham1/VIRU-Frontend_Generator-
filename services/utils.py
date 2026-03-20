import os
from pathlib import Path

def is_vercel() -> bool:
    """
    Check if the application is running in the Vercel (or AWS Lambda) environment.
    """
    # VERCEL="1" is standard for Vercel deployments.
    # VERCEL_REGION is usually present on Vercel runtime.
    # AWS_LAMBDA_FUNCTION_NAME is set in the underlying Lambda environment.
    return (
        os.environ.get("VERCEL") == "1" or 
        os.environ.get("VERCEL_ENV") is not None or
        os.environ.get("VERCEL_REGION") is not None or
        os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None
    )

def get_writable_path(base_dir: Path, relative_path: str) -> Path:
    """
    Resolve a writable path. On Vercel, this redirects to /tmp.
    Locally, it uses the provided relative path from base_dir.
    """
    if is_vercel():
        # Vercel only allows writing to /tmp
        return Path("/tmp") / relative_path
    
    return base_dir / relative_path
