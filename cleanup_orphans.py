#!/usr/bin/env python
"""Script to clean up orphaned technician users (users with is_technician=True but no profile)"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from apps.accounts.models import User
from apps.technicians.models import TechnicianProfile

def cleanup_orphans():
    """Delete technician users without profiles"""
    print("Finding orphaned technician users...")
    
    # Find users marked as technicians but without a profile
    orphaned = User.objects.filter(is_technician=True).exclude(
        id__in=TechnicianProfile.objects.values_list('user_id', flat=True)
    )
    
    count = orphaned.count()
    print(f"Found {count} orphaned technician users")
    
    if count > 0:
        for user in orphaned:
            print(f"  - Deleting: {user.email}")
        orphaned.delete()
        print(f"\nDeleted {count} orphaned users")
    else:
        print("No orphaned users found")

if __name__ == '__main__':
    cleanup_orphans()
