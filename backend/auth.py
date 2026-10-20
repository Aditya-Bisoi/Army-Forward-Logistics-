import os, jwt, bcrypt
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Request, Response, Depends
from pydantic import BaseModel
from db import db

JWT_SECRET = os.environ.get("JWT_SECRET", "supersecret_forward_logistics_2026_demo_key")
FAILED_LOGINS = {}
router = APIRouter(prefix="/api/auth")


class LoginInput(BaseModel):
    email: str
    password: str


def hash_password(password): return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
def verify_password(password, hashed): return bcrypt.checkpw(password.encode(), hashed.encode())
def token_for(user): return jwt.encode({"sub": user["id"], "email": user["email"], "role": user["role"], "exp": datetime.now(timezone.utc) + timedelta(hours=8)}, JWT_SECRET, algorithm="HS256")


async def current_user(request: Request):
    token = request.cookies.get("access_token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token: raise HTTPException(401, "Authentication required")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return {"id": payload["sub"], "email": payload["email"], "role": payload["role"]}
    except jwt.PyJWTError: raise HTTPException(401, "Invalid or expired session")


async def admin_user(user=Depends(current_user)):
    if user["role"] != "admin": raise HTTPException(403, "Admin role required")
    return user


@router.post("/login")
async def login(input: LoginInput, response: Response):
    email = input.email.lower().strip()
    attempt = FAILED_LOGINS.get(email)
    if attempt and attempt["locked_until"] > datetime.now(timezone.utc):
        raise HTTPException(429, "Too many failed attempts. Try again in 15 minutes.")
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user or not verify_password(input.password, user["password_hash"]):
        current = FAILED_LOGINS.get(email, {"count": 0, "locked_until": datetime.min.replace(tzinfo=timezone.utc)})
        current["count"] += 1
        if current["count"] >= 5: current["locked_until"] = datetime.now(timezone.utc) + timedelta(minutes=15)
        FAILED_LOGINS[email] = current
        locked = current["count"] > 5
        raise HTTPException(429 if locked else 401, "Too many failed attempts. Try again in 15 minutes." if locked else "Invalid email or password")
    FAILED_LOGINS.pop(email, None)
    safe = {"id": user["id"], "email": user["email"], "name": user["name"], "role": user["role"]}
    token = token_for(safe)
    response.set_cookie("access_token", token, httponly=True, secure=True, samesite="none", max_age=28800, path="/")
    return {**safe, "token": token}


@router.get("/me")
async def me(user=Depends(current_user)): return user


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/", secure=True, samesite="none", httponly=True)
    return {"ok": True}


async def seed_admin():
    await db.users.create_index("email", unique=True)
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@forwardlogistics.demo")
    admin_password = os.environ.get("ADMIN_PASSWORD", "ControlTower2026!")
    user = await db.users.find_one({"email": admin_email})
    if not user:
        await db.users.insert_one({"id": "usr-admin", "email": admin_email, "password_hash": hash_password(admin_password), "name": "Operations Admin", "role": "admin"})
    elif not verify_password(admin_password, user["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password)}})
