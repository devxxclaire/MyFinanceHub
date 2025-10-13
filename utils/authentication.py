# utils/authentication.py
import re
import bcrypt
from sqlalchemy.orm import Session
from .database import User, Expense, init_db, engine, SessionLocal
from datetime import date

# initialize DB on import
init_db()

def password_valid(password: str) -> bool:
    """At least 8 chars, 1 upper, 1 lower, 1 digit, 1 special char."""
    return bool(re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@#$%&*!&^()_\-+={}[\]:;\"\'<>,.?/\\|]).{8,}$', password))

def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

def check_password(password: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed)

def register_user(username: str, password: str) -> (bool, str):
    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == username).first():
            return False, "Username already exists."
        if not password_valid(password):
            return False, "Password does not meet requirements."
        user = User(username=username, password_hash=hash_password(password))
        db.add(user)
        db.commit()
        return True, "Registered successfully."
    except Exception as e:
        db.rollback()
        return False, f"Error: {e}"
    finally:
        db.close()

def authenticate(username: str, password: str) -> (bool, str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return False, "User not found."
        if check_password(password, user.password_hash):
            return True, "Authenticated"
        return False, "Invalid credentials."
    finally:
        db.close()

def get_user_by_username(username: str):
    db = SessionLocal()
    try:
        return db.query(User).filter(User.username == username).first()
    finally:
        db.close()

def reset_password(username: str, new_password: str) -> (bool, str):
    if not password_valid(new_password):
        return False, "Password does not meet requirements."
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return False, "User not found."
        user.password_hash = hash_password(new_password)
        db.commit()
        return True, "Password updated."
    except Exception as e:
        db.rollback()
        return False, f"Error: {e}"
    finally:
        db.close()

# Expense helpers
def add_expense(username: str, category: str, amount: float, dt, description: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return False, "User not found."
        if isinstance(dt, str):
            from datetime import datetime
            dt = datetime.fromisoformat(dt).date()
        e = Expense(user_id=user.id, category=category, amount=amount, date=dt, description=description)
        db.add(e)
        db.commit()
        return True, "Expense added."
    except Exception as ex:
        db.rollback()
        return False, f"Error: {ex}"
    finally:
        db.close()

def get_expenses_df(username: str):
    import pandas as pd
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return pd.DataFrame()
        rows = db.query(Expense).filter(Expense.user_id == user.id).order_by(Expense.date.desc()).all()
        data = []
        for r in rows:
            data.append({
                "id": r.id,
                "date": r.date,
                "category": r.category,
                "amount": r.amount,
                "description": r.description
            })
        return pd.DataFrame(data)
    finally:
        db.close()

def delete_expense_by_id(expense_id: int):
    db = SessionLocal()
    try:
        r = db.query(Expense).filter(Expense.id == expense_id).first()
        if not r:
            return False
        db.delete(r)
        db.commit()
        return True
    finally:
        db.close()
        