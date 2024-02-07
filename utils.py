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


class redis_config:
    redis_client=None
    def redis(cls):
        REDIS_HOST = 'localhost'
        REDIS_PORT = 6379
        REDIS_DB = 0
        redis_client = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
        return redis_client 