from celery import shared_task
from django.core.cache import cache
from apps.technicians.models import TechnicianProfile, TechnicianLocation
from apps.accounts.email_service import send_booking_notification
import logging

logger = logging.getLogger(__name__)


@shared_task
def match_technicians(booking_id):
    """
    Match technicians to a booking based on:
    - Skills/category
    - Location/distance
    - Rating
    - Online status
    """
    from apps.bookings.models import Booking
    
    try:
        booking = Booking.objects.select_related('user').get(id=booking_id)
        
        # Find technicians with matching skills and approved status
        technicians = TechnicianProfile.objects.filter(
            verification_status='approved',
            skills__contains=[booking.category],
            is_online=True
        ).select_related('user')
        
        # Calculate distances and filter by service area
        matched_technicians = []
        for tech_profile in technicians:
            try:
                tech_location = TechnicianLocation.objects.get(technician=tech_profile.user)
                distance = TechnicianLocation.calculate_distance(
                    tech_location.latitude,
                    tech_location.longitude,
                    booking.latitude,
                    booking.longitude
                )
                
                if distance <= tech_location.service_radius_km:
                    matched_technicians.append({
                        'technician_id': tech_profile.user.id,
                        'distance': distance,
                        'rating': float(tech_profile.rating)
                    })
            except TechnicianLocation.DoesNotExist:
                continue
        
        # Sort by rating (desc) then distance (asc)
        matched_technicians.sort(key=lambda x: (-x['rating'], x['distance']))
        
        # Store matched technicians in Redis for 1 hour
        cache_key = f"booking:{booking_id}:matched_technicians"
        cache.set(cache_key, matched_technicians[:10], 3600)  # Top 10 technicians
        
        # Notify top technicians (implement push notification here)
        for match in matched_technicians[:5]:  # Notify top 5
            logger.info(f"Notifying technician {match['technician_id']} about booking {booking_id}")
            # TODO: Implement push notification
        
        logger.info(f"Matched {len(matched_technicians)} technicians for booking {booking_id}")
        return {
            'booking_id': booking_id,
            'matched_count': len(matched_technicians),
            'top_matches': matched_technicians[:5]
        }
        
    except Booking.DoesNotExist:
        logger.error(f"Booking {booking_id} not found")
        return None
    except Exception as e:
        logger.error(f"Error matching technicians for booking {booking_id}: {e}")
        raise


@shared_task
def notify_user_booking_update(booking_id, event):
    """Notify user about booking status update"""
    from apps.bookings.models import Booking
    
    try:
        booking = Booking.objects.select_related('user').get(id=booking_id)
        send_booking_notification(booking.user.email, booking_id, event)
        logger.info(f"Notified user {booking.user.email} about booking {booking_id} - {event}")
        return True
    except Booking.DoesNotExist:
        logger.error(f"Booking {booking_id} not found")
        return False
    except Exception as e:
        logger.error(f"Error notifying user for booking {booking_id}: {e}")
        raise
