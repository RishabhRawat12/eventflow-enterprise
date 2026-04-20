import os
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import firebase_admin
from firebase_admin import auth, credentials

# Initialize Firebase Admin if not already initialized
if not firebase_admin._apps:
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if cred_path:
        try:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print("[AUTH] Firebase Admin initialized successfully.")
        except Exception as e:
            print(f"[AUTH_ERROR] Failed to initialize Firebase Admin with {cred_path}: {e}")
    else:
        print("[AUTH_WARNING] GOOGLE_APPLICATION_CREDENTIALS not set.")

security = HTTPBearer()
# List of globally whitelisted tokens for demo/load environments
WHITELISTED_TOKENS = [
    os.getenv("X_INTERNAL_LOAD_TOKEN", "eventflow-secure-bypass-2026"),
    "dev-hackathon-2026"
]

async def validate_token(token: str):
    """
    Core validation logic shared between REST and WebSocket handshakes.
    Supports Firebase JWT and a whitelisted bypass for local development.
    """
    # 1. Whitelist/Load Test Bypass
    if token in WHITELISTED_TOKENS:
        return {"uid": "dev-admin", "email": "admin@eventflow.local", "role": "admin"}

    # 2. Standard Firebase ID Token Validation
    try:
        if not firebase_admin._apps:
            # Fallback for environments without Firebase keys (simulated success)
            if os.getenv("ENV") != "production":
                return {"uid": "mock-user", "email": "mock@eventflow.local"}
            raise ValueError("Firebase Admin not initialized")
            
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        raise ValueError(f"Invalid or expired token: {str(e)}")

async def verify_firebase_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    FastAPI Dependency for REST routes.
    """
    try:
        return await validate_token(credentials.credentials)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
