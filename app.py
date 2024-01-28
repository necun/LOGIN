from flask import Flask, request, jsonify
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


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        print(request.headers)
        token = None

        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]  
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = data['username']  # You can adjust this according to your payload
        except:
            return jsonify({'message': 'Token is invalid!'}), 401

        return f(current_user, *args, **kwargs)

    return decorated

app = Flask(__name__)
secret_key = secrets.token_hex(16)
app.config['SECRET_KEY'] = secret_key
print("Secret Key:", secret_key)


# Azure Blob Storage Configuration
AZURE_STORAGE_CONNECTION_STRING = 'DefaultEndpointsProtocol=https;AccountName=necunblobstorage;AccountKey=hgzRK0zpgs+bXf4wnfvFLEJNbSMlbTNeJBuhYHS9jcTrRTzlh0lVlT7K59U8yG0Ojh65p/c4sV97+AStOXtFWw==;EndpointSuffix=core.windows.net'
CONTAINER_NAME = 'pictures'
print("Connection String:", AZURE_STORAGE_CONNECTION_STRING)
# Database Configuration and Connection Pool
conn = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Nikhil1234$',
    'database': 'data1'
}

# Create a connection pool
conn_pool = mysql.connector.pooling.MySQLConnectionPool(pool_name="mypool",pool_size=5,**conn)

def get_db_connection():
    return conn_pool.get_connection()


@app.route('/user/signup', methods=['POST'])
def signup_common():
    data = request.json
    print("Headers Received:", request.headers)


    required_fields = ['fullname', 'username', 'password', 'email', 'phone_number']
    missing_fields = [field for field in required_fields if field not in data or not data[field]]
    
    if missing_fields:
        return jsonify({'message': 'Missing fields', 'missing': missing_fields}), 400
    
    if 'Application' in request.headers and 'Clientid' in request.headers:
        application_id = request.headers['Application']
        client_id = request.headers['Clientid']
    else:
        print("Required headers not found")

            
    fullname = data['fullname']
    username = data['username']
    password = generate_password_hash(data['password'])
    email = data['email']
    phone_number = data['phone_number']
    pic_url="aaa"
    
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = "INSERT INTO users (client_id,application_id,fullname, username, password, email, phone_number,pic_url) VALUES (%s,%s,%s, %s, %s, %s, %s,%s)"
        cursor.execute(query, (client_id,application_id,fullname, username, password, email, phone_number,pic_url)) 
        conn.commit()
    except mysql.connector.Error as err:
        print("Error:", err)
        return jsonify({'message': "Failed to create user"}), 500
    finally:
        cursor.close()
        conn.close()
        
    return jsonify({'message': 'User created successfully'}), 201

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

    '''try:
        insert_query = "INSERT INTO users (pic_url) VALUES (%s)"
        cursor.execute(insert_query, (image_url,))
        conn.commit()
    except mysql.connector.Error as err:
        print("Error:", err)
        return jsonify({'message': 'Failed to upload image'}), 500
    finally:
        cursor.close()
        conn.close()'''

    return jsonify({'message': 'Image uploaded successfully', 'url': image_url}), 200

def upload_to_azure_blob(file_stream, file_name):
    
    if not AZURE_STORAGE_CONNECTION_STRING:
        raise ValueError("The Azure Storage Connection String is not set or is empty.")

    blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=file_name)

    blob_client.upload_blob(file_stream, overwrite=True)

    return blob_client.url


@app.route('/protected', methods=['GET'])
@token_required
def protected_route(current_user):
    print(current_user)
    return jsonify({'message': 'This is a protected route accessible only with a valid token.'})

if __name__ == '__main__':
    app.run(debug=True)