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
import utils 

class db_methods:
    def get_db_connection():
        conn = {
            'host': 'localhost',
            'user': 'root',
            'password': 'Nikhil1234$',
            'database': 'renote_login_sql_db'
        }
        conn_pool = mysql.connector.pooling.MySQLConnectionPool(pool_name="renote_login_sql_db_pool",pool_size=5,**conn)
        return conn_pool.get_connection()
    
    def signin_db_operation(self,username):
    # Database query to retrieve user information by username
        conn = self.get_db_connection()
        cursor = conn.cursor(buffered=True)
        
        try:
            query = "SELECT password,email,phone_number FROM users WHERE username = %s"
            cursor.execute(query, (username,))
            user_record = cursor.fetchone()
            password=user_record[0]
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
            
            redis_client=utils.redis_config.redis
            
            if user_record and check_password_hash (user_record[0], password):
                token = jwt.encode({'username': username,'email':email,'Application':application_id,'Clientid':client_id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)}, app.config['SECRET_KEY']) 
                redis_client.hmset(token, user_info) 
                redis_client.expire(token, 1800) 
                #redis_client.hget(token, 'username') if you want single value
                return jsonify({'message': 'Login successful', 'token': token}), 200
            else: 
                return jsonify({'message': 'Invalid username or password'}), 401
        except mysql.connector.Error as err:
            print("Database Error:", err)
            return jsonify({'message': 'Database error', 'error': str(err)}), 500
        finally:
            cursor.close()
            conn.close()
            
    def signup_db_operation(self,user_id,client_id,fullname,username,application_id,password,email,phone_number, profile_pic):
        conn = self.get_db_connection()
        cursor = conn.cursor()
    
        try:
            query = "INSERT INTO users (user_id,client_id,application_id,fullname, username, password, email) VALUES (%s,%s,%s,%s, %s, %s, %s)"
            cursor.execute(query, (user_id,client_id,application_id,fullname, username, password, email))
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
        
    def get_user_by_email(self,email):
        conn = self.get_db_connection()
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
            
    def user_by_reset_token(self,token):
        conn=self.get_db_connection() 
        cursor=conn.cursor(buffered=True)
 
        try:
            cursor.execute("SELECT user_id FROM users WHERE reset_token = %s",(token,))
            if cursor.fetchone():
                return render_template('reset_password.html',token=token)
            else:
                return jsonify({'message':'Invalid or expired token'}), 400
        except mysql.connector.Error as err:
            return jsonify({'message':'Database error', 'error': str(err)}), 500    
        finally:
            cursor.close()
            conn.close()
            
    def db_method_update_password(self,token,new_password):
        conn=self.get_db_connection()
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
        except mysql.connector.Error as err:
            return jsonify({'message':'Database error', 'error': str(err)}), 500
        finally:
            cursor.close()
            conn.close()
            
    def hello():
        print("hello world!")