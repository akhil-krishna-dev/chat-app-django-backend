from rest_framework.authentication import BasicAuthentication
from rest_framework.exceptions import AuthenticationFailed
from Accounts.models import BlacklistedToken
import jwt
from jwt.exceptions import ExpiredSignatureError,InvalidTokenError
from django.contrib.auth import get_user_model
from django.conf import settings
from datetime import datetime
from channels.db import database_sync_to_async



User = get_user_model()


class JWTAuthentication(BasicAuthentication):

    def authenticate(self, request):
        token = self.extract_token(request=request)
        if token is None:
            return None 
        
        self.check_token_blacklist(token)

        try:
            payload = jwt.decode(jwt=token, key=settings.SECRET_KEY, algorithms=['HS256'])
            self.verify_token(payload=payload) 

            user_id = payload['id']
            user = User.objects.get(id=int(user_id))
            return (user, token)
        except ExpiredSignatureError:
            raise AuthenticationFailed("Token has Expired")
        except InvalidTokenError:
            raise AuthenticationFailed("Invalid token")
        except User.DoesNotExist:
            raise AuthenticationFailed("user does not found")

    @staticmethod
    def generate_token(payload):
        token = jwt.encode(payload=payload, key=settings.SECRET_KEY, algorithm='HS256')
        return token
    
    @staticmethod
    def extract_token(request):
        auth_header = request.headers.get('Authorization')        
        if auth_header and auth_header.startswith('Bearer '):
            return auth_header.split(" ")[1]
        return None
    
    @database_sync_to_async
    def authenticate_websocket(self, scope, token):
        try:
            payload = jwt.decode(jwt=token, key=settings.SECRET_KEY, algorithms=['HS256'])
            self.verify_token(payload=payload)

            user_id = payload['id']
            user = User.objects.get(id=user_id)
            return user
        except (InvalidTokenError,ExpiredSignatureError,User.DoesNotExist):
            raise AuthenticationFailed("Invalid Token")
    
    def verify_token(self, payload):
        if 'exp' not in payload:
            raise InvalidTokenError("Token has no expire")
        
        expire_timestamp = payload['exp']
        current_timestamp = datetime.utcnow()

        if current_timestamp.timestamp() > expire_timestamp:
            raise ExpiredSignatureError("Token has expired")
        
    def check_token_blacklist(self, token):
        if BlacklistedToken.objects.filter(token=token).exists():
            raise AuthenticationFailed("Token is blacklisted")
  
        

