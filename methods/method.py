from utils import *
from database_renote import operations 

class all_methods:
    def hello(self):
        print("hellloo000000000 world")
        
    def generate_unique_user_id(self):
        return random.randint(10**15, (10**16)-1)
    
    def signup(self):
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
    
        user_id=self.generate_unique_user_id()      
        fullname = data['fullname']
        username = data['username']
        password = generate_password_hash(data['password'])
        email = data['email']
        phone_number = data['phone_number'] 
        profile_pic='aaa'
        
        response=operations.db_methods.signup_db_operation( user_id, client_id, fullname, username, application_id, password, email)
        if response is not None:
            return response
        return jsonify({'message': 'User created successfully'}), 201
    
    def signin(self):
        data = request.json
   
        username = data['username']
        password = data['password']
        
        response=operations.db_methods.signin_db_operation(username)
        if response is not None:
            return response
        
    def forgot_password(self):
        email = request.json.get('email')
        if not email:
            return jsonify({'message':'Email is required'}), 400
        
        response=operations.db_methods.get_user_by_email(email)
        if response is not None:
            return response
    
    def reset_password_(self,token):
        response=operations.db_methods.user_by_reset_token(token)
        if response is not None:
            return response
        
    def update_password(self):
        token=request.form.get('token')
        new_password=request.form.get('password')
        confirm_password=request.form.get('confirm_password')
 
        if new_password != confirm_password:
            return jsonify({'message':'passwords do not match'}), 400
        
        response=operations.db_methods.db_method_update_password(token,new_password)
        if response is not None:
            return response