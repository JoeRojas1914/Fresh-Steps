import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import pooling

load_dotenv()


_pool = pooling.MySQLConnectionPool(
    pool_name="freshsteps_pool",
    pool_size=10,
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    port=int(os.getenv("DB_PORT", 3306)),
    autocommit=False
)

def get_connection():
    return _pool.get_connection()