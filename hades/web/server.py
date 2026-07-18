"""FastAPI server for HADES web interface"""

import os
import sys
import json
import subprocess
import hashlib
import secrets
import jwt
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, validator, constr
from PIL import Image
import io
from rich.console import Console
from rich.panel import Panel
from rich import box

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from hades.templates.manager import (
    list_templates,
    read_template,
    create_template,
    update_template,
    delete_template,
    get_template_dir,
)
from hades.web.database import (
    init_database,
    hash_password,
    verify_password,
    create_user,
    get_user_by_email,
    update_user_password,
    update_user_email,
    update_username as db_update_username,
    get_username_changes_count,
    get_username_changes,
    update_profile_image,
    create_reset_token,
    get_reset_token,
    delete_reset_token,
    cleanup_expired_tokens,
    migrate_from_json,
)

from hades.config_loader import get_hades_version

app = FastAPI(
    title="HADES Web Interface",
    description="Web-based interface for HADES Security Testing Framework",
    version=get_hades_version()
)

# CORS middleware
origins_env = os.getenv("HADES_ALLOWED_ORIGINS", "*")
if origins_env == "*":
    allowed_origins = ["*"]
else:
    allowed_origins = [o.strip() for o in origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True if origins_env != "*" else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache-Control middleware to prevent browser caching of API endpoints and SPA entrypoint
@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.startswith("/api") or not path.startswith("/assets"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Define frontend path for later use
frontend_path = Path(__file__).parent.parent.parent / "frontend" / "dist"
static_path = frontend_path / "static"
assets_path = frontend_path / "assets"

# Authentication configuration
SECRET_KEY = os.getenv("HADES_SECRET_KEY")
if not SECRET_KEY:
    secret_key_file = Path(__file__).parent.parent.parent / "config" / "secret_key.txt"
    if secret_key_file.exists():
        try:
            SECRET_KEY = secret_key_file.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    if not SECRET_KEY:
        SECRET_KEY = secrets.token_hex(32)
        try:
            secret_key_file.parent.mkdir(exist_ok=True, parents=True)
            secret_key_file.write_text(SECRET_KEY, encoding="utf-8")
        except Exception:
            pass

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
PROFILE_IMAGES_DIR = Path(__file__).parent.parent.parent / "config" / "profile_images"

# Security configuration
ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_IMAGE_DIMENSION = 2000  # pixels

# Security
security = HTTPBearer()

# Global console for UI
console = Console()

# Ensure config directory exists
config_dir = Path(__file__).parent.parent.parent / "config"
config_dir.mkdir(exist_ok=True)
PROFILE_IMAGES_DIR.mkdir(exist_ok=True)

# ── System Diagnostics ───────────────────────────────────────────────────────
def get_boot_diagnostics() -> tuple[Panel, bool]:
    """Perform system boot checks and return diagnostic panel"""
    boot_results = []
    
    # 1. Initialize Database
    db_status = "[bold green]OK[/bold green]"
    try:
        init_database()
    except Exception as e:
        db_status = f"[bold red]FAIL({e})[/bold red]"
    
    boot_results.append(f"• [cyan]DATABASE   :[/cyan] {db_status}")
    
    # 2. Check Migration
    try:
        migrated_users, migrated_tokens = migrate_from_json()
        if migrated_users > 0 or migrated_tokens > 0:
            boot_results.append(f"• [cyan]MIGRATION  :[/cyan] [bold cyan]DONE[/bold cyan]")
        else:
            boot_results.append("• [cyan]MIGRATION  :[/cyan] [dim]SKIP[/dim]")
    except Exception:
        boot_results.append("• [cyan]MIGRATION  :[/cyan] [bold yellow]WARN[/bold yellow]")
    
    # 3. Clean up expired tokens
    cleanup_expired_tokens()
    
    # 4. Check Frontend
    frontend_exists = frontend_path.exists() and frontend_path.is_dir()
    if frontend_exists:
        boot_results.append(f"• [cyan]FRONTEND   :[/cyan] [bold green]OK[/bold green]")
    else:
        boot_results.append(f"• [cyan]FRONTEND   :[/cyan] [bold yellow]MISS[/bold yellow]")
        
    boot_panel = Panel(
        "\n".join(boot_results),
        title="[bold blue]SYSTEM ROOT[/bold blue]",
        title_align="left",
        border_style="blue" if frontend_exists else "yellow",
        box=box.DOUBLE_EDGE,
        padding=(1, 2),
        expand=False
    )
    
    return boot_panel, frontend_exists

# Silent boot check on import
_, frontend_exists = get_boot_diagnostics()

# Mount static files FIRST (before routes) - FastAPI evaluates mounts before routes
try:
    # Mount assets folder (Vite puts JS/CSS here)
    if assets_path.exists() and assets_path.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")
        # console.print(f"✓ Assets mounted from: {assets_path}")
    
    # Mount static folder if it exists
    if static_path.exists() and static_path.is_dir():
        app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
        # console.print(f"✓ Static files mounted from: {static_path}")
except Exception as e:
    # If mounting fails, continue without static files
    print(f"Warning: Could not mount static files: {e}")


# ============================================================================
# Pydantic Models
# ============================================================================

class TemplateCreate(BaseModel):
    name: str
    content: str


class TemplateUpdate(BaseModel):
    content: str


class APIConfig(BaseModel):
    provider_key: str
    api_key: str


class ScanRequest(BaseModel):
    targets: List[str]
    instruction: Optional[str] = None
    template: Optional[str] = None
    run_name: Optional[str] = None
    non_interactive: bool = False


class DockerStatus(BaseModel):
    docker_installed: bool
    docker_running: bool
    docker_image_available: bool
    docker_image_name: str
    error: Optional[str] = None


# Authentication Models
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr


class ResetPassword(BaseModel):
    token: str
    new_password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]


class UpdateUsernameRequest(BaseModel):
    new_username: constr(min_length=3, max_length=50, strip_whitespace=True)
    
    @validator('new_username')
    def validate_username(cls, v):
        # Prevent XSS, SQLi, RCE, SSTI
        dangerous_patterns = [
            r'[<>"\']',  # XSS
            r'[;\\]',  # Command injection
            r'\{.*%',  # SSTI
            r'`.*`',  # Command execution
            r'\$\(',  # Command substitution
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, v):
                raise ValueError('Username contains invalid characters')
        return v.strip()


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: constr(min_length=6, max_length=128)
    
    @validator('new_password')
    def validate_password(cls, v):
        # Prevent command injection in password
        dangerous_patterns = [
            r'[;\\`$()]',  # Command injection
            r'\{.*%',  # SSTI
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, v):
                raise ValueError('Password contains invalid characters')
        return v


class ChangeEmailRequest(BaseModel):
    new_email: EmailStr
    password: str


# AI Provider configuration models
class ProviderItem(BaseModel):
    key: str
    name: str
    model: str
    env_var: str
    api_key_url: str
    description: str
    icon: str
    api_base: Optional[str] = None


class SaveProvidersRequest(BaseModel):
    providers: List[ProviderItem]


# ============================================================================
# Authentication Helper Functions (using database)
# ============================================================================
# All user and token operations now use SQLite database via hades.web.database


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Verify JWT token and return user data"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = get_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Database initialization is done at module import level


# ============================================================================
# API Routes
# ============================================================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "HADES Web Interface"}


# ============================================================================
# Authentication API
# ============================================================================

@app.post("/api/auth/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    """Register a new user"""
    # Check if user already exists
    existing_user = get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate password
    if len(user_data.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters"
        )
    
    # Create user
    try:
        user = create_user(
            email=user_data.email.lower(),
            password=user_data.password,
            name=user_data.name
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_data.email.lower()}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "email": user["email"],
            "name": user["name"],
            "username": user.get("username", user["name"]),
            "profile_image": user.get("profile_image")
        }
    }


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    """Login user"""
    email = user_data.email.lower()
    
    # Get user from database
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Verify password
    if not verify_password(user_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "email": user["email"],
            "name": user.get("name", ""),
            "username": user.get("username", user.get("name", "")),
            "profile_image": user.get("profile_image")
        }
    }


@app.post("/api/auth/reset-password-request")
async def reset_password_request(request: ResetPasswordRequest):
    """Request password reset"""
    email = request.email.lower()
    
    # Check if user exists
    user = get_user_by_email(email)
    if not user:
        # Don't reveal if user exists for security
        return {"message": "If the email exists, a reset link has been sent"}
    
    # Generate reset token
    reset_token = secrets.token_urlsafe(32)
    create_reset_token(email, reset_token, expires_in_hours=1)
    
    # In production, send email with reset link
    # For now, return token (in production, don't return token)
    return {
        "message": "Password reset token generated",
        "token": reset_token  # Remove this in production, send via email instead
    }


@app.post("/api/auth/reset-password")
async def reset_password(reset_data: ResetPassword):
    """Reset password using token"""
    # Get token from database
    token_data = get_reset_token(reset_data.token)
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Validate new password
    if len(reset_data.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters"
        )
    
    # Update password
    email = token_data["email"]
    if not update_user_password(email, reset_data.new_password):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Remove used token
    delete_reset_token(reset_data.token)
    
    return {"message": "Password reset successfully"}


@app.get("/api/auth/me")
async def get_current_user(current_user: Dict[str, Any] = Depends(verify_token)):
    """Get current user information"""
    # Get username changes from database
    username_changes = get_username_changes(current_user["email"])
    
    return {
        "email": current_user["email"],
        "name": current_user.get("name", ""),
        "username": current_user.get("username", current_user.get("name", "")),
        "profile_image": current_user.get("profile_image"),
        "username_changes": username_changes
    }


# ============================================================================
# Security Helper Functions
# ============================================================================

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and other attacks"""
    # Remove path components
    filename = os.path.basename(filename)
    # Remove dangerous characters
    filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
    # Limit length
    if len(filename) > 100:
        filename = filename[:100]
    return filename


def validate_image_file(file: UploadFile) -> tuple[bool, str]:
    """Validate uploaded image file with comprehensive security checks"""
    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset
    
    if file_size > MAX_IMAGE_SIZE:
        return False, f"File size exceeds {MAX_IMAGE_SIZE / 1024 / 1024}MB"
    
    if file_size == 0:
        return False, "File is empty"
    
    # Read file content for validation
    content = file.file.read()
    file.file.seek(0)  # Reset
    
    # Security: Check file signature (magic bytes) to prevent extension bypass
    # This is more secure than trusting content-type header
    allowed_signatures = {
        b'\xff\xd8\xff',  # JPEG
        b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a',  # PNG
        b'GIF87a',  # GIF87a
        b'GIF89a',  # GIF89a
        b'\x52\x49\x46\x46',  # WebP (RIFF)
    }
    
    # Check magic bytes
    is_valid_signature = False
    for signature in allowed_signatures:
        if content.startswith(signature):
            is_valid_signature = True
            break
    
    if not is_valid_signature:
        return False, "Invalid file signature. Only JPEG, PNG, GIF, and WebP are allowed"
    
    # Security: Explicitly block SVG files (can contain XSS/XXE)
    if content.startswith(b'<?xml') or b'<svg' in content[:1000].lower() or b'<!DOCTYPE svg' in content[:1000].lower():
        return False, "SVG files are not allowed for security reasons"
    
    # Security: Block XML-based formats (XXE vulnerability)
    if content.startswith(b'<?xml') or content.startswith(b'<!DOCTYPE'):
        return False, "XML-based formats are not allowed"
    
    # Security: Check for embedded scripts and dangerous content
    dangerous_patterns = [
        b'<script',
        b'javascript:',
        b'onerror=',
        b'onload=',
        b'<iframe',
        b'<object',
        b'<embed',
        b'data:text/html',
        b'vbscript:',
        b'<svg',
        b'<?php',
        b'<%',
        b'#!/',
        b'__import__',
        b'eval(',
        b'exec(',
        b'system(',
    ]
    
    # Check first 10KB for dangerous patterns (most attacks are in headers/metadata)
    content_to_check = content[:10240].lower()
    for pattern in dangerous_patterns:
        if pattern.lower() in content_to_check:
            return False, f"File contains potentially dangerous content: {pattern.decode('utf-8', errors='ignore')}"
    
    # Security: Check content type header matches actual file
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        return False, f"File type {file.content_type} not allowed"
    
    # Verify it's actually an image using PIL (this will fail on non-image files)
    try:
        img = Image.open(io.BytesIO(content))
        
        # Security: Force PIL to verify the image structure
        img.verify()
        
        # Reopen after verify (verify() closes the image)
        img = Image.open(io.BytesIO(content))
        
        # Security: Check image format matches expected
        format_lower = img.format.lower() if img.format else ''
        if format_lower not in ['jpeg', 'png', 'gif', 'webp']:
            return False, f"Image format {img.format} is not allowed"
        
        # Check dimensions
        width, height = img.size
        if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
            return False, f"Image dimensions exceed {MAX_IMAGE_DIMENSION}x{MAX_IMAGE_DIMENSION}"
        
        # Security: Check for extremely small or invalid dimensions (potential DoS)
        if width < 1 or height < 1:
            return False, "Invalid image dimensions"
        
        # Security: Check aspect ratio for extreme values (potential DoS)
        aspect_ratio = max(width, height) / min(width, height) if min(width, height) > 0 else 0
        if aspect_ratio > 100:
            return False, "Image aspect ratio is too extreme"
        
        # Security: Check file size vs image dimensions (detect embedded content)
        pixels = width * height
        expected_min_size = pixels * 0.1  # Rough estimate
        if file_size < expected_min_size and file_size < 1000:
            # Suspiciously small file for its dimensions
            return False, "File size does not match image dimensions (possible embedded content)"
            
    except Exception as e:
        return False, f"Invalid image file: {str(e)}"
    
    return True, ""


def can_change_username(email: str) -> tuple[bool, str]:
    """Check if user can change username (max 2x per 7 days)"""
    changes_count = get_username_changes_count(email, days=7)
    
    if changes_count >= 2:
        # Get oldest change in last 7 days
        changes = get_username_changes(email, limit=2)
        if changes:
            oldest_change = min(changes, key=lambda x: x["changed_at"])
            change_date = datetime.fromisoformat(oldest_change["changed_at"])
            next_allowed = change_date + timedelta(days=7)
            return False, f"You can change username again after {next_allowed.strftime('%Y-%m-%d %H:%M:%S')}"
    
    return True, ""


# ============================================================================
# Profile Management API
# ============================================================================

@app.put("/api/auth/username")
async def update_username(
    request: UpdateUsernameRequest,
    current_user: Dict[str, Any] = Depends(verify_token)
):
    """Update username (max 2x per 7 days)"""
    email = current_user["email"]
    
    # Check if user exists
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if username change is allowed
    can_change, message = can_change_username(email)
    if not can_change:
        raise HTTPException(status_code=400, detail=message)
    
    # Check if new username is same as current
    current_username = user.get("username") or user.get("name", "")
    if request.new_username.strip() == current_username.strip():
        raise HTTPException(status_code=400, detail="New username is same as current")
    
    # Update username
    try:
        updated_user = db_update_username(email, request.new_username)
        changes_count = get_username_changes_count(email, days=7)
        
        return {
            "message": "Username updated successfully",
            "username": request.new_username,
            "changes_remaining": max(0, 2 - changes_count)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update username: {str(e)}")


@app.post("/api/auth/profile-image")
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(verify_token)
):
    """Upload profile image with security validation"""
    # Validate file
    is_valid, error_msg = validate_image_file(file)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    email = current_user["email"]
    
    # Get user from database
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Read file content
    content = await file.read()
    
    # Process image: resize and optimize with security measures
    try:
        # Security: Re-verify image after reading
        img = Image.open(io.BytesIO(content))
        
        # Security: Force convert to RGB and strip all metadata
        # This removes any embedded scripts, EXIF data, or other metadata
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Security: Resize to standard size to prevent DoS and remove any embedded content
        max_profile_size = 500
        if img.width > max_profile_size or img.height > max_profile_size:
            img.thumbnail((max_profile_size, max_profile_size), Image.Resampling.LANCZOS)
        
        # Security: Generate secure filename with timestamp to prevent collisions
        timestamp = datetime.utcnow().isoformat()
        file_hash = hashlib.sha256(f"{email}{timestamp}{secrets.token_hex(8)}".encode()).hexdigest()[:32]
        filename = f"{file_hash}.jpg"
        filepath = PROFILE_IMAGES_DIR / filename
        
        # Security: Save as JPEG with no metadata to strip all embedded data
        # This ensures no scripts, EXIF, or other metadata can be embedded
        # Create a new image without metadata by copying pixel data only
        clean_img = Image.new('RGB', img.size)
        clean_img.paste(img)
        clean_img.save(filepath, 'JPEG', quality=85, optimize=True)
        
        # Security: Verify saved file is actually a valid image
        try:
            verify_img = Image.open(filepath)
            verify_img.verify()
            verify_img = Image.open(filepath)  # Reopen after verify
            if verify_img.format.lower() != 'jpeg':
                # If somehow not JPEG, delete and reject
                filepath.unlink()
                raise HTTPException(status_code=400, detail="Failed to process image securely")
        except Exception as e:
            if filepath.exists():
                filepath.unlink()
            raise HTTPException(status_code=400, detail=f"Image validation failed: {str(e)}")
        
        # Security: Verify file actually exists on disk before updating database
        if not filepath.exists() or not filepath.is_file():
            raise HTTPException(status_code=500, detail="Failed to save image file")
        
        # Remove old profile image if exists (before updating database)
        old_image = user.get("profile_image")
        if old_image:
            old_path = PROFILE_IMAGES_DIR / old_image
            if old_path.exists() and old_path.is_file():
                try:
                    old_path.unlink()
                except Exception:
                    pass  # Ignore errors when deleting old image
        
        # Update user profile image in database
        # This ensures the filename is stored in SQLite for persistence
        update_success = update_profile_image(email, filename)
        if not update_success:
            # If database update fails, delete the file we just created
            if filepath.exists():
                filepath.unlink()
            raise HTTPException(status_code=500, detail="Failed to update profile image in database")
        
        # Verify database was updated correctly
        updated_user = get_user_by_email(email)
        if not updated_user or updated_user.get("profile_image") != filename:
            # Database update didn't work, clean up file
            if filepath.exists():
                filepath.unlink()
            raise HTTPException(status_code=500, detail="Database update verification failed")
        
        return {
            "message": "Profile image uploaded successfully",
            "profile_image": filename
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


@app.get("/api/auth/profile-image/{filename}")
async def get_profile_image(filename: str):
    """Get profile image with security headers"""
    # Security: prevent path traversal
    filename = sanitize_filename(filename)
    
    # Security: Additional validation - only allow .jpg extension
    if not filename.endswith('.jpg'):
        raise HTTPException(status_code=400, detail="Invalid file extension")
    
    filepath = PROFILE_IMAGES_DIR / filename
    
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Security: ensure file is in profile_images directory (prevent path traversal)
    try:
        filepath.resolve().relative_to(PROFILE_IMAGES_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid file path")
    
    # Security: Verify file is actually a valid image before serving
    try:
        with open(filepath, 'rb') as f:
            content = f.read(10)  # Read first 10 bytes
            # Check JPEG signature
            if not content.startswith(b'\xff\xd8\xff'):
                raise HTTPException(status_code=400, detail="Invalid image file")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file")
    
    # Security: Add security headers to prevent XSS and other attacks
    from fastapi.responses import Response
    with open(filepath, 'rb') as f:
        content = f.read()
    
    return Response(
        content=content,
        media_type="image/jpeg",
        headers={
            "Content-Disposition": "inline",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Content-Security-Policy": "default-src 'self'",
        }
    )


@app.post("/api/auth/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: Dict[str, Any] = Depends(verify_token)
):
    """Change password (authenticated user)"""
    email = current_user["email"]
    
    # Get user from database
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify current password
    if not verify_password(request.current_password, user["password"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    
    # Update password
    if not update_user_password(email, request.new_password):
        raise HTTPException(status_code=500, detail="Failed to update password")
    
    return {"message": "Password changed successfully"}


@app.post("/api/auth/change-email")
async def change_email(
    request: ChangeEmailRequest,
    current_user: Dict[str, Any] = Depends(verify_token)
):
    """Change email address"""
    old_email = current_user["email"].lower()
    new_email = request.new_email.lower()
    
    # Get user from database
    user = get_user_by_email(old_email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify password
    if not verify_password(request.password, user["password"]):
        raise HTTPException(status_code=401, detail="Password is incorrect")
    
    # Check if new email already exists
    existing_user = get_user_by_email(new_email)
    if existing_user:
        raise HTTPException(status_code=400, detail="New email already registered")
    
    # Update email
    if not update_user_email(old_email, new_email):
        raise HTTPException(status_code=500, detail="Failed to update email")
    
    # Get updated user
    updated_user = get_user_by_email(new_email)
    
    # Create new access token with new email
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "email": updated_user["email"],
            "name": updated_user.get("name", ""),
            "username": updated_user.get("username", updated_user.get("name", ""))
        },
        "message": "Email updated successfully"
    }


# ============================================================================
# Template Management API
# ============================================================================

@app.get("/api/templates")
async def get_templates():
    """Get list of all templates"""
    try:
        templates = list_templates()
        result = []
        for template_name in templates:
            content = read_template(template_name)
            if content:
                result.append({
                    "name": template_name,
                    "size": len(content),
                    "preview": content[:100] + "..." if len(content) > 100 else content
                })
        return {"templates": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/templates/{template_name}")
async def get_template(template_name: str):
    """Get a specific template"""
    try:
        content = read_template(template_name)
        if content is None:
            raise HTTPException(status_code=404, detail="Template not found")
        return {"name": template_name, "content": content}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/templates")
async def create_template_api(template: TemplateCreate):
    """Create a new template"""
    try:
        success = create_template(template.name, template.content)
        if not success:
            raise HTTPException(status_code=400, detail="Template creation failed")
        return {"message": "Template created successfully", "name": template.name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/templates/{template_name}")
async def update_template_api(template_name: str, template: TemplateUpdate):
    """Update an existing template"""
    try:
        success = update_template(template_name, template.content)
        if not success:
            raise HTTPException(status_code=404, detail="Template not found")
        return {"message": "Template updated successfully", "name": template_name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/templates/{template_name}")
async def delete_template_api(template_name: str):
    """Delete a template"""
    try:
        success = delete_template(template_name)
        if not success:
            raise HTTPException(status_code=404, detail="Template not found")
        return {"message": "Template deleted successfully", "name": template_name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API Key Configuration API
# ============================================================================

@app.get("/api/providers")
async def get_providers():
    """Get list of all AI providers"""
    try:
        # Import AI_PROVIDERS from main.py
        script_dir = Path(__file__).parent.parent.parent
        
        # Read main.py and extract AI_PROVIDERS
        import importlib.util
        main_path = script_dir / "main.py"
        
        if not main_path.exists():
            raise HTTPException(status_code=500, detail="main.py not found")
        
        spec = importlib.util.spec_from_file_location("main_module", main_path)
        if spec is None or spec.loader is None:
            raise HTTPException(status_code=500, detail="Could not load main.py")
        
        main_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main_module)
        
        if not hasattr(main_module, 'AI_PROVIDERS'):
            raise HTTPException(status_code=500, detail="AI_PROVIDERS not found in main.py")
        
        providers = []
        for key, provider in main_module.AI_PROVIDERS.items():
            providers.append({
                "key": key,
                "name": provider["name"],
                "model": provider["model"],
                "env_var": provider["env_var"],
                "api_key_url": provider["api_key_url"],
                "description": provider["description"],
                "icon": provider["icon"],
                "api_base": provider.get("api_base")
            })

        return {"providers": providers}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading providers: {str(e)}")


@app.post("/api/providers")
async def save_providers(payload: SaveProvidersRequest):
    """Save/Update the list of AI providers"""
    try:
        # Write debug payload to config/debug_payload.json
        config_dir = Path(__file__).parent.parent.parent / "config"
        config_dir.mkdir(exist_ok=True)
        with open(config_dir / "debug_payload.json", "w", encoding="utf-8") as debug_f:
            json.dump([p.dict() for p in payload.providers], debug_f, indent=4)

        new_providers = {}
        for p in payload.providers:
            new_providers[str(p.key)] = {
                "name": p.name,
                "model": p.model,
                "env_var": p.env_var,
                "api_key_url": p.api_key_url,
                "description": p.description,
                "icon": p.icon,
                "api_base": p.api_base
            }

        # Save to config/providers.json
        config_dir = Path(__file__).parent.parent.parent / "config"
        config_dir.mkdir(exist_ok=True)
        providers_file = config_dir / "providers.json"

        with open(providers_file, 'w', encoding='utf-8') as f:
            json.dump(new_providers, f, indent=4)

        return {"success": True, "message": "Providers configuration saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save providers: {str(e)}")


@app.get("/api/config/keys")
async def get_api_keys():
    """Get current API key configuration"""
    try:
        env_file = Path(__file__).parent.parent.parent / ".env"
        keys = {}
        
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        keys[key.strip()] = value.strip()
        
        return {"keys": keys}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config/keys")
async def save_api_keys(configs: List[APIConfig]):
    """Save API keys"""
    try:
        script_dir = Path(__file__).parent.parent.parent
        main_path = script_dir / "main.py"
        
        if not main_path.exists():
            raise HTTPException(status_code=500, detail="main.py not found")
        
        import importlib.util
        spec = importlib.util.spec_from_file_location("main_module", main_path)
        if not spec or not spec.loader:
            raise HTTPException(status_code=500, detail="Could not load main.py")
            
        main_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main_module)
        
        if not hasattr(main_module, 'save_multiple_api_keys_to_env'):
            raise HTTPException(status_code=500, detail="save_multiple_api_keys_to_env not found in main.py")
            
        # Convert List[APIConfig] to Dict[provider_key, api_key]
        api_keys_dict = {config.provider_key: config.api_key for config in configs}
        
        # Save keys using the centralized function
        success = main_module.save_multiple_api_keys_to_env(api_keys_dict)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save API keys to .env file")
            
        return {"message": "API keys saved successfully"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error saving API keys: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config/provider/upload-keys")
async def upload_provider_keys(
    provider_key: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload file containing multiple API keys for any provider (one per line)"""
    try:
        if not file.filename.endswith('.txt'):
            raise HTTPException(status_code=400, detail="Only .txt files are allowed")
        
        # Get provider info
        import importlib.util
        script_dir = Path(__file__).parent.parent.parent
        main_path = script_dir / "main.py"
        
        if not main_path.exists():
            raise HTTPException(status_code=500, detail="Cannot find main.py")
        
        spec = importlib.util.spec_from_file_location("main_module", main_path)
        if not spec or not spec.loader:
            raise HTTPException(status_code=500, detail="Cannot load main.py")
        
        main_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main_module)
        
        if not hasattr(main_module, 'AI_PROVIDERS') or provider_key not in main_module.AI_PROVIDERS:
            raise HTTPException(status_code=400, detail="Invalid provider key")
        
        provider = main_module.AI_PROVIDERS[provider_key]
        env_var_name = provider['env_var']
        
        content = await file.read()
        text_content = content.decode('utf-8')
        
        # Parse API keys (one per line, skip empty lines and comments)
        api_keys = []
        for line in text_content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                if len(line) >= 10:  # Basic validation
                    api_keys.append(line)
        
        if not api_keys:
            raise HTTPException(status_code=400, detail="No valid API keys found in file (minimum 10 characters)")
        
        # Save to .env file
        env_file = script_dir / ".env"
        
        # Read existing .env
        env_vars = {}
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        
        # Save multiple API keys for provider
        keys_var = f"{env_var_name}_KEYS"
        index_var = f"{env_var_name}_INDEX"
        
        env_vars[env_var_name] = api_keys[0]  # Primary key
        env_vars[keys_var] = '\n'.join(api_keys)  # All keys
        env_vars[index_var] = '0'  # Start with first key
        
        # Write back
        with open(env_file, 'w', encoding='utf-8') as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
        
        return {
            "message": f"Successfully uploaded {len(api_keys)} {provider['name']} API key(s)!",
            "count": len(api_keys),
            "current_index": 0,
            "provider_name": provider['name']
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config/providers")
async def get_configured_providers():
    """Get all configured providers with their status"""
    try:
        import importlib.util
        script_dir = Path(__file__).parent.parent.parent
        main_path = script_dir / "main.py"
        
        if not main_path.exists():
            return {"providers": []}
        
        spec = importlib.util.spec_from_file_location("main_module", main_path)
        if not spec or not spec.loader:
            return {"providers": []}
        
        main_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main_module)
        
        if not hasattr(main_module, 'AI_PROVIDERS'):
            return {"providers": []}
        
        AI_PROVIDERS = main_module.AI_PROVIDERS
        
        env_file = script_dir / ".env"
        if not env_file.exists():
            return {"providers": [], "active_provider": None}
        
        # Read .env
        env_vars = {}
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
        
        current_active = env_vars.get('HADES_LLM', '')
        
        providers = []
        for provider_key, provider in AI_PROVIDERS.items():
            env_var_name = provider['env_var']
            keys_var = f"{env_var_name}_KEYS"
            index_var = f"{env_var_name}_INDEX"
            
            has_key = False
            is_multiple = False
            count = 0
            current_index = 0
            
            if keys_var in env_vars:
                api_keys = env_vars[keys_var].split('\n')
                api_keys = [k.strip() for k in api_keys if k.strip()]
                if api_keys:
                    has_key = True
                    is_multiple = True
                    count = len(api_keys)
                    current_index = int(env_vars.get(index_var, '0'))
            elif env_var_name in env_vars and env_vars[env_var_name]:
                has_key = True
                is_multiple = False
                count = 1
                current_index = 0
            
            if has_key:
                is_active = current_active == provider['model']
                providers.append({
                    "key": provider_key,
                    "name": provider['name'],
                    "model": provider['model'],
                    "icon": provider['icon'],
                    "description": provider['description'],
                    "is_active": is_active,
                    "is_multiple": is_multiple,
                    "key_count": count,
                    "current_key_index": current_index,
                    "api_base": provider.get("api_base")
                })
        
        return {
            "providers": providers,
            "active_provider": current_active
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config/active-provider")
async def set_active_provider(provider_key: str = Form(...)):
    """Set active provider"""
    try:
        import importlib.util
        script_dir = Path(__file__).parent.parent.parent
        main_path = script_dir / "main.py"
        
        if not main_path.exists():
            raise HTTPException(status_code=500, detail="Cannot find main.py")
        
        spec = importlib.util.spec_from_file_location("main_module", main_path)
        if not spec or not spec.loader:
            raise HTTPException(status_code=500, detail="Cannot load main.py")
        
        main_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main_module)
        
        if not hasattr(main_module, 'AI_PROVIDERS') or provider_key not in main_module.AI_PROVIDERS:
            raise HTTPException(status_code=400, detail="Invalid provider key")
        
        if not hasattr(main_module, 'save_multiple_api_keys_to_env'):
            raise HTTPException(status_code=500, detail="Cannot find save function")
        
        provider = main_module.AI_PROVIDERS[provider_key]
        
        # Check if provider has API key configured
        env_file = script_dir / ".env"
        if not env_file.exists():
            raise HTTPException(status_code=400, detail="No .env file found. Please configure API keys first.")
        
        # Read .env to check if provider has keys
        env_vars = {}
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
        
        env_var_name = provider['env_var']
        keys_var = f"{env_var_name}_KEYS"
        has_key = False
        
        if keys_var in env_vars:
            api_keys = env_vars[keys_var].split('\n')
            api_keys = [k.strip() for k in api_keys if k.strip()]
            has_key = len(api_keys) > 0
        elif env_var_name in env_vars and env_vars[env_var_name]:
            has_key = True
        
        if not has_key:
            raise HTTPException(
                status_code=400, 
                detail=f"No API key configured for {provider['name']}. Please configure API key first."
            )
        
        # Set as active provider (pass empty dict to only update active provider)
        success = main_module.save_multiple_api_keys_to_env({}, active_provider=provider_key)
        
        if success:
            return {
                "message": f"Active provider set to {provider['name']}",
                "provider": {
                    "key": provider_key,
                    "name": provider['name'],
                    "model": provider['model'],
                    "icon": provider['icon']
                }
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to set active provider")
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = str(e)
        # Log full traceback for debugging
        print(f"Error setting active provider: {error_detail}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to set active provider: {error_detail}")


@app.get("/api/config/provider/status")
async def get_provider_key_status(provider_key: str):
    """Get current API key status for a provider (which key is active)"""
    try:
        # Get provider info
        import importlib.util
        script_dir = Path(__file__).parent.parent.parent
        main_path = script_dir / "main.py"
        
        if not main_path.exists():
            return {
                "has_keys": False,
                "count": 0,
                "current_index": 0,
                "current_key_preview": None
            }
        
        spec = importlib.util.spec_from_file_location("main_module", main_path)
        if not spec or not spec.loader:
            return {
                "has_keys": False,
                "count": 0,
                "current_index": 0,
                "current_key_preview": None
            }
        
        main_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(main_module)
        
        if not hasattr(main_module, 'AI_PROVIDERS') or provider_key not in main_module.AI_PROVIDERS:
            return {
                "has_keys": False,
                "count": 0,
                "current_index": 0,
                "current_key_preview": None
            }
        
        provider = main_module.AI_PROVIDERS[provider_key]
        env_var_name = provider['env_var']
        
        env_file = script_dir / ".env"
        
        if not env_file.exists():
            return {
                "has_keys": False,
                "count": 0,
                "current_index": 0,
                "current_key_preview": None
            }
        
        # Read .env
        env_vars = {}
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
        
        # Check for multiple keys
        keys_var = f"{env_var_name}_KEYS"
        index_var = f"{env_var_name}_INDEX"
        
        if keys_var in env_vars:
            api_keys = env_vars[keys_var].split('\n')
            api_keys = [k.strip() for k in api_keys if k.strip()]
            count = len(api_keys)
            current_index = int(env_vars.get(index_var, '0'))
            
            # Get preview of current key (first 10 and last 4 chars)
            current_key = api_keys[current_index] if current_index < count else api_keys[0]
            preview = f"{current_key[:10]}...{current_key[-4:]}" if len(current_key) > 14 else current_key[:10] + "..."
            
            return {
                "has_keys": True,
                "count": count,
                "current_index": current_index,
                "current_key_preview": preview,
                "current_key_number": current_index + 1
            }
        elif env_var_name in env_vars:
            # Single key
            key = env_vars[env_var_name]
            preview = f"{key[:10]}...{key[-4:]}" if len(key) > 14 else key[:10] + "..."
            return {
                "has_keys": True,
                "count": 1,
                "current_index": 0,
                "current_key_preview": preview,
                "current_key_number": 1
            }
        else:
            return {
                "has_keys": False,
                "count": 0,
                "current_index": 0,
                "current_key_preview": None
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class TestProviderRequest(BaseModel):
    provider_key: str
    api_key: str
    model: str
    api_base: Optional[str] = None


@app.post("/api/config/test-provider")
async def test_provider_connection(request: TestProviderRequest):
    """Test if an API key works for a specific provider"""
    try:
        import litellm
        import asyncio

        # Prepare test message
        test_messages = [
            {"role": "user", "content": "Say 'test successful' if you can read this."}
        ]

        # Prepare completion args based on model
        model_name = request.model
        completion_args = {
            "model": model_name,
            "messages": test_messages,
            "max_tokens": 50,
            "timeout": 30,
        }

        # Set custom api_base if provided
        if request.api_base:
            completion_args["api_base"] = request.api_base
            # If using custom api_base, force custom_llm_provider to openai for compatible endpoints
            if not model_name.startswith("openrouter/") and not model_name.startswith("deepseek/"):
                completion_args["custom_llm_provider"] = "openai"
                # Strip prefix (like 'mimo/' or 'openai/') from model name so the API receives the raw model name
                if "/" in model_name:
                    completion_args["model"] = model_name.split("/", 1)[1]
        
        # Set API key temporarily
        original_api_key = litellm.api_key
        litellm.api_key = request.api_key
        
        # Handle OpenRouter specifically
        if model_name.startswith("openrouter/"):
            completion_args["custom_llm_provider"] = "openrouter"
            # Set the API key in environment for OpenRouter
            os.environ["OPENROUTER_API_KEY"] = request.api_key
        
        # Handle DeepSeek specifically - Use OpenAI-compatible protocol for reliability
        elif model_name.startswith("deepseek/"):
            completion_args["custom_llm_provider"] = "openai"
            completion_args["api_base"] = "https://api.deepseek.com"
            completion_args["api_key"] = request.api_key
            completion_args["model"] = "deepseek-chat" if "deepseek-chat" in model_name else "deepseek-reasoner"
            os.environ["DEEPSEEK_API_KEY"] = request.api_key
        
        # Handle other providers
        elif "gemini" in model_name.lower() or "google" in model_name.lower():
            os.environ["GOOGLE_API_KEY"] = request.api_key
        elif "gpt" in model_name.lower() or model_name.startswith("openai/"):
            os.environ["OPENAI_API_KEY"] = request.api_key
        elif "claude" in model_name.lower() or "anthropic" in model_name.lower():
            os.environ["ANTHROPIC_API_KEY"] = request.api_key
        elif "groq" in model_name.lower():
            os.environ["GROQ_API_KEY"] = request.api_key
        
        # Handle Local Models (Directly via Transformers)
        if model_name.startswith("huggingface/"):
            try:
                from hades.llm.llm import LLM, LLMConfig
                llm_config = LLMConfig(model_name=model_name)
                llm_test = LLM(llm_config)
                # This will trigger lazy loading and model call
                test_resp = await llm_test._make_local_transformers_request(test_messages, model_name)
                return {
                    "success": True,
                    "message": "Local model (Transformers) successfully loaded and responded. Ready for use!",
                    "model_response": test_resp.choices[0].message.content[:100],
                    "provider": request.provider_key
                }
            except Exception as e:
                return {
                    "success": False,
                    "message": f"Transformers local test failed. Ensure 'transformers' and 'torch' are installed on WSL.",
                    "error": str(e),
                    "provider": request.provider_key
                }
        
        try:
            # Make test request
            response = await asyncio.to_thread(
                litellm.completion,
                **completion_args
            )
            
            # Restore original API key
            litellm.api_key = original_api_key
            
            # Extract response content
            content = ""
            if response.choices and hasattr(response.choices[0], "message"):
                content = getattr(response.choices[0].message, "content", "")
            
            return {
                "success": True,
                "message": "API key is valid and model is accessible",
                "model_response": content[:100] if content else "No response content",
                "provider": request.provider_key
            }
            
        except litellm.AuthenticationError as e:
            litellm.api_key = original_api_key
            return {
                "success": False,
                "message": "Authentication failed - Invalid API key",
                "error": str(e),
                "provider": request.provider_key
            }
        except litellm.NotFoundError as e:
            litellm.api_key = original_api_key
            return {
                "success": False,
                "message": f"Model '{model_name}' not found or not accessible",
                "error": str(e),
                "provider": request.provider_key
            }
        except litellm.RateLimitError as e:
            litellm.api_key = original_api_key
            return {
                "success": False,
                "message": "Rate limit exceeded - API key is valid but quota exceeded",
                "error": str(e),
                "provider": request.provider_key
            }
        except Exception as e:
            litellm.api_key = original_api_key
            return {
                "success": False,
                "message": f"Test failed: {str(e)}",
                "error": str(e),
                "provider": request.provider_key
            }
            
    except Exception as e:
        import traceback
        print(f"Error testing provider: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to test provider: {str(e)}")


# ============================================================================
# Docker Status API
# ============================================================================

@app.get("/api/docker/status")
async def get_docker_status():
    """Get Docker installation and status"""
    try:
        status = {
            "docker_installed": False,
            "docker_running": False,
            "docker_image_available": False,
            "docker_image_name": os.getenv("HADES_IMAGE", "ghcr.io/joelindra/hades-sandbox-now:latest"),
            "error": None,
        }
        
        try:
            import docker
            status["docker_installed"] = True
            
            try:
                client = docker.from_env()
                client.ping()
                status["docker_running"] = True
                
                # Check if image is available
                try:
                    image_name = status["docker_image_name"]
                    client.images.get(image_name)
                    status["docker_image_available"] = True
                except Exception:
                    status["docker_image_available"] = False
                    
            except Exception as e:
                status["error"] = str(e)
                status["docker_running"] = False
                
        except ImportError:
            status["error"] = "Docker Python library not installed"
            status["docker_installed"] = False
        
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Scan Management API
# ============================================================================

@app.post("/api/scan/start")
async def start_scan(scan_request: ScanRequest, background_tasks: BackgroundTasks):
    """Start a HADES scan"""
    try:
        script_dir = Path(__file__).parent.parent.parent
        
        # Ensure agent_runs directory exists
        agent_runs_dir = script_dir / "agent_runs"
        agent_runs_dir.mkdir(exist_ok=True)
        
        # Generate run_name if not provided
        import random
        if not scan_request.run_name or not scan_request.run_name.strip():
            adjectives = [
                "stealthy", "sneaky", "crafty", "elite", "phantom", "shadow", "silent",
                "rogue", "covert", "ninja", "ghost", "cyber", "digital", "binary",
                "encrypted", "obfuscated", "masked", "cloaked", "invisible", "anonymous"
            ]
            nouns = [
                "exploit", "payload", "backdoor", "rootkit", "keylogger", "botnet", "trojan",
                "worm", "virus", "packet", "buffer", "shell", "daemon", "spider", "crawler",
                "hunter", "scanner", "probe", "sniffer", "listener", "agent", "vector"
            ]
            scan_request.run_name = f"{random.choice(adjectives)}-{random.choice(nouns)}-{random.randint(100, 999)}"
        
        # Build command
        # The user wants exactly: python3 main.py -t <target> --templates <templates>
        # We use python3 main.py to ensure it runs correctly in WSL/Linux environments
        cmd = ["python3", "main.py"]
        
        for target in scan_request.targets:
            cmd.extend(["-t", target])
        
        if scan_request.template:
            cmd.extend(["--templates", scan_request.template])
            
        if scan_request.run_name:
            cmd.extend(["--run-name", scan_request.run_name])
            
        if scan_request.instruction:
            cmd.extend(["--instruction", scan_request.instruction])

        # Respect the non_interactive flag from the request
        # By default it's False, so it will open the TUI (HadesAgent) as requested
        if scan_request.non_interactive:
            cmd.append("--non-interactive")
        
        # Run in background in a NEW terminal window
        def run_scan():
            try:
                import os
                import platform
                
                # Detect if running on Windows (including WSL)
                is_windows = platform.system() == 'Windows' or os.path.exists('/mnt/c/Windows')
                
                if is_windows or os.path.exists('/mnt/c/Windows'):
                    # Running on Windows or WSL - open new PowerShell terminal with WSL
                    wsl_path = str(script_dir)

                    # If running natively on Windows, convert Windows path to WSL format for the bash cd command
                    if platform.system() == 'Windows' and len(wsl_path) > 1 and wsl_path[1] == ':':
                        drive = wsl_path[0].lower()
                        wsl_path = f"/mnt/{drive}{wsl_path[2:].replace('\\\\', '/').replace('\\', '/')}"

                    # Convert WSL path to Windows path for display
                    if wsl_path.startswith('/mnt/'):
                        drive_letter = wsl_path[5].upper()
                        win_path = f"{drive_letter}:{wsl_path[6:].replace('/', '\\\\')}"
                    else:
                        win_path = wsl_path
                    
                    # Detect WSL distribution name
                    try:
                        distro_result = subprocess.run(
                            ['wsl', '-l', '-q'],
                            capture_output=True,
                            text=True,
                            encoding='utf-16-le'
                        )
                        distros = [d.strip() for d in distro_result.stdout.strip().split('\n') if d.strip()]
                        wsl_distro = distros[0] if distros else 'kali-linux'
                    except:
                        wsl_distro = 'kali-linux'
                    
                    # Build the bash command
                    escaped_cmd = []
                    for arg in cmd:
                        if ' ' in arg:
                            # Wrap in single quotes and escape existing single quotes
                            safe_arg = arg.replace("'", "'\\''")
                            escaped_cmd.append(f"'{safe_arg}'")
                        else:
                            escaped_cmd.append(arg)
                    
                    bash_cmd = ' '.join(escaped_cmd)
                    full_bash_script = f"cd '{wsl_path}' && {bash_cmd}; echo; echo 'Scan completed. Press Enter to close...'; read"
                    
                    # Command to run in the new window
                    target_window_cmd = f'wsl -d {wsl_distro} bash -c "{full_bash_script}"'
                    
                    # Base64 encode the command for PowerShell -EncodedCommand (must be UTF-16LE)
                    import base64
                    encoded_cmd = base64.b64encode(target_window_cmd.encode('utf-16le')).decode('ascii')
                    
                    # PowerShell command that launches the new window
                    ps_command = f'Start-Process powershell.exe -ArgumentList "-NoExit", "-EncodedCommand", "{encoded_cmd}"'
                    
                    try:
                        # Launch via PowerShell
                        subprocess.Popen(
                            ['powershell.exe', '-NoProfile', '-WindowStyle', 'Hidden', '-Command', ps_command],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            stdin=subprocess.DEVNULL,
                            start_new_session=True,
                            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if hasattr(subprocess, 'CREATE_NEW_PROCESS_GROUP') else 0
                        )
                        print(f"✓ Launched scan '{scan_request.run_name}' in new PowerShell window (WSL: {wsl_distro})")
                    except Exception as e:
                        print(f"⚠ Failed to launch PowerShell window: {e}")
                        print(f"⚠ Running scan '{scan_request.run_name}' in background...")
                        # Fallback: run silently in background
                        subprocess.Popen(
                            cmd,
                            cwd=str(script_dir),
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            stdin=subprocess.DEVNULL,
                            start_new_session=True
                        )
                else:
                    # Linux native - search for available terminal emulator
                    cmd_str = ' '.join([f'"{arg}"' if ' ' in arg else arg for arg in cmd])
                    # Common Linux terminal emulators and their command execution flags
                    terminal_commands = [
                        # 1. Debian/Kali standard preferred terminal
                        f'x-terminal-emulator -e bash -c "cd {script_dir} && {cmd_str}; echo; echo \\"Scan completed. Press Enter to close...\\"; read"',
                        # 2. Kali default (Xfce)
                        f'xfce4-terminal --title="HADES Scan: {scan_request.run_name}" -e "bash -c \\"cd {script_dir} && {cmd_str}; echo; echo \\\\\\"Scan completed. Press Enter to close...\\\\\\"; read\\""',
                        # 3. Kali default (KDE/Qt)
                        f'qterminal -e bash -c "cd {script_dir} && {cmd_str}; echo; echo \\"Scan completed. Press Enter to close...\\"; read"',
                        # 4. GNOME
                        f'gnome-terminal -- bash -c "cd {script_dir} && {cmd_str}; echo; echo \\"Scan completed. Press Enter to close...\\"; read"',
                        # 5. Generic X11
                        f'xterm -T "HADES Scan: {scan_request.run_name}" -e bash -c "cd {script_dir} && {cmd_str}; echo; echo \\"Scan completed. Press Enter to close...\\"; read"',
                        # 6. KDE
                        f'konsole -e bash -c "cd {script_dir} && {cmd_str}; echo; echo \\"Scan completed. Press Enter to close...\\"; read"',
                    ]
                    
                    success = False
                    for term_cmd in terminal_commands:
                        try:
                            subprocess.Popen(
                                term_cmd,
                                shell=True,
                                cwd=str(script_dir),
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                start_new_session=True
                            )
                            print(f"✓ Launched scan '{scan_request.run_name}' in new terminal window")
                            success = True
                            break
                        except Exception:
                            continue
                    
                    if not success:
                        # Fallback: run in background
                        subprocess.Popen(
                            cmd,
                            cwd=str(script_dir),
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            start_new_session=True
                        )
                        print(f"⚠ Could not open new terminal. Running scan '{scan_request.run_name}' in background...")
                
            except Exception as e:
                print(f"Error launching scan: {e}")
                import traceback
                traceback.print_exc()
        
        background_tasks.add_task(run_scan)
        
        return {"message": "Scan started", "scan_id": scan_request.run_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/scan/results")
async def get_scan_results():
    """Get list of scan results"""
    try:
        script_dir = Path(__file__).parent.parent.parent
        results_dir = script_dir / "agent_runs"
        
        results = []
        if results_dir.exists():
            for run_dir in results_dir.iterdir():
                if run_dir.is_dir():
                    # Calculate total size of directory
                    total_size = 0
                    try:
                        for file_path in run_dir.rglob('*'):
                            if file_path.is_file():
                                total_size += file_path.stat().st_size
                    except Exception:
                        total_size = 0
                    
                    # Import csv for checking vulnerabilities
                    import csv
                    
                    # Check if vulnerabilities exist
                    vulnerabilities_csv = run_dir / "vulnerabilities.csv"
                    vulnerabilities_dir = run_dir / "vulnerabilities"
                    has_findings = False
                    
                    if vulnerabilities_csv.exists():
                        try:
                            with open(vulnerabilities_csv, 'r', encoding='utf-8') as f:
                                reader = csv.reader(f)
                                next(reader, None)  # Skip header
                                if any(reader):  # Check if there are any rows
                                    has_findings = True
                        except Exception:
                            pass
                    elif vulnerabilities_dir.exists():
                        # Check if directory has any markdown files
                        has_findings = any(vulnerabilities_dir.glob("*.md"))
                    
                    # Load run configuration if exists
                    targets = []
                    user_instructions = ""
                    template = ""

                    run_config_file = run_dir / "run_config.json"
                    if run_config_file.exists() and run_config_file.is_file():
                        try:
                            with open(run_config_file, 'r', encoding='utf-8') as config_f:
                                run_config = json.load(config_f)
                                targets = run_config.get("targets", [])
                                user_instructions = run_config.get("user_instructions", "")
                                template = run_config.get("template", "")
                        except Exception:
                            pass

                    results.append({
                        "name": run_dir.name,
                        "path": str(run_dir),
                        "created": run_dir.stat().st_mtime,
                        "size": total_size,
                        "has_findings": has_findings,
                        "targets": targets,
                        "user_instructions": user_instructions,
                        "template": template
                    })
        
        results.sort(key=lambda x: x["created"], reverse=True)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/scan/results/{result_name}")
async def delete_scan_result(result_name: str):
    """Delete a scan result"""
    try:
        import shutil
        script_dir = Path(__file__).parent.parent.parent
        results_dir = script_dir / "agent_runs"
        result_path = results_dir / result_name
        
        if not result_path.exists() or not result_path.is_dir():
            raise HTTPException(status_code=404, detail="Scan result not found")
        
        # Security check: ensure we're only deleting from agent_runs directory
        if not str(result_path).startswith(str(results_dir)):
            raise HTTPException(status_code=403, detail="Invalid path")
        
        shutil.rmtree(result_path)
        return {"message": f"Scan result '{result_name}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/scan/results/{result_name}/export")
async def export_scan_result(result_name: str):
    """Export scan result to markdown"""
    try:
        script_dir = Path(__file__).parent.parent.parent
        results_dir = script_dir / "agent_runs"
        result_path = results_dir / result_name
        
        if not result_path.exists() or not result_path.is_dir():
            raise HTTPException(status_code=404, detail="Scan result not found")
        
        # Security check
        if not str(result_path).startswith(str(results_dir)):
            raise HTTPException(status_code=403, detail="Invalid path")
        
        # Generate markdown report
        markdown_content = generate_markdown_report(result_path)
        
        # Return as downloadable file
        from fastapi.responses import Response
        return Response(
            content=markdown_content,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f"attachment; filename={result_name}_report.md"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/scan/results/{result_name}/export-csv")
async def export_scan_result_csv(result_name: str):
    """Export vulnerabilities CSV file"""
    try:
        script_dir = Path(__file__).parent.parent.parent
        results_dir = script_dir / "agent_runs"
        result_path = results_dir / result_name
        
        if not result_path.exists() or not result_path.is_dir():
            raise HTTPException(status_code=404, detail="Scan result not found")
        
        # Security check
        if not str(result_path).startswith(str(results_dir)):
            raise HTTPException(status_code=403, detail="Invalid path")
        
        # Check for CSV file
        csv_file = result_path / "vulnerabilities.csv"
        if not csv_file.exists():
            raise HTTPException(
                status_code=404, 
                detail="No vulnerabilities CSV file found. This scan did not discover any vulnerabilities."
            )
        
        # Check if CSV has any data (not just header)
        try:
            import csv
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None)  # Skip header
                if not any(reader):
                    raise HTTPException(
                        status_code=404,
                        detail="No vulnerabilities found in CSV file. This scan did not discover any vulnerabilities."
                    )
        except HTTPException:
            raise
        except Exception:
            pass  # If we can't read it, let it through and let the download fail naturally
        
        # Return CSV file
        from fastapi.responses import FileResponse
        return FileResponse(
            path=str(csv_file),
            media_type="text/csv",
            filename=f"{result_name}_vulnerabilities.csv"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/scan/results/{result_name}/export-pdf")
async def export_scan_result_pdf(result_name: str):
    """Export scan result to PDF"""
    try:
        script_dir = Path(__file__).parent.parent.parent
        results_dir = script_dir / "agent_runs"
        result_path = results_dir / result_name
        
        if not result_path.exists() or not result_path.is_dir():
            raise HTTPException(status_code=404, detail="Scan result not found")
        
        # Security check
        if not str(result_path).startswith(str(results_dir)):
            raise HTTPException(status_code=403, detail="Invalid path")
        
        # Generate markdown report (always generates, even if no findings)
        try:
            markdown_content = generate_markdown_report(result_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")
        
        # Convert markdown to PDF
        try:
            pdf_content = generate_pdf_from_markdown(markdown_content, result_name)
        except ImportError:
            raise HTTPException(
                status_code=500, 
                detail="PDF generation requires weasyprint. Install with: pip install weasyprint"
            )
        except Exception as e:
            import traceback
            error_detail = str(e)
            print(f"Error generating PDF: {error_detail}")
            print(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {error_detail}")
        
        # Return as downloadable file
        from fastapi.responses import Response
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={result_name}_report.pdf"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def generate_pdf_from_markdown(markdown_content: str, report_name: str) -> bytes:
    """Convert markdown content to PDF using weasyprint"""
    try:
        import markdown
        from weasyprint import HTML, CSS
        from weasyprint.text.fonts import FontConfiguration
        from pathlib import Path
    except ImportError:
        raise ImportError("weasyprint and markdown are required for PDF generation")
    
    # Read favicon SVG and convert to JPG for logo
    # Check multiple locations to handle both dev and prod (.deb) builds
    base_root = Path(__file__).parent.parent.parent
    favicon_candidates = [
        base_root / "hades" / "web" / "frontend" / "dist" / "favicon.svg",
        base_root / "hades" / "web" / "frontend" / "public" / "favicon.svg",
        Path(__file__).parent.parent / "frontend" / "dist" / "favicon.svg"
    ]
    
    favicon_path = None
    for p in favicon_candidates:
        if p.exists():
            favicon_path = p
            break
            
    logo_jpg_base64 = ""
    if favicon_path:
        try:
            from PIL import Image
            import io
            import base64
            from cairosvg import svg2png
            
            # Convert SVG to PNG first (larger size for better quality)
            png_data = svg2png(url=str(favicon_path), output_width=800, output_height=800)
            
            # Open PNG and convert to JPG
            img = Image.open(io.BytesIO(png_data))
            # Convert RGBA to RGB if needed
            if img.mode == 'RGBA':
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[3])
                img = rgb_img
            
            # Save to bytes as JPG
            jpg_buffer = io.BytesIO()
            img.save(jpg_buffer, format='JPEG', quality=95)
            jpg_data = jpg_buffer.getvalue()
            
            # Convert to base64 for embedding
            logo_jpg_base64 = base64.b64encode(jpg_data).decode('utf-8')
        except ImportError:
            # Fallback: try to use weasyprint to render SVG directly
            try:
                from weasyprint import HTML as WeasyHTML
                import base64
                import io
                
                # Read SVG
                with open(favicon_path, 'r', encoding='utf-8') as f:
                    svg_content = f.read()
                
                # Render SVG to PNG using weasyprint
                svg_html = f'<html><body>{svg_content}</body></html>'
                png_bytes = WeasyHTML(string=svg_html).write_png()
                
                # Convert PNG to JPG
                img = Image.open(io.BytesIO(png_bytes))
                if img.mode == 'RGBA':
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    rgb_img.paste(img, mask=img.split()[3])
                    img = rgb_img
                
                # Resize to larger size for bigger logo
                img = img.resize((800, 800), Image.Resampling.LANCZOS)
                
                # Save as JPG
                jpg_buffer = io.BytesIO()
                img.save(jpg_buffer, format='JPEG', quality=95)
                logo_jpg_base64 = base64.b64encode(jpg_buffer.getvalue()).decode('utf-8')
            except Exception:
                # Final fallback: use SVG as base64
                try:
                    with open(favicon_path, 'r', encoding='utf-8') as f:
                        logo_svg = f.read()
                        import base64
                        # Note: This will be SVG, not JPG, but it's a fallback
                        logo_jpg_base64 = base64.b64encode(logo_svg.encode('utf-8')).decode('utf-8')
                except Exception:
                    pass
        except Exception as e:
            # If conversion fails, try weasyprint fallback
            try:
                from weasyprint import HTML as WeasyHTML
                import base64
                import io
                
                with open(favicon_path, 'r', encoding='utf-8') as f:
                    svg_content = f.read()
                
                svg_html = f'<html><body>{svg_content}</body></html>'
                png_bytes = WeasyHTML(string=svg_html).write_png()
                
                img = Image.open(io.BytesIO(png_bytes))
                if img.mode == 'RGBA':
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    rgb_img.paste(img, mask=img.split()[3])
                    img = rgb_img
                
                img = img.resize((800, 800), Image.Resampling.LANCZOS)
                
                jpg_buffer = io.BytesIO()
                img.save(jpg_buffer, format='JPEG', quality=95)
                logo_jpg_base64 = base64.b64encode(jpg_buffer.getvalue()).decode('utf-8')
            except Exception:
                pass
    
    # Convert markdown to HTML
    html_content = markdown.markdown(
        markdown_content,
        extensions=['tables', 'fenced_code', 'codehilite']
    )
    
    # Add CSS styling for professional PDF
    css_style = """
    @page {
        size: A4;
        margin: 2.5cm 2cm 3cm 2cm;
        @top-center {
            content: "HADES Security Penetration Test Report";
            font-size: 9pt;
            color: #666;
            font-weight: normal;
        }
        @bottom-right {
            content: "Page " counter(page) " of " counter(pages);
            font-size: 8pt;
            color: #999;
        }
        @bottom-left {
            content: "Copyright © 2025 TUANHADES";
            font-size: 7pt;
            color: #9CA3AF;
        }
    }
    
    @page:first {
        margin: 4cm 3cm;
        @top-center {
            content: "";
        }
        @bottom-left {
            content: "";
        }
        @bottom-right {
            content: "";
        }
    }
    
    /* Title page styling */
    .title-page {
        page: first;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 100%;
        text-align: center;
    }
    
    .title-page .logo {
        width: 300pt;
        height: 300pt;
        margin-bottom: 50pt;
        display: block;
        margin-left: auto;
        margin-right: auto;
        opacity: 0.85;
    }
    
    .title-page .logo img {
        width: 100%;
        height: 100%;
        object-fit: contain;
    }
    
    .title-page h1 {
        font-size: 36pt;
        margin: 30pt 0 15pt 0;
        border: none;
        padding: 0;
        color: #DC2626;
        font-weight: bold;
    }
    
    .title-page .subtitle {
        font-size: 16pt;
        color: #6B7280;
        margin-top: 10pt;
        margin-bottom: 50pt;
        font-weight: normal;
    }
    
    .title-page .report-info {
        margin-top: 50pt;
        font-size: 12pt;
        color: #4B5563;
        line-height: 2.2;
    }
    
    .title-page .report-info p {
        margin: 8pt 0;
    }
    
    /* Executive Summary - start on new page */
    a[id="executive-summary"] {
        page-break-before: always;
        display: block;
    }
    
    a[id="executive-summary"] + h2 {
        page-break-before: always;
        margin-top: 0;
    }
    
    /* Table of Contents styling */
    .toc {
        page-break-after: always;
    }
    
    .toc h2 {
        margin-top: 0;
        page-break-after: avoid;
    }
    
    .toc ul {
        list-style: none;
        padding-left: 0;
    }
    
    .toc li {
        margin: 8pt 0;
        padding-left: 0;
    }
    
    .toc li a {
        color: #1F2937;
        text-decoration: none;
        display: flex;
        justify-content: space-between;
    }
    
    .toc li a::after {
        content: leader('.') ' ' target-counter(attr(href), page);
        color: #9CA3AF;
    }
    
    /* List of Figures */
    .list-of-figures {
        page-break-after: always;
    }
    
    .list-of-figures h2 {
        margin-top: 0;
        page-break-after: avoid;
    }
    
    .list-of-figures ul {
        list-style: none;
        padding-left: 0;
    }
    
    .list-of-figures li {
        margin: 8pt 0;
        padding-left: 0;
    }
    
    .list-of-figures li a {
        color: #1F2937;
        text-decoration: none;
        display: flex;
        justify-content: space-between;
    }
    
    .list-of-figures li a::after {
        content: leader('.') ' ' target-counter(attr(href), page);
        color: #9CA3AF;
    }
    
    /* Figure styling */
    figure {
        margin: 20pt 0;
        page-break-inside: avoid;
    }
    
    figure img {
        max-width: 100%;
        height: auto;
        display: block;
        margin: 0 auto;
    }
    
    figcaption {
        text-align: center;
        font-size: 9pt;
        color: #6B7280;
        margin-top: 8pt;
        font-style: italic;
    }
    
    body {
        font-family: 'DejaVu Sans', Arial, sans-serif;
        font-size: 11pt;
        line-height: 1.7;
        color: #1F2937;
    }
    
    h1 {
        color: #DC2626;
        font-size: 28pt;
        margin-top: 0;
        margin-bottom: 20pt;
        border-bottom: 4px solid #DC2626;
        padding-bottom: 12pt;
        font-weight: bold;
        page-break-after: avoid;
    }
    
    h2 {
        color: #1F2937;
        font-size: 18pt;
        margin-top: 25pt;
        margin-bottom: 12pt;
        border-bottom: 2px solid #E5E7EB;
        padding-bottom: 8pt;
        font-weight: bold;
        page-break-after: avoid;
    }
    
    h3 {
        color: #374151;
        font-size: 14pt;
        margin-top: 18pt;
        margin-bottom: 10pt;
        font-weight: bold;
        page-break-after: avoid;
    }
    
    h4 {
        color: #4B5563;
        font-size: 12pt;
        margin-top: 15pt;
        margin-bottom: 8pt;
        font-weight: bold;
        page-break-after: avoid;
    }
    
    /* Table of Contents styling */
    h2:has(+ ul) {
        page-break-after: auto;
    }
    
    ul {
        margin: 12pt 0;
        padding-left: 20pt;
    }
    
    li {
        margin: 6pt 0;
        line-height: 1.6;
    }
    
    /* TOC specific */
    h2:contains("Table of Contents") + ul {
        list-style-type: decimal;
    }
    
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 15pt 0;
        font-size: 10pt;
    }
    
    th {
        background-color: #1F2937;
        color: white;
        padding: 8pt;
        text-align: left;
        font-weight: bold;
    }
    
    td {
        padding: 6pt;
        border: 1px solid #E5E7EB;
    }
    
    tr:nth-child(even) {
        background-color: #F9FAFB;
    }
    
    code {
        background-color: #F3F4F6;
        padding: 2pt 4pt;
        border-radius: 3pt;
        font-family: 'Courier New', monospace;
        font-size: 9pt;
    }
    
    pre {
        background-color: #1F2937;
        color: #F9FAFB;
        padding: 12pt;
        border-radius: 5pt;
        overflow-x: auto;
        font-size: 9pt;
        line-height: 1.4;
    }
    
    pre code {
        background-color: transparent;
        color: inherit;
        padding: 0;
    }
    
    blockquote {
        border-left: 4px solid #F59E0B;
        padding-left: 12pt;
        margin: 12pt 0;
        color: #6B7280;
        font-style: italic;
    }
    
    hr {
        border: none;
        border-top: 2px solid #E5E7EB;
        margin: 20pt 0;
    }
    
    strong {
        color: #1F2937;
    }
    
    a {
        color: #3B82F6;
        text-decoration: none;
    }
    
    /* Footer copyright */
    .copyright {
        text-align: center;
        font-size: 7pt;
        color: #9CA3AF;
        margin-top: 30pt;
        padding-top: 10pt;
        border-top: 1px solid #E5E7EB;
    }
    
    /* Professional spacing */
    p {
        margin: 8pt 0;
        text-align: justify;
    }
    
    /* Remove emoji styling if any */
    .emoji {
        display: none;
    }
    """
    
    # Wrap HTML with proper structure and add title page
    from datetime import datetime
    import base64
    title_page_html = ""
    if logo_jpg_base64:
        # Determine if it's JPG or SVG based on the data
        try:
            decoded = base64.b64decode(logo_jpg_base64[:200])
            if b'<svg' in decoded or b'svg' in decoded[:50].lower():
                # It's SVG, use SVG data URI
                img_src = f"data:image/svg+xml;base64,{logo_jpg_base64}"
            else:
                # It's JPG
                img_src = f"data:image/jpeg;base64,{logo_jpg_base64}"
        except Exception:
            # Default to JPG
            img_src = f"data:image/jpeg;base64,{logo_jpg_base64}"
        
        title_page_html = f"""
        <div class="title-page">
            <div class="logo">
                <img src="{img_src}" alt="HADES Logo" />
            </div>
            <h1>HADES</h1>
            <div class="subtitle">Security Penetration Test Report Powered by AI</div>
        </div>
        """
    
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{report_name} - Security Report</title>
    </head>
    <body>
        {title_page_html}
        {html_content}
    </body>
    </html>
    """
    
    # Generate PDF
    font_config = FontConfiguration()
    html_doc = HTML(string=full_html)
    css_doc = CSS(string=css_style, font_config=font_config)
    
    pdf_bytes = html_doc.write_pdf(stylesheets=[css_doc], font_config=font_config)
    
    return pdf_bytes


def generate_markdown_report(result_path: Path) -> str:
    """Generate professional markdown report from scan results"""
    import json
    import csv
    from datetime import datetime
    
    md_lines = []
    
    # Title Page (will be handled by PDF generator with logo)
    # Skip title in markdown as it's handled in PDF template
    
    # Executive Summary (will be added to TOC later)
    md_lines.append('<a id="executive-summary"></a>')
    md_lines.append("## Executive Summary")
    md_lines.append("")
    md_lines.append("This report contains the findings from a comprehensive security penetration test conducted using the HADES Security Testing Framework.")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    
    toc_items = []
    
    # Add TOC items
    toc_items.append(("Executive Summary", "executive-summary"))
    toc_items.append(("Scan Information", "scan-information"))
    
    # Scan metadata
    md_lines.append("")
    md_lines.append('<a id="scan-information"></a>')
    md_lines.append("## Scan Information")
    md_lines.append("")
    md_lines.append("| Property | Value |")
    md_lines.append("|----------|-------|")
    md_lines.append(f"| Scan Name | `{result_path.name}` |")
    md_lines.append(f"| Scan Directory | `{result_path}` |")
    md_lines.append(f"| Scan Date | {datetime.fromtimestamp(result_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')} |")
    md_lines.append("")
    
    # Check for penetration test report
    penetration_report = result_path / "penetration_test_report.md"
    has_penetration_report = penetration_report.exists()
    
    if has_penetration_report:
        toc_items.append(("Detailed Penetration Test Findings", "penetration-findings"))
        md_lines.append("")
        md_lines.append('<a id="penetration-findings"></a>')
        md_lines.append("## Detailed Penetration Test Findings")
        md_lines.append("")
        try:
            with open(penetration_report, 'r', encoding='utf-8') as f:
                content = f.read()
                # Remove the first header if it exists
                if content.startswith("#"):
                    lines = content.split("\n")
                    # Skip first header line
                    content = "\n".join(lines[1:]).strip()
                md_lines.append(content)
                md_lines.append("")
        except Exception as e:
            md_lines.append(f"*Error reading penetration test report: {str(e)}*")
            md_lines.append("")
        md_lines.append("---")
        md_lines.append("")
    
    # Check for vulnerabilities
    vulnerabilities_dir = result_path / "vulnerabilities"
    vulnerabilities_csv = result_path / "vulnerabilities.csv"
    
    has_vulnerabilities = False
    vulnerabilities = []
    
    if vulnerabilities_csv.exists():
        try:
            with open(vulnerabilities_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    vulnerabilities.append(row)
            has_vulnerabilities = len(vulnerabilities) > 0
        except Exception as e:
            md_lines.append(f"*Error reading vulnerabilities CSV: {str(e)}*")
            md_lines.append("")
    elif vulnerabilities_dir.exists():
        # Check if directory has any markdown files
        vuln_files = list(vulnerabilities_dir.glob("*.md"))
        has_vulnerabilities = len(vuln_files) > 0
    
    if has_vulnerabilities:
        toc_items.append(("Vulnerabilities Discovered", "vulnerabilities"))
        md_lines.append("")
        md_lines.append('<a id="vulnerabilities"></a>')
        md_lines.append("## Vulnerabilities Discovered")
        md_lines.append("")
        
        # Count by severity
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        for vuln in vulnerabilities:
            severity = vuln.get("severity", "").upper()
            if severity in severity_counts:
                severity_counts[severity] += 1
        
        total_vulns = len(vulnerabilities)
        
        # Vulnerability Summary Table
        md_lines.append("### Vulnerability Summary")
        md_lines.append("")
        md_lines.append("| Severity | Count |")
        md_lines.append("|----------|-------|")
        md_lines.append(f"| **CRITICAL** | **{severity_counts['CRITICAL']}** |")
        md_lines.append(f"| **HIGH** | **{severity_counts['HIGH']}** |")
        md_lines.append(f"| **MEDIUM** | **{severity_counts['MEDIUM']}** |")
        md_lines.append(f"| **LOW** | **{severity_counts['LOW']}** |")
        md_lines.append(f"| **INFO** | **{severity_counts['INFO']}** |")
        md_lines.append(f"| **TOTAL** | **{total_vulns}** |")
        md_lines.append("")
        
        if total_vulns > 0:
            md_lines.append(f"> **WARNING:** {total_vulns} vulnerability/vulnerabilities discovered during this security assessment.")
            md_lines.append("")
        
        # List all vulnerabilities
        if vulnerabilities:
            md_lines.append("### Detailed Vulnerability Analysis")
            md_lines.append("")
            
            for idx, vuln in enumerate(vulnerabilities, 1):
                severity = vuln.get('severity', '').upper()
                
                md_lines.append(f"#### VULN-{idx:04d}: {vuln.get('title', 'Unknown')}")
                md_lines.append("")
                md_lines.append("| Property | Value |")
                md_lines.append("|----------|-------|")
                md_lines.append(f"| **Vulnerability ID** | `{vuln.get('id', 'N/A')}` |")
                md_lines.append(f"| **Severity** | **{severity}** |")
                md_lines.append(f"| **Discovery Date** | {vuln.get('timestamp', 'N/A')} |")
                md_lines.append("")
                
                # Try to read detailed content from markdown file
                vuln_file = result_path / vuln.get('file', '')
                if vuln_file.exists():
                    try:
                        with open(vuln_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Remove the header if it exists
                            lines = content.split("\n")
                            # Skip first header line if it starts with #
                            if lines and lines[0].startswith("#"):
                                content = "\n".join(lines[1:]).strip()
                            md_lines.append(content)
                    except Exception as e:
                        md_lines.append(f"*Error reading vulnerability details: {str(e)}*")
                
                md_lines.append("")
                md_lines.append("---")
                md_lines.append("")
        else:
            md_lines.append("*No vulnerabilities found in CSV index.*")
            md_lines.append("")
        
        # If vulnerabilities directory exists but no CSV, list files
        if vulnerabilities_dir.exists() and not vulnerabilities:
            vuln_files = list(vulnerabilities_dir.glob("*.md"))
            if vuln_files:
                md_lines.append(f"### Vulnerability Files ({len(vuln_files)} found)")
                md_lines.append("")
                for vuln_file in sorted(vuln_files):
                    md_lines.append(f"#### {vuln_file.name}")
                    md_lines.append("")
                    try:
                        with open(vuln_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            md_lines.append(content)
                    except Exception as e:
                        md_lines.append(f"*Error reading file: {str(e)}*")
                    md_lines.append("")
                    md_lines.append("---")
                    md_lines.append("")
        
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")
    else:
        # No vulnerabilities found
        toc_items.append(("No Vulnerabilities Found", "no-vulnerabilities"))
        md_lines.append("")
        md_lines.append('<a id="no-vulnerabilities"></a>')
        md_lines.append("## No Vulnerabilities Found")
        md_lines.append("")
        md_lines.append("**Congratulations!** This security assessment did not discover any vulnerabilities.")
        md_lines.append("")
        md_lines.append("The target application or system appears to be secure based on the tests performed. However, please note that:")
        md_lines.append("")
        md_lines.append("- Security testing is an ongoing process")
        md_lines.append("- New vulnerabilities may be discovered as the application evolves")
        md_lines.append("- Regular security assessments are recommended")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")
    
    # Find and process other result files (excluding vulnerabilities and penetration report)
    toc_items.append(("Additional Scan Results", "additional-results"))
    
    md_lines.append("")
    md_lines.append('<a id="additional-results"></a>')
    md_lines.append("## Additional Scan Results")
    md_lines.append("")
    
    excluded_paths = {
        "vulnerabilities",
        "penetration_test_report.md",
        "vulnerabilities.csv"
    }
    
    result_files = []
    for file_path in result_path.rglob("*"):
        if file_path.is_file():
            relative_path = file_path.relative_to(result_path)
            # Skip vulnerabilities directory and penetration report
            if relative_path.parts[0] not in excluded_paths and relative_path.name not in excluded_paths:
                result_files.append(file_path)
    
    if not result_files:
        md_lines.append("No additional result files found.")
        md_lines.append("")
    else:
        md_lines.append(f"Found {len(result_files)} additional file(s):")
        md_lines.append("")
        
        for file_path in sorted(result_files):
            relative_path = file_path.relative_to(result_path)
            md_lines.append(f"### {relative_path}")
            md_lines.append("")
            
            # Try to read and format content
            try:
                if file_path.suffix.lower() == '.json':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        md_lines.append("```json")
                        md_lines.append(json.dumps(data, indent=2, ensure_ascii=False))
                        md_lines.append("```")
                elif file_path.suffix.lower() in ['.txt', '.log', '.md']:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if content.strip():
                            md_lines.append("```")
                            md_lines.append(content)
                            md_lines.append("```")
                        else:
                            md_lines.append("*File is empty*")
                else:
                    # Try to read as text
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(5000)  # Limit to first 5000 chars
                        if content.strip():
                            md_lines.append("```")
                            md_lines.append(content)
                            if len(content) >= 5000:
                                md_lines.append("\n... (truncated)")
                            md_lines.append("```")
                        else:
                            md_lines.append(f"*Binary file or empty*")
            except Exception as e:
                md_lines.append(f"*Error reading file: {str(e)}*")
            
            md_lines.append("")
            md_lines.append("---")
            md_lines.append("")
    
    # Add Report Summary to TOC
    toc_items.append(("Report Summary", "report-summary"))
    toc_items.append(("List of Figures", "list-of-figures"))
    toc_items.append(("Appendix", "appendix"))
    
    # Insert Table of Contents after Executive Summary
    # Find Executive Summary section end
    exec_summary_end = None
    for i, line in enumerate(md_lines):
        if line.startswith("---") and i > 0 and "Executive Summary" in md_lines[i-5:i]:
            exec_summary_end = i
            break
    
    if exec_summary_end is None:
        # Fallback: find first "---" after Executive Summary
        for i, line in enumerate(md_lines):
            if '<a id="executive-summary"></a>' in md_lines[max(0, i-3):i]:
                if line.startswith("---"):
                    exec_summary_end = i
                    break
    
    if exec_summary_end is not None:
        # Insert TOC after Executive Summary
        toc_lines = [
            "",
            '<div class="toc">',
            "## Table of Contents",
            "",
            "<ul>"
        ]
        for i, (item_name, item_id) in enumerate(toc_items, 1):
            toc_lines.append(f'<li><a href="#{item_id}">{i}. {item_name}</a></li>')
        toc_lines.extend([
            "</ul>",
            "</div>",
            "",
            "---",
            ""
        ])
        md_lines = md_lines[:exec_summary_end+1] + toc_lines + md_lines[exec_summary_end+1:]
    
    # Summary
    md_lines.append('<a id="report-summary"></a>')
    md_lines.append("## Report Summary")
    md_lines.append("")
    md_lines.append("### Key Findings")
    md_lines.append("")
    md_lines.append("| Metric | Value |")
    md_lines.append("|--------|-------|")
    md_lines.append(f"| Scan Name | `{result_path.name}` |")
    md_lines.append(f"| Scan Date | {datetime.fromtimestamp(result_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')} |")
    if has_vulnerabilities and len(vulnerabilities) > 0:
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        for vuln in vulnerabilities:
            severity = vuln.get("severity", "").upper()
            if severity in severity_counts:
                severity_counts[severity] += 1
        md_lines.append(f"| Total Vulnerabilities | **{len(vulnerabilities)}** |")
        md_lines.append(f"| Critical | {severity_counts['CRITICAL']} |")
        md_lines.append(f"| High | {severity_counts['HIGH']} |")
        md_lines.append(f"| Medium | {severity_counts['MEDIUM']} |")
        md_lines.append(f"| Low | {severity_counts['LOW']} |")
        md_lines.append(f"| Info | {severity_counts['INFO']} |")
    else:
        md_lines.append(f"| Total Vulnerabilities | **0** |")
    md_lines.append(f"| Additional Files | {len(result_files)} |")
    md_lines.append("")
    
    # Recommendations
    if has_vulnerabilities and len(vulnerabilities) > 0:
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        for vuln in vulnerabilities:
            severity = vuln.get("severity", "").upper()
            if severity in severity_counts:
                severity_counts[severity] += 1
        
        if severity_counts['CRITICAL'] + severity_counts['HIGH'] > 0:
            md_lines.append("### Immediate Action Required")
            md_lines.append("")
            md_lines.append("**Critical and High severity vulnerabilities require immediate attention.**")
            md_lines.append("")
            md_lines.append("1. Review all critical and high severity findings")
            md_lines.append("2. Prioritize remediation based on business impact")
            md_lines.append("3. Implement temporary mitigations if immediate fixes are not possible")
            md_lines.append("4. Schedule security patches and updates")
            md_lines.append("")
    
    # Add List of Figures placeholder
    md_lines.append("")
    md_lines.append('<a id="list-of-figures"></a>')
    md_lines.append('<div class="list-of-figures">')
    md_lines.append("## List of Figures")
    md_lines.append("")
    md_lines.append("<ul>")
    md_lines.append("<li>No figures available in this report.</li>")
    md_lines.append("</ul>")
    md_lines.append("</div>")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    md_lines.append('<a id="appendix"></a>')
    md_lines.append("## Appendix")
    md_lines.append("")
    md_lines.append("### Report Metadata")
    md_lines.append("")
    md_lines.append(f"- **Report Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md_lines.append(f"- **Report Location:** `{result_path}`")
    if vulnerabilities_dir.exists():
        md_lines.append(f"- **Vulnerabilities Directory:** `{vulnerabilities_dir}`")
    if penetration_report.exists():
        md_lines.append(f"- **Penetration Test Report:** `{penetration_report}`")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    md_lines.append("**Report generated by [HADES Security Testing Framework](https://github.com/hades-framework)**")
    md_lines.append("")
    md_lines.append("*This report contains sensitive security information and should be handled with appropriate confidentiality.*")
    md_lines.append("")
    
    return "\n".join(md_lines)


# ============================================================================
# Activity & Statistics API
# ============================================================================

@app.get("/api/activity")
async def get_activity():
    """Get activity statistics (scans over time)"""
    try:
        from datetime import datetime, timedelta
        script_dir = Path(__file__).parent.parent.parent
        results_dir = script_dir / "agent_runs"
        
        # Get last 30 days of activity
        activity_data = []
        if results_dir.exists():
            for run_dir in results_dir.iterdir():
                if run_dir.is_dir():
                    created_time = datetime.fromtimestamp(run_dir.stat().st_mtime)
                    activity_data.append({
                        "date": created_time.strftime("%Y-%m-%d"),
                        "timestamp": created_time.timestamp(),
                        "count": 1
                    })
        
        # Group by date
        date_counts = {}
        for item in activity_data:
            date = item["date"]
            date_counts[date] = date_counts.get(date, 0) + 1
        
        # Create last 30 days data
        today = datetime.now().date()
        chart_data = []
        for i in range(29, -1, -1):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            chart_data.append({
                "date": date,
                "scans": date_counts.get(date, 0)
            })
        
        return {"activity": chart_data, "total_scans": len(activity_data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vulnerabilities")
async def get_vulnerabilities():
    """Get vulnerability statistics from CSV files only"""
    try:
        import csv
        script_dir = Path(__file__).parent.parent.parent
        results_dir = script_dir / "agent_runs"
        
        vulnerabilities = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0
        }
        
        # Use set to track unique vulnerabilities by ID
        seen_vulnerabilities = set()
        vulnerability_details = []
        
        if results_dir.exists():
            for run_dir in results_dir.iterdir():
                if run_dir.is_dir():
                    # Only read from vulnerabilities.csv file
                    csv_file = run_dir / "vulnerabilities.csv"
                    if csv_file.exists() and csv_file.is_file():
                        try:
                            with open(csv_file, 'r', encoding='utf-8', newline='') as f:
                                reader = csv.DictReader(f)
                                for row in reader:
                                    # Get vulnerability ID for deduplication
                                    vuln_id = row.get('id', '').strip()
                                    title = row.get('title', '').strip()
                                    severity = row.get('severity', '').strip().lower()
                                    timestamp = row.get('timestamp', '').strip()
                                    file_path = row.get('file', '').strip()
                                    
                                    # Skip if missing essential data
                                    if not vuln_id or not title or not severity:
                                        continue
                                    
                                    # Create unique key: run_name + vuln_id to prevent skipping same IDs from different scans
                                    unique_key = f"{run_dir.name}_{vuln_id}" if vuln_id else f"{run_dir.name}_{title}_{severity}"
                                    
                                    # Skip duplicates
                                    if unique_key in seen_vulnerabilities:
                                        continue
                                    
                                    seen_vulnerabilities.add(unique_key)
                                    
                                    # Extract vulnerability type from ID or title
                                    # ID format is usually like: sql_injection_001, xss_002, etc.
                                    vuln_type = "Unknown"
                                    if vuln_id:
                                        # Extract type from ID (e.g., "sql_injection_001" -> "SQL Injection")
                                        parts = vuln_id.split('_')
                                        if len(parts) > 1:
                                            # Remove numeric suffix and join
                                            type_parts = [p for p in parts if not p.isdigit()]
                                            if type_parts:
                                                vuln_type = ' '.join(word.capitalize() for word in type_parts)
                                    elif title:
                                        # Try to extract from title
                                        vuln_type = title.split('-')[0].strip() if '-' in title else title.split()[0].strip()
                                    
                                    # Count by severity
                                    if severity in vulnerabilities:
                                        vulnerabilities[severity] += 1
                                    elif severity:
                                        # Handle case variations
                                        severity_lower = severity.lower()
                                        if severity_lower in vulnerabilities:
                                            vulnerabilities[severity_lower] += 1
                                        else:
                                            vulnerabilities["info"] += 1
                                    
                                    # Read vulnerability content from markdown file if it exists
                                    content = ""
                                    if file_path:
                                        full_vuln_path = run_dir / file_path
                                        if full_vuln_path.exists() and full_vuln_path.is_file():
                                            try:
                                                with open(full_vuln_path, 'r', encoding='utf-8') as vuln_f:
                                                    content = vuln_f.read()
                                            except Exception:
                                                pass

                                    # Add to details
                                    vulnerability_details.append({
                                        "id": vuln_id,
                                        "title": title,
                                        "type": vuln_type,
                                        "severity": severity,
                                        "timestamp": timestamp,
                                        "file": file_path,
                                        "scan": run_dir.name,
                                        "content": content
                                    })
                        except Exception as e:
                            # Skip CSV files that can't be read
                            continue
        
        # Sort by severity priority (critical > high > medium > low > info)
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        vulnerability_details.sort(key=lambda x: (
            severity_order.get(x.get("severity", "").lower(), 99),
            x.get("timestamp", ""),
            x.get("title", "")
        ))
        
        return {
            "summary": vulnerabilities,
            "total": sum(vulnerabilities.values()),
            "details": vulnerability_details
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# System Info API
# ============================================================================

@app.get("/api/system/info")
async def get_system_info():
    """Get system information"""
    try:
        script_dir = Path(__file__).parent.parent.parent
        
        info = {
            "version": get_hades_version(),
            "author": "Joel Indra - Anonre",
            "project_path": str(script_dir),
            "templates_path": str(get_template_dir()),
            "results_path": str(script_dir / "agent_runs")
        }
        
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Notification Functions
# ============================================================================

def send_scan_notification(scan_name: str, results_dir: Path):
    """Send notification with all files from scan results to Telegram and Discord"""
    try:
        script_dir = Path(__file__).parent.parent.parent
        config_dir = script_dir / "config"
        
        # Get notification settings
        telegram_token_file = config_dir / "telegram_token.txt"
        telegram_chat_id_file = config_dir / "telegram_chat_id.txt"
        discord_webhook_file = config_dir / "discord_webhook.txt"
        config_file = config_dir / "config.yaml"
        
        telegram_enabled = False
        telegram_token = None
        telegram_chat_id = None
        telegram_send_files = True
        telegram_max_file_size = 50 * 1024 * 1024  # 50MB default
        
        discord_enabled = False
        discord_webhook = None
        
        # Load settings from config.yaml
        if config_file.exists():
            try:
                import yaml
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    if config.get('notifications'):
                        if config['notifications'].get('telegram'):
                            telegram_config = config['notifications']['telegram']
                            telegram_enabled = telegram_config.get('enabled', False)
                            telegram_send_files = telegram_config.get('send_files', True)
                            max_size_str = telegram_config.get('max_file_size', '50M')
                            # Parse size (e.g., "50M" -> 50 * 1024 * 1024)
                            if max_size_str.endswith('M'):
                                telegram_max_file_size = int(max_size_str[:-1]) * 1024 * 1024
                            elif max_size_str.endswith('K'):
                                telegram_max_file_size = int(max_size_str[:-1]) * 1024
                            else:
                                telegram_max_file_size = int(max_size_str)
                        
                        if config['notifications'].get('discord'):
                            discord_config = config['notifications']['discord']
                            discord_enabled = discord_config.get('enabled', False)
            except Exception as e:
                print(f"Error reading config.yaml: {e}")
        
        # Override with text files if they exist
        if telegram_token_file.exists() and telegram_chat_id_file.exists():
            try:
                telegram_token = telegram_token_file.read_text(encoding='utf-8').strip()
                telegram_chat_id = telegram_chat_id_file.read_text(encoding='utf-8').strip()
                if telegram_token and telegram_chat_id:
                    telegram_enabled = True
            except Exception as e:
                print(f"Error reading Telegram credentials: {e}")
        
        if discord_webhook_file.exists():
            try:
                discord_webhook = discord_webhook_file.read_text(encoding='utf-8').strip()
                if discord_webhook:
                    discord_enabled = True
            except Exception as e:
                print(f"Error reading Discord webhook: {e}")
        
        # Collect all files from results directory
        if not results_dir.exists():
            print(f"Results directory not found: {results_dir}")
            return
        
        files_to_send = []
        for file_path in results_dir.rglob('*'):
            if file_path.is_file():
                # Skip very large files or system files
                if file_path.stat().st_size > telegram_max_file_size:
                    continue
                files_to_send.append(file_path)
        
        if not files_to_send:
            print(f"No files found in results directory: {results_dir}")
            return
        
        # Prepare summary message
        summary_message = f"🔔 **HADES Scan Completed**\n\n"
        summary_message += f"**Scan Name:** `{scan_name}`\n"
        summary_message += f"**Total Files:** {len(files_to_send)}\n"
        summary_message += f"**Results Directory:** `{results_dir.name}`\n\n"
        
        # Send Telegram notification
        if telegram_enabled and telegram_token and telegram_chat_id:
            try:
                import requests
                
                # Send summary message first
                summary_text = summary_message.replace('**', '*').replace('`', '`')
                requests.post(
                    f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                    json={
                        "chat_id": telegram_chat_id,
                        "text": summary_text,
                        "parse_mode": "Markdown"
                    },
                    timeout=10
                )
                
                # Send files if enabled
                if telegram_send_files:
                    for file_path in files_to_send:
                        try:
                            file_size = file_path.stat().st_size
                            if file_size > telegram_max_file_size:
                                continue
                            
                            with open(file_path, 'rb') as f:
                                files = {'document': (file_path.name, f, 'application/octet-stream')}
                                data = {
                                    'chat_id': telegram_chat_id,
                                    'caption': f"📄 {file_path.relative_to(results_dir)}"
                                }
                                requests.post(
                                    f"https://api.telegram.org/bot{telegram_token}/sendDocument",
                                    files=files,
                                    data=data,
                                    timeout=30
                                )
                        except Exception as e:
                            print(f"Error sending file {file_path} to Telegram: {e}")
                            continue
                
                print(f"Telegram notification sent for scan: {scan_name}")
            except Exception as e:
                print(f"Error sending Telegram notification: {e}")
        
        # Send Discord notification
        if discord_enabled and discord_webhook:
            try:
                import requests
                
                # Discord has 25MB file size limit
                discord_max_size = 25 * 1024 * 1024
                
                # Send summary message first
                summary_embed = {
                    "title": "🔔 HADES Scan Completed",
                    "description": f"**Scan Name:** `{scan_name}`\n**Total Files:** {len(files_to_send)}\n**Results Directory:** `{results_dir.name}`",
                    "color": 0x5865F2,  # Discord blue
                    "timestamp": datetime.now().isoformat()
                }
                
                requests.post(
                    discord_webhook,
                    json={
                        "embeds": [summary_embed]
                    },
                    timeout=10
                )
                
                # Discord webhooks don't support file uploads directly
                # Send file list as text instead
                if files_to_send:
                    file_list = "\n".join([f"📄 `{file_path.relative_to(results_dir)}`" for file_path in files_to_send[:20]])  # Limit to 20 files
                    if len(files_to_send) > 20:
                        file_list += f"\n\n... and {len(files_to_send) - 20} more files"
                    
                    file_list_embed = {
                        "title": "📁 Files Generated",
                        "description": file_list,
                        "color": 0x5865F2,
                    }
                    
                    requests.post(
                        discord_webhook,
                        json={
                            "embeds": [file_list_embed]
                        },
                        timeout=10
                    )
                
                print(f"Discord notification sent for scan: {scan_name}")
            except Exception as e:
                print(f"Error sending Discord notification: {e}")
    
    except Exception as e:
        print(f"Error in send_scan_notification: {e}")
        import traceback
        traceback.print_exc()


# ============================================================================
# Settings API (Shell Module Mode Notifications)
# ============================================================================

class NotificationSettings(BaseModel):
    telegram: Optional[Dict[str, Any]] = None
    discord: Optional[Dict[str, Any]] = None


@app.get("/api/settings")
async def get_settings():
    """Get notification settings for Shell Module Mode"""
    try:
        script_dir = Path(__file__).parent.parent.parent
        config_file = script_dir / "config" / "config.yaml"
        telegram_token_file = script_dir / "config" / "telegram_token.txt"
        telegram_chat_id_file = script_dir / "config" / "telegram_chat_id.txt"
        discord_webhook_file = script_dir / "config" / "discord_webhook.txt"
        
        settings = {
            "telegram": {
                "enabled": False,
                "token": "",
                "chat_id": ""
            },
            "discord": {
                "enabled": False,
                "webhook": ""
            }
        }
        
        # Load from config.yaml if exists
        if config_file.exists():
            try:
                import yaml
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    if config.get('notifications'):
                        if config['notifications'].get('telegram'):
                            settings['telegram'] = config['notifications']['telegram']
                        if config['notifications'].get('discord'):
                            settings['discord'] = config['notifications']['discord']
            except Exception as e:
                print(f"Error reading config.yaml: {e}")
        
        # Override with text files if they exist (for security)
        if telegram_token_file.exists():
            try:
                settings['telegram']['token'] = telegram_token_file.read_text(encoding='utf-8').strip()
            except:
                pass
        
        if telegram_chat_id_file.exists():
            try:
                settings['telegram']['chat_id'] = telegram_chat_id_file.read_text(encoding='utf-8').strip()
            except:
                pass
        
        if discord_webhook_file.exists():
            try:
                settings['discord']['webhook'] = discord_webhook_file.read_text(encoding='utf-8').strip()
            except:
                pass
        
        return settings
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/settings")
async def save_settings(settings: NotificationSettings):
    """Save notification settings for Shell Module Mode"""
    try:
        script_dir = Path(__file__).parent.parent.parent
        config_dir = script_dir / "config"
        config_dir.mkdir(exist_ok=True)
        
        config_file = config_dir / "config.yaml"
        telegram_token_file = config_dir / "telegram_token.txt"
        telegram_chat_id_file = config_dir / "telegram_chat_id.txt"
        discord_webhook_file = config_dir / "discord_webhook.txt"
        
        # Load existing config
        config = {}
        if config_file.exists():
            try:
                import yaml
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
            except:
                pass
        
        # Initialize notifications section
        if 'notifications' not in config:
            config['notifications'] = {}
        
        # Update Telegram settings
        if settings.telegram:
            config['notifications']['telegram'] = {
                'enabled': settings.telegram.get('enabled', False),
                'token': '',  # Don't store in YAML for security
                'chat_id': '',  # Don't store in YAML for security
                'send_summary': settings.telegram.get('send_summary', True),
                'send_files': settings.telegram.get('send_files', True),
                'max_file_size': settings.telegram.get('max_file_size', '50M')
            }
            
            # Save sensitive data to text files
            if settings.telegram.get('token'):
                telegram_token_file.write_text(settings.telegram['token'], encoding='utf-8')
                telegram_token_file.chmod(0o600)  # Read/write for owner only
            
            if settings.telegram.get('chat_id'):
                telegram_chat_id_file.write_text(settings.telegram['chat_id'], encoding='utf-8')
                telegram_chat_id_file.chmod(0o600)
        
        # Update Discord settings
        if settings.discord:
            config['notifications']['discord'] = {
                'enabled': settings.discord.get('enabled', False),
                'webhook': ''  # Don't store in YAML for security
            }
            
            # Save sensitive data to text file
            if settings.discord.get('webhook'):
                discord_webhook_file.write_text(settings.discord['webhook'], encoding='utf-8')
                discord_webhook_file.chmod(0o600)
        
        # Save config.yaml
        try:
            import yaml
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            print(f"Error writing config.yaml: {e}")
        
        return {"message": "Settings saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/settings/test-notification")
async def test_notification(data: Dict[str, Any]):
    """Test notification (Telegram or Discord)"""
    try:
        notification_type = data.get('type')
        script_dir = Path(__file__).parent.parent.parent
        config_dir = script_dir / "config"
        
        if notification_type == 'telegram':
            token_file = config_dir / "telegram_token.txt"
            chat_id_file = config_dir / "telegram_chat_id.txt"
            
            if not token_file.exists() or not chat_id_file.exists():
                raise HTTPException(status_code=400, detail="Telegram token or chat ID not configured")
            
            token = token_file.read_text(encoding='utf-8').strip()
            chat_id = chat_id_file.read_text(encoding='utf-8').strip()
            
            if not token or not chat_id:
                raise HTTPException(status_code=400, detail="Telegram token or chat ID is empty")
            
            # Send test message
            import requests
            test_message = "🔔 HADES Test Notification\n\nThis is a test message from HADES Security Testing Framework."
            response = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": test_message,
                    "parse_mode": "Markdown"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return {"message": "Test notification sent successfully"}
            else:
                raise HTTPException(status_code=400, detail=f"Failed to send: {response.text}")
        
        elif notification_type == 'discord':
            webhook_file = config_dir / "discord_webhook.txt"
            
            if not webhook_file.exists():
                raise HTTPException(status_code=400, detail="Discord webhook not configured")
            
            webhook = webhook_file.read_text(encoding='utf-8').strip()
            
            if not webhook:
                raise HTTPException(status_code=400, detail="Discord webhook is empty")
            
            # Send test message
            import requests
            test_message = {
                "content": "🔔 **HADES Test Notification**",
                "embeds": [{
                    "title": "Test Message",
                    "description": "This is a test message from HADES Security Testing Framework.",
                    "color": 0x5865F2,  # Discord blue
                    "timestamp": str(datetime.now().isoformat())
                }]
            }
            
            response = requests.post(webhook, json=test_message, timeout=10)
            
            if response.status_code in [200, 204]:
                return {"message": "Test notification sent successfully"}
            else:
                raise HTTPException(status_code=400, detail=f"Failed to send: {response.text}")
        
        else:
            raise HTTPException(status_code=400, detail="Invalid notification type")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Frontend Routes (must be last to allow API routes to be matched first)
# ============================================================================

@app.get("/")
async def serve_index():
    """Serve frontend index.html"""
    index_path = frontend_path / "index.html"
    if index_path.exists() and index_path.is_file():
        return FileResponse(str(index_path))
    
    # If frontend not built, return a helpful message
    return JSONResponse({
        "message": "HADES Web Interface",
        "status": "running",
        "api": "http://localhost:9656/api",
        "note": "Frontend not built. Run: cd hades/web/frontend && npm install && npm run build",
        "api_docs": "http://localhost:9656/docs"
    })


@app.get("/favicon.svg")
async def serve_favicon():
    """Serve favicon"""
    favicon_path = frontend_path.parent / "public" / "favicon.svg"
    if favicon_path.exists():
        return FileResponse(str(favicon_path), media_type="image/svg+xml")
    # Fallback to dist if public doesn't exist
    favicon_path = frontend_path / "favicon.svg"
    if favicon_path.exists():
        return FileResponse(str(favicon_path), media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="Favicon not found")


@app.get("/{full_path:path}")
async def serve_spa_routes(full_path: str):
    """Serve frontend for SPA routes (templates, api-config, etc.)"""
    # Don't serve API routes (shouldn't reach here if API routes are defined first)
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    
    # Don't serve assets (should be handled by mount, but safety check)
    if full_path.startswith("assets/") or full_path.startswith("static/"):
        raise HTTPException(status_code=404, detail="Not found")
    
    # Serve index.html for SPA routing
    index_path = frontend_path / "index.html"
    if index_path.exists() and index_path.is_file():
        return FileResponse(str(index_path))
    
    raise HTTPException(status_code=404, detail="Not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9656)

