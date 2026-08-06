import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import boto3
from botocore.exceptions import ClientError

app = Flask(__name__)
CORS(app)


def get_secret():
    secret_name = "rds!db-ac74596e-50e0-4120-8858-461f7beef0fe"
    region_name = "us-east-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    secret_string = get_secret_value_response.get('SecretString')
    if secret_string is None:
        secret_string = get_secret_value_response['SecretBinary'].decode('utf-8')

    try:
        secret_data = json.loads(secret_string)
    except json.JSONDecodeError:
        return secret_string

    return secret_data

secret_data = get_secret()

# Database Configuration
db_config = {
    'host': 'database-1.ckhkeogg21ln.us-east-1.rds.amazonaws.com',
    'user': secret_data['username'] ,
    'password': secret_data['password'] ,
    'database': 'dev'
}

# Connect to MySQL
def get_db_connection():
    return mysql.connector.connect(**db_config)

# 1️⃣ Get all users
@app.route('/users', methods=['GET'])
def get_users():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(users)

# 2️⃣ Get user by ID
@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if user:
        return jsonify(user)
    return jsonify({'error': 'User not found'}), 404

# 3️⃣ Add a new user
@app.route('/users/add', methods=['POST'])
def add_user():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    if not name or not email:
        return jsonify({'error': 'Name and Email are required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (name, email) VALUES (%s, %s)",
            (name, email)
        )
        conn.commit()
        return jsonify({'message': 'User added successfully'}), 201
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

# 4️⃣ Update user by ID
@app.route('/users/update/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    data = request.json
    name = data.get('name')
    email = data.get('email')
    if not name or not email:
        return jsonify({'error': 'Name and Email are required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    if not cursor.fetchone():
        return jsonify({'error': 'User not found'}), 404

    try:
        cursor.execute(
            "UPDATE users SET name = %s, email = %s WHERE id = %s",
            (name, email, user_id)
        )
        conn.commit()
        return jsonify({'message': 'User updated successfully'})
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

# 5️⃣ Delete user by ID
@app.route('/users/delete/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    if not cursor.fetchone():
        return jsonify({'error': 'User not found'}), 404

    try:
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        return jsonify({'message': 'User deleted successfully'})
    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

# 🔹 Simple Hello route
@app.route('/')
def index():
    return "Hello"

# Entry Point
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
