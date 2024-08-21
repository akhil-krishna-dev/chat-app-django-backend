from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.contrib.auth import authenticate



User = get_user_model()



class RegistrationSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)
    class Meta:
        model = User
        fields = ["email", "password", "confirm_password","first_name", "last_name"]

    def create(self, validated_data):
        password = validated_data["password"]
        confirm_password = validated_data['confirm_password']
        if password != confirm_password:
            raise serializers.ValidationError("password and confirm password doesn't match")

        return User.objects.create_user(
            email = validated_data["email"],
            password = password,
            first_name = validated_data.get("first_name", ""),
            last_name = validated_data.get("last_name", "")
        )
    


class UserLoginSerializer(serializers.Serializer):
    
    email = serializers.EmailField()
    id = serializers.CharField(max_length=15, read_only=True)
    password = serializers.CharField(max_length=155, write_only=True)

    def validate(self, data):
        email = data.get("email",None)
        password = data.get("password",None)

        if email is None:
            raise serializers.ValidationError("An email is required for login")
        if password is None:
            raise serializers.ValidationError("Please enter the password")
        
        user = authenticate(username=email, password=password)

        if user is None:
            raise serializers.ValidationError("Email or Password wrong")
        if not user.is_active:
            raise serializers.ValidationError("User is inactive")
        
        return {
            "email":user.email,
            "id":user.id
        }
    


class UserProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    online = serializers.BooleanField(default=False)

    class Meta:
        model = User
        fields = ["id","email", "full_name","status","online","image","last_seen"]

    def get_full_name(self, obj):
        obj.first_name = obj.first_name.capitalize()
        obj.last_name = obj.last_name.capitalize()
        return f"{obj.first_name} {obj.last_name}"
    
    

