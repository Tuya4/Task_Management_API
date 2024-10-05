from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import viewsets, status
from .models import Task, Category, TaskHistory
from .serializers import TaskSerializer, CategorySerializer, TaskHistorySerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework.filters import OrderingFilter
from datetime import timedelta
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.views import APIView


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)

        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
                'status': 'success',
                'user_id': user.id,
                'refresh': str(refresh),
                'access': str(refresh.access_token)
            })
        else:
            return Response({'status': 'failed', 'message': 'Invalid credentials'}, status=401)
        
class RegisterView(APIView):
    
    def post(self, request):
        username = request.data['username']
        password = request.data['password']

        if not username or not password:
            return Response({'status': 'failed', 'message': 'Username and password are required'}, status=400)
        user = User(username=username)
        user.set_password(password)
        user.save()
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "status": "success",
                'user_id': user.id,
                'refresh': str(refresh),
                'access': str(refresh.access_token)
            })        

class TaskFilter(filters.FilterSet):
    status = filters.ChoiceFilter(choices=[('Pending', 'Pending'), ('Completed', 'Completed')])
    priority = filters.ChoiceFilter(choices=[('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')])
    due_date = filters.DateFilter()

    class Meta:
        model = Task
        fields = ['status', 'priority', 'due_date']

class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    filterset_class = TaskFilter
    ordering_fields = ['due_date', 'priority']
    authentication_classes = [JWTAuthentication]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['patch'], url_path='mark_complete')
    def mark_complete(self, request, pk=None):
        
        task = self.get_object()
        task.status = 'Completed'
        task.completed_at = timezone.now()

        # Save the task to TaskHistory
        TaskHistory.objects.create(task=task, completed_at=task.completed_at)

        # Handle recurrence
        if task.recurrence != 'None':
            if task.recurrence == 'Daily':
                task.next_due_date = task.due_date + timedelta(days=1)
            elif task.recurrence == 'Weekly':
                task.next_due_date = task.due_date + timedelta(weeks=1)
            elif task.recurrence == 'Monthly':
                task.next_due_date = task.due_date + timedelta(days=30)
            
            task.status = 'Pending'  # Reset status for the next task occurrence

        task.save()
        return Response({'status': 'Task marked as complete'})

    @action(detail=True, methods=['patch'], url_path='mark_incomplete')
    def mark_incomplete(self, request, pk=None):
        task = self.get_object()
        if task.status == 'Pending':
            return Response({"error": "Task is already marked as incomplete."}, status=status.HTTP_400_BAD_REQUEST)

        task.status = 'Pending'
        task.completed_at = None
        task.save()
        return Response({"message": "Task marked as incomplete."}, status=status.HTTP_200_OK)


class TaskHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TaskHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TaskHistory.objects.filter(task__user=self.request.user)