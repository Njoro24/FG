#!/usr/bin/env python
"""
Create test data for FundiGO platform
Run: python manage.py shell < create_test_data.py
"""

from apps.accounts.models import User
from apps.technicians.models import TechnicianProfile, TechnicianLocation
from django.db import transaction

print("🚀 Creating test data for FundiGO...")

# Test technicians data
technicians_data = [
    {
        'email': 'john.kamau@fundigo.com',
        'first_name': 'John',
        'last_name': 'Kamau',
        'phone': '+254712345678',
        'skills': ['phone_repair', 'laptop_repair'],
        'rating': 4.9,
        'trust_score': 20,
        'completed_jobs': 156,
        'city': 'Nairobi',
        'lat': -1.286389,
        'lng': 36.817223,
    },
    {
        'email': 'mary.wanjiku@fundigo.com',
        'first_name': 'Mary',
        'last_name': 'Wanjiku',
        'phone': '+254723456789',
        'skills': ['solar_repair', 'electric_fence'],
        'rating': 4.8,
        'trust_score': 15,
        'completed_jobs': 98,
        'city': 'Nairobi',
        'lat': -1.292066,
        'lng': 36.821945,
    },
    {
        'email': 'peter.omondi@fundigo.com',
        'first_name': 'Peter',
        'last_name': 'Omondi',
        'phone': '+254734567890',
        'skills': ['cctv_installation', 'tv_mounting'],
        'rating': 4.9,
        'trust_score': 25,
        'completed_jobs': 142,
        'city': 'Nairobi',
        'lat': -1.280000,
        'lng': 36.830000,
    },
    {
        'email': 'grace.akinyi@fundigo.com',
        'first_name': 'Grace',
        'last_name': 'Akinyi',
        'phone': '+254745678901',
        'skills': ['water_pump', 'shower_repair'],
        'rating': 4.7,
        'trust_score': 10,
        'completed_jobs': 87,
        'city': 'Nairobi',
        'lat': -1.295000,
        'lng': 36.810000,
    },
    {
        'email': 'david.mwangi@fundigo.com',
        'first_name': 'David',
        'last_name': 'Mwangi',
        'phone': '+254756789012',
        'skills': ['fridge_repair', 'cooker_repair', 'microwave_repair'],
        'rating': 4.6,
        'trust_score': 10,
        'completed_jobs': 73,
        'city': 'Nairobi',
        'lat': -1.275000,
        'lng': 36.825000,
    },
]

try:
    with transaction.atomic():
        for tech_data in technicians_data:
            # Check if user already exists
            if User.objects.filter(email=tech_data['email']).exists():
                print(f"⚠️  User {tech_data['email']} already exists, skipping...")
                continue
            
            # Create user
            user = User.objects.create_user(
                email=tech_data['email'],
                password='Test1234!',
                first_name=tech_data['first_name'],
                last_name=tech_data['last_name'],
                full_name=f"{tech_data['first_name']} {tech_data['last_name']}",
                phone_number=tech_data['phone'],
                is_technician=True,
                email_verified=True,
                is_active=True
            )
            
            # Create technician profile
            profile = TechnicianProfile.objects.create(
                user=user,
                phone=tech_data['phone'],
                skills=tech_data['skills'],
                verification_status='approved',
                rating=tech_data['rating'],
                trust_score=tech_data['trust_score'],
                completed_jobs_count=tech_data['completed_jobs'],
                is_online=True,
                is_active=True
            )
            
            # Create location
            location = TechnicianLocation.objects.create(
                technician=user,
                address=f"{tech_data['city']}, Kenya",
                city=tech_data['city'],
                latitude=tech_data['lat'],
                longitude=tech_data['lng'],
                service_radius_km=10
            )
            
            print(f"✅ Created technician: {tech_data['first_name']} {tech_data['last_name']}")
    
    print("\n🎉 Test data created successfully!")
    print("\n📊 Summary:")
    print(f"   Total Technicians: {TechnicianProfile.objects.filter(verification_status='approved').count()}")
    print(f"   Active Technicians: {TechnicianProfile.objects.filter(is_active=True).count()}")
    print("\n🔐 Login credentials for all technicians:")
    print("   Password: Test1234!")
    print("\n🌐 Test the API:")
    print("   GET http://localhost:8000/api/technicians/top/")
    
except Exception as e:
    print(f"\n❌ Error creating test data: {e}")
    import traceback
    traceback.print_exc()
