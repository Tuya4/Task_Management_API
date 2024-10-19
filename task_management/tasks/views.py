from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import viewsets, status
from .models import Task, Category, TaskHistory, Notification, SharedTask
from .serializers import TaskSerializer, CategorySerializer, TaskHistorySerializer, NotificationSerializer
from rest_framework.decorators import action, api_view
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
    # Explicitly filter by the primary key to ensure only one task is fetched
        try:
            task = Task.objects.get(pk=pk)  # Fetch the task using its primary key
        except Task.DoesNotExist:
            return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)
        except Task.MultipleObjectsReturned:
            return Response({"error": "Multiple tasks found with this ID"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_id = request.data['user_id']
            shared_with = User.objects.get(pk=user_id)
        except KeyError:
            return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if shared_with == request.user:
            return Response({"error": "You cannot share task with yourself."}, status=status.HTTP_400_BAD_REQUEST)

        can_edit = request.data.get('can_edit', False)
        if SharedTask.objects.filter(task=task, shared_with=shared_with).exists():
            return Response({"message": f"Task is already shared with {shared_with.username}."}, status=status.HTTP_400_BAD_REQUEST)

        # Share the task
        SharedTask.objects.create(task=task, shared_with=shared_with, can_edit=can_edit)

        # Return custom message with task title and username
        return Response(
            {"message": f"Task '{task.title}' shared with {shared_with.username}."},
            status=status.HTTP_200_OK
        )     
    
    @action(detail=True, methods=['patch'], url_path='mark_complete')
    def mark_complete(self, request, pk=None):
        
        # task = self.get_object()
        # task.status = 'Completed'
        # task.completed_at = timezone.now()

        # # Save the task to TaskHistory
        # TaskHistory.objects.create(task=task, completed_at=task.completed_at)

        # # Handle recurrence
        # if task.recurrence != 'None':
        #     if task.recurrence == 'Daily':
        #         task.next_due_date = task.due_date + timedelta(days=1)
        #     elif task.recurrence == 'Weekly':
        #         task.next_due_date = task.due_date + timedelta(weeks=1)
        #     elif task.recurrence == 'Monthly':
        #         task.next_due_date = task.due_date + timedelta(days=30)
            
        #     task.status = 'Pending'  # Reset status for the next task occurrence

        # task.save()
        # return Response({'status': 'Task marked as complete'})
        try:
            task = self.get_object()
            if task.due_date is None:
                return Response({'error': 'Task due date is missing'}, status=status.HTTP_400_BAD_REQUEST)
            task.status = 'Completed'
            task.completed_at = timezone.now()

            # Save the task to TaskHistory
            TaskHistory.objects.create(task=task, completed_at=task.completed_at, user=self.request.user if request.user.is_authenticated else None)

            # Handle recurrence
            if task.recurrence != 'None':
                if task.recurrence == 'Daily':
                    task.next_due_date = task.due_date + timedelta(days=1)
                elif task.recurrence == 'Weekly':
                    task.next_due_date = task.due_date + timedelta(weeks=1)
                elif task.recurrence == 'Monthly':
                    task.next_due_date = task.due_date + timedelta(days=30)
                else:
                    return Response({'error': 'Invalid recurrence type'}, status=status.HTTP_400_BAD_REQUEST)    
            
                task.status = 'Pending'  # Reset status for the next task occurrence

            task.save()
            return Response({'status': 'Task marked as complete'}, status=status.HTTP_200_OK)
    
        except Task.DoesNotExist:
            return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        #return TaskHistory.objects.filter(task__user=self.request.user)

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Fetch notifications for the current user, sorted by creation date (newest first)
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    # Fetch unread notifications only
    @action(detail=False, methods=['get'], url_path='unread')
    def get_unread_notifications(self, request):
        unread_notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')
        serializer = self.get_serializer(unread_notifications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # Mark all unread notifications as read
    @action(detail=False, methods=['post'], url_path='mark_all_read')
    def mark_all_notifications_as_read(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"message": "All unread notifications marked as read."}, status=status.HTTP_200_OK)

    # Mark selected notifications as read
    @action(detail=False, methods=['patch'], url_path='mark_read')
    def mark_selected_notifications_as_read(self, request):
        notification_ids = request.data.get('notification_ids', [])
        notifications = Notification.objects.filter(id__in=notification_ids, user=request.user)

        if not notifications.exists():
            return Response({"detail": "No notifications found."}, status=status.HTTP_404_NOT_FOUND)

        notifications.update(is_read=True)
        return Response({"message": "Selected notifications marked as read."}, status=status.HTTP_200_OK)
        
    @api_view(['GET'])
    def user_notifications(request):
        notifications = Notification.objects.filter(user=request.user, read=False)
        notifications_data = [{"message": n.message, "created_at": n.created_at} for n in notifications]
        return Response(notifications_data)
       