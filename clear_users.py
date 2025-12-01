#!/usr/bin/env python
"""Script to clear all users from the database for fresh start"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.accounts.models import User
from apps.technicians.models import TechnicianProfile, TechnicianLocation, Company

def clear_all_users():
    """Delete all users and related data"""
    print("Clearing all users and related data...")
    
    # Delete technician profiles first (due to foreign key)
    tech_count = TechnicianProfile.objects.count()
    TechnicianProfile.objects.all().delete()
    print(f"  Deleted {tech_count} technician profiles")
    
    # Delete technician locations
    loc_count = TechnicianLocation.objects.count()
    TechnicianLocation.objects.all().delete()
    print(f"  Deleted {loc_count} technician locations")
    
    # Delete companies
    company_count = Company.objects.count()
    Company.objects.all().delete()
    print(f"  Deleted {company_count} companies")
    
    # Delete all users
    user_count = User.objects.count()
    User.objects.all().delete()
    print(f"  Deleted {user_count} users")
    
    print("\nDatabase cleared successfully!")

if __name__ == '__main__':
    confirm = input("Are you sure you want to delete ALL users? (yes/no): ")
    if confirm.lower() == 'yes':
        clear_all_users()
    else:
        print("Aborted.")
