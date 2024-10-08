from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import viewsets, status
from .models import Task, Category, TaskHistory, Notification, SharedTask
from .serializers import TaskSerializer, CategorySerializer, TaskHistorySerializer, NotificationSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework.filters import OrderingFilter
from datetime import timedelta
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied


User = get_user_model()

        

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

def create_task_notification(user, task):
    message = f'Task "{task.title}" is due on {task.due_date}.'
    Notification.objects.create(user=user, task=task, message=message)

class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    filterset_class = TaskFilter
    ordering_fields = ['due_date', 'priority']
    authentication_classes = [JWTAuthentication]

    def perform_create(self, serializer):
        task = serializer.save(user=self.request.user)
        create_task_notification(self.request.user, task)

    def get_queryset(self):
        user = self.request.user
        owned_tasks = Task.objects.filter(user=user)
        shared_tasks = Task.objects.filter(sharedtask__shared_with=user)
        return owned_tasks | shared_tasks 
        
    
    def perform_update(self, serializer):
        task = self.get_object()
        user = self.request.user
        create_task_notification(self.request.user, task)
        if task.user == user or SharedTask.objects.filter(task=task, shared_with=user, can_edit=True).exists():
            serializer.save()
        else:
            raise PermissionDenied("You don't have permission to edit this task.")

    @action(detail=True, methods=['post'], url_path='share')
    def share_task(self, request, pk=None):
        task = self.get_object()
        shared_with = User.objects.get(pk=request.data['user_id'])
        can_edit = request.data.get('can_edit', False)

        if SharedTask.objects.filter(task=task, shared_with=shared_with).exists():
            return Response({"message": "Task is already shared with this user."}, status=status.HTTP_400_BAD_REQUEST)

        SharedTask.objects.create(task=task, shared_with=shared_with, can_edit=can_edit)
        return Response({"message": "Task shared successfully."}, status=status.HTTP_200_OK)        
        
    
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
    
class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    # Fetch unread notifications
    @action(detail=False, methods=['get'], url_path='unread')
    def mark_notifications_as_read(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"message": "All unread notifications marked as read."})
    
    @action(detail=False, methods=['patch'], url_path='mark_read')
    def mark_read(self, request):
        notification_ids = request.data.get('notification_ids', [])
        notifications = Notification.objects.filter(id__in=notification_ids, user=request.user)

        if not notifications.exists():
            return Response({"detail": "No notifications found."}, status=status.HTTP_404_NOT_FOUND)

        notifications.update(is_read=True)
        return Response({"message": "Notifications marked as read."}, status=status.HTTP_200_OK) 
    
       