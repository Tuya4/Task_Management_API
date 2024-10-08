from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet, CategoryViewSet, TaskHistoryViewSet, NotificationViewSet

router = DefaultRouter()
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'task_history', TaskHistoryViewSet, basename='taskhistory')
router.register(r'notifications', NotificationViewSet, basename='notifications')

urlpatterns = [
    path('', include(router.urls)),
    # path('register/', RegisterView.as_view()),
    # path('login/', LoginView.as_view(), name='login'),
]