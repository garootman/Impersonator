import sqlite3
from bot_config import *
import os
import json
from datetime import datetime, timedelta


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

# Connect to SQLite database
conn = sqlite3.connect(DB_FILE)
conn.row_factory = dict_factory
cursor = conn.cursor()


# Create table for storing user data
cursor.execute('''CREATE TABLE IF NOT EXISTS user_data
                  (user_id INTEGER PRIMARY KEY, name TEXT, lang TEXT, balance REAL, banned INTEGER, subscribed INTEGER, ban_comment TEXT, subs_timestamp DATETIME)''')

# Create table for referals
cursor.execute('''CREATE TABLE IF NOT EXISTS referals
                  (host_id INTEGER, guest_id INTEGER, timestamp DATETIME)''')


# Create table for user chats
cursor.execute('''CREATE TABLE IF NOT EXISTS chat_data
                  (chat_id INTEGER PRIMARY KEY, owner_id INTEGER, title TEXT,role_id INTEGER, skipped INTEGER, type TEXT)''')

# Create table for balance data
cursor.execute('''CREATE TABLE IF NOT EXISTS money_acions
                  (user_id INTEGER, chat_id INTEGER, description TEXT, amount REAL, timestamp DATETIME)''')

# Create table for chat history
cursor.execute('''CREATE TABLE IF NOT EXISTS chat_history
                  (chat_id INTEGER, user_id INTEGER, role_id INTEGER, message TEXT, tokens INTEGER, timestamp DATETIME)''')


#cursor.execute("PRAGMA table_info(chat_data)")
#columns = [col['name'] for col in cursor.fetchall()]

#if "last_sub_upd" not in columns:
#    cursor.execute("ALTER TABLE user_data ADD COLUMN last_sub_upd DATETIME")
#    cursor.execute("UPDATE user_data set last_sub_upd = ?", (datetime(2010,1,1),))
#    conn.commit() 

#cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
#tables = cursor.fetchall()
#print(tables)


conn.commit()    



print("Database initiated!")
