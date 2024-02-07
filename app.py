
from flask import Flask, request, jsonify,render_template,json 
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from azure.storage.blob import BlobServiceClient
import mysql.connector
from mysql.connector import pooling
from mysql.connector import Error as MySQLError
from mysql.connector import errorcode
import jwt
import datetime
import secrets
import os
from functools import wraps
from redis import Redis
import random
import re 
import methods.method

methods.method.methods1.hello()
 
app = Flask(__name__)
secret_key = secrets.token_hex(16)
app.config['SECRET_KEY'] = secret_key

conn = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Nikhil1234$',
    'database': 'renote_login_sql_db'
}
 
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0
redis_client = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
 
# Create a connection pool
conn_pool = mysql.connector.pooling.MySQLConnectionPool(pool_name="renote_login_sql_db_pool",pool_size=5,**conn)
 
def get_db_connection():
    return conn_pool.get_connection()

# Azure Blob Storage Configuration
AZURE_STORAGE_CONNECTION_STRING = 'DefaultEndpointsProtocol=https;AccountName=necunblobstorage;AccountKey=hgzRK0zpgs+bXf4wnfvFLEJNbSMlbTNeJBuhYHS9jcTrRTzlh0lVlT7K59U8yG0Ojh65p/c4sV97+AStOXtFWw==;EndpointSuffix=core.windows.net'
CONTAINER_NAME = 'pictures'
print("Connection String:", AZURE_STORAGE_CONNECTION_STRING)
 
def token_required(f): 
    @wraps(f)
    def decorated(*args, **kwargs):
        print(request.headers)
        token = None
        if not request.headers.get('Authorization'):
            return jsonify({'message': 'Token is missing!'}), 401
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1] 
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        redis_client.setex
 
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            token_user = data['username']# You can adjust this according to your payload
            token_email=data['email']
            token_application_id=data['Application']
            token_client_id=data['Clientid']
            print(token_client_id)
            
            redis_username = redis_client.hget(token, 'username')

            if redis_username is None or redis_username.decode() != token_user or token_application_id != "renote" or token_client_id != "necun":
                return jsonify({'message': 'Token is invalid or expired!'}), 401
        except:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(token_user,token_email,token_application_id,token_client_id,token,*args, **kwargs)
 
    return decorated

def generate_unique_user_id():
    return random.randint(10**15, (10**16)-1)
 
 
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
 
    user_id=generate_unique_user_id()      
    fullname = data['fullname']
    username = data['username']
    password = generate_password_hash(data['password'])
    email = data['email']
    phone_number = data['phone_number'] 
    pic_url="aaa"
   
    conn = get_db_connection()
    cursor = conn.cursor()
     
    try:
        query = "INSERT INTO users (user_id,client_id,application_id,fullname, username, password, email, phone_number,profile_pic,status) VALUES (%s,%s,%s,%s, %s, %s, %s, %s,%s,%s)"
        cursor.execute(query, (user_id,client_id,application_id,fullname, username, password, email, phone_number,pic_url,0))
        conn.commit()
    except MySQLError as err:
        if err.errno == errorcode.ER_DUP_ENTRY:
            # Check if the error message contains information about which field is duplicated
            error_msg = str(err).lower()
            if "email" in error_msg:
                return jsonify({'message': 'Email already exists'}), 409
            elif "username" in error_msg:
                return jsonify({'message': 'Username already exists'}), 409
            elif "phone_number" in error_msg:
                return jsonify({'message':'Phone Number already exists'}), 409
            else:
                # For any other unique constraints that might have been violated
                return jsonify({'message': 'Duplicate entry for unique field'}), 409
        else:
            print("Database Error:", err)
            return jsonify({'message': "Failed to create user due to a database error", 'error': str(err)}), 500
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
        query = "SELECT password,email,phone_number FROM users WHERE username = %s"
        cursor.execute(query, (username,))
        user_record = cursor.fetchone()
        email = user_record[1]
        phone_number=user_record[2]
        print(user_record)
        
        application_id = request.headers['Application'] 
        client_id = request.headers['Clientid'] 
        
        user_info = {
                'username': username,
                'Application': application_id,
                'Clientid': client_id,
                'email':email,
                'phone_number':phone_number
                }
 
        if user_record and check_password_hash (user_record[0], password):
            token = jwt.encode({'username': username,'email':email,'Application':application_id,'Clientid':client_id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)}, app.config['SECRET_KEY']) 
            redis_client.hmset(token, user_info) 
            redis_client.expire(token, 1800) 
            user1_info = redis_client.hgetall(token) 
            print(user1_info) 
            
            #redis_client.hget(token, 'username') if you want single value
            
            print(user1_info)
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
def protected_route(token_user,token_email,token_application_id,token_client_id,token):
    print(token_user)
    print(token_email)
    redis_username = redis_client.hget(token, 'username')
    print(redis_username) 
    return jsonify({'message': 'This is a protected route accessible only with a valid token.'})
 
 
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
        print(reset_token)
 
        cursor.execute("UPDATE users SET reset_token = %s WHERE user_id=%s", (reset_token, user[0]))
        conn.commit()
 
        reset_url = f"http://120:0:0:1:5000/reset_password/{reset_token}"
 
 
    #need to add email integration
        return jsonify({'message':'password reset link has been sent to your mail'})
    except mysql.connector.Error as err:
        return jsonify({'message':'Database error', 'error': str(err)}), 500
    finally:
        cursor.close()
        conn.close()
 
@app.route('/reset_password/<token>')
def reset_password(token):
    conn=get_db_connection()
    cursor=conn.cursor(buffered=True)
 
    try:
        cursor.execute("SELECT user_id FROM users WHERE reset_token = %s",(token,))
        if cursor.fetchone():
            return render_template('reset_password.html',token=token)
        else:
            return jsonify({'message':'Invalid or expired token'}), 400
       
    finally:
        cursor.close()
        conn.close()
 
@app.route('/update_password', methods=['POST'])
def update_password():
    token=request.form.get('token')
    new_password=request.form.get('password')
    confirm_password=request.form.get('confirm_password')
 
    if new_password != confirm_password:
        return jsonify({'message':'passwords do not match'}), 400
   
    conn=get_db_connection()
    cursor=conn.cursor(buffered=True)
 
    try:
        cursor.execute("SELECT user_id FROM users WHERE reset_token = %s", (token,))
        user = cursor.fetchone()
 
        if user:
            hashed_password=generate_password_hash(new_password)
            cursor.execute("UPDATE users SET password =%s, reset_token=NULL WHERE user_id=%s",(hashed_password, user[0]))
            conn.commit()
            return jsonify({'message':'password has been upodated successfully'}), 200
        else:
            return jsonify({'message':'Invalid or expired token'}), 400
    finally:
        cursor.close()
        conn.close()
 
 
 
 
if __name__ == '__main__':
    app.run(debug=True)        
