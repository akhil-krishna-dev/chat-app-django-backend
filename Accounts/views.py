from rest_framework.decorators import api_view,permission_classes
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework.response import Response
from rest_framework import status
from Accounts.models import BlacklistedToken
from Accounts.serializers import *
from .token_authentication import JWTAuthentication
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta


@api_view(["POST"])
@permission_classes([AllowAny])
def registration(request):
    serializer = RegistrationSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status.HTTP_201_CREATED)
    email = serializer.errors.get("email")
    return Response(email, status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        expire = datetime.utcnow() + timedelta(hours=24)
        payload = serializer.data
        payload['exp'] = expire.timestamp()

        token = JWTAuthentication.generate_token(payload=payload)
        response = Response(status=status.HTTP_200_OK)
        response.data = {
            "message":"login succesfull",
            "token":token,
            "expire":expire.isoformat(),
            "user":serializer.data
        }
        return response
    return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def requested_user_profile(request):
    requested_user = request.user
    serializer = UserProfileSerializer(requested_user)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_users(request):
    requested_user = request.user

    def user_filter(user):
        if not user.is_superuser and user.id != requested_user.id:
            return user
  
    users = filter(user_filter ,get_user_model().objects.all())
    serializer = UserProfileSerializer(users, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def edit_fullname(request):
    data = request.data
    try:
        user = User.objects.get(id = request.user.id)
        user.first_name = data['first_name']
        user.last_name = data['last_name']
        user.save()
        return Response({"full_name":str(user.get_full_name())})
    except User.DoesNotExist:
        return Response({"error":"user does not found"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def edit_status(request):
    data = request.data
    try:
        user = User.objects.get(id = request.user.id)
        user.status = data['status']
        user.save()
        return Response({"status":str(user.status)})
    except User.DoesNotExist:
        return Response({"error":"user does not found"}, status=status.HTTP_400_BAD_REQUEST)
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_profile_image(request):
    user = request.user

    if 'image' in request.FILES:
        user.image = request.FILES['image']
        user.save()
        data = {
            "message":"image changed successfully",
            "image":user.image.url
        }
        return Response(data, status=status.HTTP_200_OK)
    return Response({"message":"no image in request"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    token = JWTAuthentication.extract_token(request)
    BlacklistedToken.objects.create(token=token).save()
    return Response({"message":"token blacklisted"}, status=status.HTTP_200_OK)
