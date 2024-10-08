from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import CustomUser
from rest_framework.permissions import AllowAny
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer

class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                "status": "success",
                "user": UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token)
            })
        return Response(serializer.errors, status=400)
    
class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            user = authenticate(username=username, password=password)
            if user:
                refresh = RefreshToken.for_user(user)
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'user': UserSerializer(user).data  # Serialize user data
                })
            return Response({'status': 'failed', 'message': 'Invalid credentials'}, status=400)
        return Response(serializer.errors, status=400)   

# class LoginView(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         username = request.data.get('username')
#         password = request.data.get('password')

#         user = authenticate(username=username, password=password)

#         if user is not None:
#             refresh = RefreshToken.for_user(user)
#             return Response({
#                 'status': 'success',
#                 'user_id': user.id,
#                 'refresh': str(refresh),
#                 'access': str(refresh.access_token)
#             })
#         else:
#             return Response({'status': 'failed', 'message': 'Invalid credentials'}, status=401)
        
# class RegisterView(APIView):
    
#     def post(self, request):
#         username = request.data['username']
#         password = request.data['password']
#         email = request.data['email']

#         if not username or not password or not email:
#             return Response({'status': 'failed', 'message': 'Username, password, and email are required'}, status=400)
        
#         if CustomUser.objects.filter(email=email).exists():
#             return Response({'status': 'failed', 'message': 'Email is already in use'}, status=400)
        
#         user = CustomUser(username=username, email=email)
#         user.set_password(password)
#         user.save()
#         refresh = RefreshToken.for_user(user)

#         return Response(
#             {
#                 "status": "success",
#                 'user_id': user.id,
#                 'refresh': str(refresh),
#                 'access': str(refresh.access_token)
#             })
