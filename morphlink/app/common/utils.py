import random, string
from fastapi import HTTPException

USERS = {
    "alice": {"id": 1, "name": "Alice"},
    "bob": {"id": 2, "name": "Bob"},
}

def get_user(user: str) -> int:
    if user not in USERS:
        raise HTTPException(status_code=401, detail="Invalid user")
    return USERS[user]["id"]

def generate_code(length: int = 6) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))
