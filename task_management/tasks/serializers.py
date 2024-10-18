from rest_framework import serializers
from .models import Task, Category, TaskHistory, Notification
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model

User = get_user_model()

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class TaskSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), source='category', write_only=True)

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'due_date', 'priority', 'status', 'completed_at', 'user', 'category', 'category_id', 'recurrence', 'next_due_date']
        read_only_fields = ['completed_at', 'user', 'next_due_date']
    
    def validate(self, data):
        # Prevent editing of completed tasks unless reverting to Pending
        if self.instance and self.instance.status == 'Completed' and data.get('status') != 'Pending':
            raise serializers.ValidationError("Cannot edit a task that has been marked as complete.")
        return data

    def update(self, instance, validated_data):
        # Mark task as completed and set completed_at timestamp
        if validated_data.get('status') == 'Completed' and instance.status != 'Completed':
            instance.completed_at = timezone.now()
            # Handle recurring tasks
            if instance.recurrence != 'None':
                if instance.recurrence == 'Daily':
                    instance.next_due_date = instance.due_date + timedelta(days=1)
                elif instance.recurrence == 'Weekly':
                    instance.next_due_date = instance.due_date + timedelta(weeks=1)
                elif instance.recurrence == 'Monthly':
                    instance.next_due_date = instance.due_date + timedelta(days=30)
                # Reset task for the next occurrence
                instance.status = 'Pending'

        # Revert to incomplete
        elif validated_data.get('status') == 'Pending' and instance.status == 'Completed':
            instance.completed_at = None

        return super().update(instance, validated_data)
    

class TaskHistorySerializer(serializers.ModelSerializer):
    task = TaskSerializer()
    user = serializers.StringRelatedField()

    class Meta:
        model = TaskHistory
        fields = ['task', 'completed_at', 'user']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'email']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User(username=validated_data['username'])
        user.set_password(validated_data['password'])
        user.save()
        return user 

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'user', 'task', 'message', 'is_read', 'created_at']       