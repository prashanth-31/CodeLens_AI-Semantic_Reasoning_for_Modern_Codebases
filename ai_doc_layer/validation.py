# validation.py
"""Input validation utilities for CodeLens AI."""
import re
from pathlib import Path
from typing import Optional, Tuple, Any
import requests


def validate_directory_path(path: str) -> Path:
    """
    Validate that a path exists and is a directory.
    
    Args:
        path: Path string to validate
        
    Returns:
        Path object if valid
        
    Raises:
        ValueError: If path is invalid or not a directory
        FileNotFoundError: If path does not exist
    """
    if not path or not path.strip():
        raise ValueError("Path cannot be empty")
    
    path_obj = Path(path).resolve()
    
    if not path_obj.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")
    
    if not path_obj.is_dir():
        raise ValueError(f"Path is not a directory: {path}")
    
    return path_obj


def validate_file_path(path: str, must_exist: bool = True) -> Path:
    """
    Validate that a path is a valid file path.
    
    Args:
        path: Path string to validate
        must_exist: Whether the file must already exist
        
    Returns:
        Path object if valid
        
    Raises:
        ValueError: If path is invalid
        FileNotFoundError: If must_exist=True and file doesn't exist
    """
    if not path or not path.strip():
        raise ValueError("Path cannot be empty")
    
    path_obj = Path(path).resolve()
    
    if must_exist:
        if not path_obj.exists():
            raise FileNotFoundError(f"File does not exist: {path}")
        
        if not path_obj.is_file():
            raise ValueError(f"Path is not a file: {path}")
    
    return path_obj


def validate_python_file(path: str) -> Path:
    """
    Validate that a path is a Python file.
    
    Args:
        path: Path string to validate
        
    Returns:
        Path object if valid
        
    Raises:
        ValueError: If file is not a Python file
    """
    path_obj = validate_file_path(path, must_exist=True)
    
    if path_obj.suffix != '.py':
        raise ValueError(f"File is not a Python file: {path}")
    
    return path_obj


def validate_model_name(model: str) -> str:
    """
    Validate Ollama model name format.
    
    Args:
        model: Model name to validate
        
    Returns:
        Model name if valid
        
    Raises:
        ValueError: If model name is invalid
    """
    if not model or not model.strip():
        raise ValueError("Model name cannot be empty")
    
    # Basic validation for Ollama model format (e.g., "model:tag" or "model")
    if not re.match(r'^[a-z0-9._-]+(?::[a-z0-9._-]+)?$', model, re.IGNORECASE):
        raise ValueError(f"Invalid model name format: {model}")
    
    return model.strip()


def validate_positive_integer(value: Any, name: str = "value", min_value: int = 1) -> int:
    """
    Validate that a value is a positive integer.
    
    Args:
        value: Value to validate
        name: Name of the parameter for error messages
        min_value: Minimum allowed value (inclusive)
        
    Returns:
        Integer value if valid
        
    Raises:
        ValueError: If value is not a valid positive integer
    """
    try:
        int_value = int(value)
    except (ValueError, TypeError):
        raise ValueError(f"{name} must be an integer, got: {type(value).__name__}")
    
    if int_value < min_value:
        raise ValueError(f"{name} must be >= {min_value}, got: {int_value}")
    
    return int_value


def check_ollama_connection(base_url: str = "http://localhost:11434", timeout: int = 5) -> Tuple[bool, Optional[str]]:
    """
    Check if Ollama service is accessible.
    
    Args:
        base_url: Ollama service URL
        timeout: Connection timeout in seconds
        
    Returns:
        Tuple of (is_connected, error_message)
    """
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=timeout)
        if response.status_code == 200:
            return True, None
        else:
            return False, f"Ollama responded with status {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to Ollama. Make sure it's running: ollama serve"
    except requests.exceptions.Timeout:
        return False, f"Connection to Ollama timed out after {timeout}s"
    except Exception as e:
        return False, f"Unexpected error connecting to Ollama: {e}"


def validate_git_repository(path: Path) -> None:
    """
    Validate that a path is a git repository.
    
    Args:
        path: Path to validate
        
    Raises:
        ValueError: If path is not a git repository
    """
    git_dir = path / ".git"
    if not git_dir.exists():
        raise ValueError(f"Not a git repository: {path}")
