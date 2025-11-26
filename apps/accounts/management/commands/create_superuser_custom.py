from django.core.management.base import BaseCommand
from apps.accounts.models import User


class Command(BaseCommand):
    help = 'Create a superuser with all required fields'

    def handle(self, *args, **options):
        username = input('Username: ')
        email = input('Email: ')
        phone_number = input('Phone number: ')
        password = input('Password: ')
        
        user = User.objects.create_superuser(
            username=username,
            email=email,
            phone_number=phone_number,
            password=password,
            user_type='customer'
        )
        
        self.stdout.write(self.style.SUCCESS(f'Superuser {username} created successfully!'))
