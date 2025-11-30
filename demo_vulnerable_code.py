"""
Demo file with intentional vulnerabilities to show how the agent detects them.
"""

import sqlite3
import requests

# VULNERABILITY 1: Hardcoded password
password = "mySecretPassword123"
api_key = "PLACEHOLDER_API_KEY_HERE"  # DEMO ONLY - DO NOT USE REAL KEYS

# VULNERABILITY 2: SQL Injection
def get_user_unsafe(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # BAD: String formatting in SQL query
    query = f"SELECT * FROM users WHERE id = {user_id}"
    cursor.execute(query)
    return cursor.fetchone()

# VULNERABILITY 3: Missing error handling
def fetch_data_unsafe(url):
    # BAD: No try-catch for network call
    response = requests.get(url)
    data = response.json()  # BAD: No error handling for JSON parsing
    return data

# VULNERABILITY 4: High complexity function
def complex_function(x, y, z):
    if x > 0:
        if y > 0:
            if z > 0:
                if x > y:
                    if y > z:
                        if x > z:
                            if x > 10:
                                if y > 10:
                                    if z > 10:
                                        return "very complex"
    return "simple"

# GOOD: Proper implementation
def get_user_safe(user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    # GOOD: Parameterized query
    query = "SELECT * FROM users WHERE id = ?"
    cursor.execute(query, (user_id,))
    return cursor.fetchone()

def fetch_data_safe(url):
    # GOOD: Proper error handling
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return None
