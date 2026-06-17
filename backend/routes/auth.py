from fastapi import APIRouter, HTTPException, Depends, Header
from datetime import datetime, timedelta
from typing import Optional
from bson import ObjectId
import logging

from database.mongo import db
from auth.models import UserRegister, UserLogin, UserResponse, ChangePassword
from auth.security import (
    Token,
    verify_password,
    get_password_hash,
    create_access_token,
    decode_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

logger = logging.getLogger(__name__)
router = APIRouter()

users_collection = db["users"]


async def get_current_user(authorization: Optional[str] = Header(None)):
    """Dependency to get current user from JWT token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        scheme, token = authorization.split(" ")
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token format")
    
    token_data = decode_token(token)
    if token_data is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user = users_collection.find_one({"email": token_data.email})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user


@router.post("/auth/signup", response_model=Token)
async def signup(user_data: UserRegister):
    """Register a new user"""
    try:
        # Check if user already exists
        existing_user = users_collection.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Validate password length
        if len(user_data.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        new_user = {
            "email": user_data.email,
            "full_name": user_data.full_name,
            "password_hash": hashed_password,
            "created_at": datetime.utcnow(),
            "is_active": True,
        }
        
        result = users_collection.insert_one(new_user)
        new_user["_id"] = result.inserted_id
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": new_user["email"], "user_id": str(new_user["_id"])},
            expires_delta=access_token_expires,
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user={
                "email": new_user["email"],
                "full_name": new_user["full_name"],
                "id": str(new_user["_id"]),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup error: {e}")
        raise HTTPException(status_code=500, detail="Signup failed")


@router.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin):
    """Login user and return JWT token"""
    try:
        user = users_collection.find_one({"email": credentials.email})
        if not user or not verify_password(credentials.password, user.get("password_hash", "")):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        if not user.get("is_active", True):
            raise HTTPException(status_code=403, detail="User account is inactive")
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user["email"], "user_id": str(user["_id"])},
            expires_delta=access_token_expires,
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user={
                "email": user["email"],
                "full_name": user.get("full_name", ""),
                "id": str(user["_id"]),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")


@router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(
        id=str(current_user["_id"]),
        email=current_user["email"],
        full_name=current_user.get("full_name", ""),
        created_at=current_user.get("created_at"),
    )


@router.post("/auth/change-password")
async def change_password(
    pwd_change: ChangePassword,
    current_user = Depends(get_current_user),
):
    """Change user password"""
    try:
        # Verify old password
        if not verify_password(pwd_change.old_password, current_user.get("password_hash", "")):
            raise HTTPException(status_code=401, detail="Current password is incorrect")
        
        # Validate new password
        if len(pwd_change.new_password) < 6:
            raise HTTPException(status_code=400, detail="New password must be at least 6 characters")
        
        if pwd_change.old_password == pwd_change.new_password:
            raise HTTPException(status_code=400, detail="New password must be different from current password")
        
        # Update password
        hashed_password = get_password_hash(pwd_change.new_password)
        users_collection.update_one(
            {"_id": current_user["_id"]},
            {"$set": {"password_hash": hashed_password}},
        )
        
        return {"message": "Password changed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Change password error: {e}")
        raise HTTPException(status_code=500, detail="Failed to change password")


@router.post("/auth/logout")
async def logout(current_user = Depends(get_current_user)):
    """Logout user (token is invalidated on client side)"""
    return {"message": "Logged out successfully"}
