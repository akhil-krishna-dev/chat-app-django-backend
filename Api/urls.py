from django.urls import path, include
from Accounts.views import *
from Home.views import *
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register(r'home/chats', ChatViewSet, basename="chat")



urlpatterns = [
    path('', include(router.urls)),
    path("accounts/register/", registration, name="register"),
    path("accounts/login/", login, name='login'),
    path('accounts/users/', get_users, name='get-users'),
    path('accounts/request-user-profile/',requested_user_profile, name='requested-user-profile'),
    path('accounts/users/search/', UsersList.as_view(), name="search-users"),
    path('accounts/users/edit-username', edit_fullname, name='edit-username'),
    path('accounts/users/edit-status', edit_status, name='edit-status'),
    path('accounts/users/change-profile-image', change_profile_image, name='change-profile-image'),
    path('accounts/users/logout/', logout, name='logout'),

]