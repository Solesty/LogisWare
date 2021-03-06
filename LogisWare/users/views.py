from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegisterForm

from rest_framework import viewsets

from .serializers import UserSerializer

# from .util import NewUserMessages

# from addressbook.models import AddressBook, Tag


class UsersViewset(viewsets.ReadOnlyModelViewSet):
    """
        This class can only be read and no edit can be done to it.
    """
    queryset = get_user_model().objects.all()
    serializer_class = UserSerializer


@login_required
def login_success(request):
    redirect_to_url = "logout"

    # Check if this user is a super admin

    user = request.user

    if user.is_sales:
        redirect_to_url = "dashboard_sales"
    elif user.is_procurement == True:
        redirect_to_url = "dashboard_procurement"
    elif user.is_delivery == True:
        redirect_to_url = "dashboard_delivery"

    print(redirect_to_url)

    # A link will be in the menu if one user has many roles
    return redirect(redirect_to_url)


def register(request):

    messages.error(request, f'Thanks for showing interest to use our platform. We are in a closed beta phase. Only churches and fellowships that enrolled are given access to make use of the platform. Thanks.')
    return redirect('login')

    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email_verified = False
            user.is_super_admin = True
            user.save()

            username = form.cleaned_data.get('username')

            # send first time user mails
            # new_user_messages_obj = NewUserMessages()
            # new_user_messages_obj.send_welcome_message(
            #     user.email, user.name, request, user)
            # new_user_messages_obj.send_email_verification_message(
            #     user.email, user.name, request, user)

            # Create Smart Tag named Youth
            # Tag.objects.create(

            # )

            messages.success(
                request, f'Wow! Welcome on board. Your account has been created. Quickly login to get started')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'users/registrations/register.html', {'form': form, 'title': 'Registration'})
