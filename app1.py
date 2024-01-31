from flask import Flask, request, jsonify, redirect, url_for, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from azure.storage.blob import BlobServiceClient
import mysql.connector
from mysql.connector import pooling
import jwt
import datetime
import secrets
import os
from functools import wraps
from redis import Redis
from flask_ngrok import run_with_ngrok

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization']
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = data['username']
        except:
            return jsonify({'message': 'Token is invalid!'}), 401

        return f(current_user, *args, **kwargs)

    return decorated

app = Flask(__name__)
run_with_ngrok(app)
secret_key = secrets.token_hex(16)
app.config['SECRET_KEY'] = secret_key
print("Secret Key:", secret_key)

AZURE_STORAGE_CONNECTION_STRING = 'DefaultEndpointsProtocol=https;AccountName=necunblobstorage;AccountKey=hgzRK0zpgs+bXf4wnfvFLEJNbSMlbTNeJBuhYHS9jcTrRTzlh0lVlT7K59U8yG0Ojh65p/c4sV97+AStOXtFWw==;EndpointSuffix=core.windows.net'
CONTAINER_NAME = 'pictures'

conn = {
    'host': 'localhost',
    'user': 'root',
    'password': 'vishnuvardhan',
    'database': 'data1'
}

REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0
redis_client = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

conn_pool = mysql.connector.pooling.MySQLConnectionPool(pool_name="mypool",pool_size=5,**conn)

def get_db_connection():
    return conn_pool.get_connection()

@app.route('/user/signup', methods=['POST'])
def signup_common():
    try:
        data = request.json

        required_fields = ['fullname', 'username', 'password', 'email', 'phone_number']
        missing_fields = [field for field in required_fields if field not in data or not data[field]]
        if missing_fields:
            return jsonify({'message': 'Missing fields', 'missing': missing_fields}), 400
        
        fullname = data['fullname']
        username = data['username']
        password = generate_password_hash(data['password'])
        email = data['email']
        phone_number = data['phone_number']
        application_id = data['application_id']
        client_id = data['client_id']

        conn = get_db_connection()
        cursor = conn.cursor(buffered=True)

        try:
            # Check if the username, email, or phone_number already exists
            query = "SELECT * FROM users WHERE username = %s OR email = %s OR phone_number = %s"
            cursor.execute(query,(username, email, phone_number))
            existing_user = cursor.fetchone()

            if existing_user:
                return jsonify({'message': 'Username, email, or phone number already exists'}), 400
            
            else:
                # Insert the new user data into the database
                query = "INSERT INTO users (application_id, client_id, fullname, username, password, email, phone_number) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                cursor.execute(query, (application_id, client_id, fullname, username, password, email, phone_number))
                conn.commit()

                return jsonify({'message': 'User created successfully'}), 201

        except mysql.connector.Error as err:
            return jsonify({'message': "Failed to create user", 'error': str(err)}), 500

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        return jsonify({'message': 'Internal Server Error', 'error': str(e)}), 500


@app.route('/user/signin', methods=['POST'])
def signin():
    data = request.json 
    
    username = data['username']
    password = data['password']

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)

    try:
        query = "SELECT password FROM users WHERE username = %s"
        cursor.execute(query, (username,))
        user_record = cursor.fetchone() 

        if user_record and check_password_hash(user_record[0], password):
            token = jwt.encode({'username': username, 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)}, app.config['SECRET_KEY'])
            redis_client.setex(token, 1800, username)
            return jsonify({'message': 'Login successful', 'token': token}), 200
        else:
            return jsonify({'message': 'Invalid username or password'}), 401
    except mysql.connector.Error as err:
        print("Database Error:", err)
        return jsonify({'message': 'Database error', 'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'message': 'No image part'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400

    filename = secure_filename(file.filename)
    image_url = upload_to_azure_blob(file, filename)

    conn = get_db_connection()
    cursor = conn.cursor()

    return jsonify({'message': 'Image uploaded successfully', 'url': image_url}), 200

def upload_to_azure_blob(file_stream, file_name):
    
    if not AZURE_STORAGE_CONNECTION_STRING:
        raise ValueError("The Azure Storage Connection String is not set or is empty.")

    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=file_name)

    blob_client.upload_blob(file_stream, overwrite=True)

    return blob_client.url

@app.route('/user/forgot_password', methods=['POST'] )
def forgot_password():
    email = request.json.get('email')
    if not email:
        return jsonify({'message':'Email is required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)

    try:
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if not user:
            return jsonify({'message':'user not found'}), 404
        
        reset_token = secrets.token_hex(16)

        cursor.execute("UPDATE users SET reset_token = %s WHERE user_id=%s", (reset_token, user[0]))
        conn.commit()

        return jsonify({'message':'password reset link has been sent to your mail'
                        f"http://localhost:5000/user/reset_password/{reset_token}"}) # this link should be mailed to the user

        #return jsonify({'message':'password reset link has been sent to your mail'})
    except mysql.connector.Error as err:
        return jsonify({'message':'Database error', 'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/user/reset_password/<token>')
def reset_password(token):
    conn=get_db_connection()
    cursor=conn.cursor(buffered=True)

    try:
        cursor.execute("SELECT user_id FROM users WHERE reset_token = %s", (token,))
        if cursor.fetchone():
            return render_template('reset_password.html',token=token)
        else:
            return jsonify({'message':'Invalid or expired token'}), 400
        
    finally:
        cursor.close()
        conn.close()

@app.route('/user/update_password', methods=['POST'])
def update_password():

    token=request.form.get('token')
    new_password=request.form.get('password')
    confirm_password=request.form.get('confirm_password')
    
    if new_password != confirm_password:
        return jsonify({'message': 'Passwords do not match'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)

    try:
        cursor.execute("SELECT user_id FROM users WHERE reset_token = %s", (token,))
        user = cursor.fetchone()

        if user:
            hashed_password=generate_password_hash(new_password)
            cursor.execute("UPDATE users SET password =%s, reset_token=NULL WHERE user_id=%s",(hashed_password, user[0]))
            conn.commit()
            return jsonify({'message':'password has been updated successfully'}), 200
        else:
            return jsonify({'message':'Invalid or expired token'}), 400
    finally:
        cursor.close()
        conn.close()
    
@app.route('/user/change_password', methods=['POST'])
@token_required
def change_password(current_user):
    old_password = request.json.get('old_password')
    new_password = request.json.get('new_password')
    confirm_password = request.json.get('confirm_password')

    if not all([old_password, new_password, confirm_password]):
        return jsonify({'message': 'All fields are required'}), 400

    if new_password != confirm_password:
        return jsonify({'message': 'Passwords do not match'}), 400

    if new_password == old_password:
        return jsonify({'message': 'Old and new passwords should not be the same'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(buffered=True)

    try:
        cursor.execute("SELECT password FROM users WHERE username = %s", (current_user,))
        stored_hashed_password = cursor.fetchone()

        if stored_hashed_password and check_password_hash(stored_hashed_password[0], old_password):
            hashed_new_password = generate_password_hash(new_password)
            cursor.execute("UPDATE users SET password = %s WHERE username = %s", (hashed_new_password, current_user))
            conn.commit()
            return jsonify({'message': 'Password has been changed successfully'}), 200
        else:
            return jsonify({'message': 'Incorrect old password'}), 400
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run()