"""
Базовая модель для Peewee ORM
"""
from peewee import Model, SqliteDatabase
import os

# Создаем базу данных
db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'bullaware.db')
os.makedirs(os.path.dirname(db_path), exist_ok=True)

database = SqliteDatabase(db_path)

class BaseModel(Model):
    """Базовая модель для всех таблиц"""
    
    class Meta:
        database = database

