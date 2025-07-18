# views.py
from django.shortcuts import render
from django.http import HttpResponseNotFound, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .models import ContactMessage




def index(request):
    """
    Simple view that only returns HTML template
    """
    return render(request, 'index1.html')



def nowcloset_waitlist(request):
    """
    Simple view that only returns HTML template
    """
    return render(request, 'nowcloset_waitlist.html')



def about(request):
    """
    Simple view that only returns HTML template
    """
    return render(request, 'about.html')




def contact_view(request):
    """
    Simple view that only returns HTML template
    """
    return render(request, 'contact/contact_form.html')


@csrf_exempt
@require_http_methods(["POST"])
def contact_api(request):
    """
    API view to save contact data
    """
    try:
        # Get JSON data from request
        data = json.loads(request.body)
        
        # Create contact message
        contact_message = ContactMessage.objects.create(
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            email=data.get('email', ''),
            subject=data.get('subject', ''),
            message=data.get('message', ''),
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Contact message saved successfully',
            'id': contact_message.id
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


def get_client_ip(request):
    """
    Get client's IP address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip



# views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from .models import Waitlist
import re

def validate_phone_number(phone):
    """Simple phone number validation"""
    # Remove all non-digit characters
    cleaned_phone = re.sub(r'[^\d]', '', phone)
    
    # Check if it's between 10-15 digits
    if len(cleaned_phone) < 10 or len(cleaned_phone) > 15:
        return False
    return True


@api_view(['POST'])
@permission_classes([AllowAny])
def join_waitlist(request):
    """
    API endpoint to join waitlist
    
    Expected data:
    {
        "name": "John Doe",
        "email": "john@example.com",
        "phone_number": "+1234567890",
        "message": "Looking forward to the product!" (optional),
        "is_store": true (optional, default: false)
    }
    """
    try:
        # Get data from request
        data = request.data
        
        # Validate required fields
        required_fields = ['name', 'email', 'phone_number']
        for field in required_fields:
            if not data.get(field):
                return Response(
                    {
                        'success': False,
                        'error': f'{field} is required'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        name = data.get('name').strip()
        email = data.get('email').strip().lower()
        phone_number = data.get('phone_number').strip()
        message = data.get('message', '').strip()
        is_store = data.get('is_store', False)  # Optional boolean field
        
        # Validate name
        if len(name) < 2 or len(name) > 150:
            return Response(
                {
                    'success': False,
                    'error': 'Name must be between 2 and 150 characters'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate email
        try:
            validate_email(email)
        except ValidationError:
            return Response(
                {
                    'success': False,
                    'error': 'Please enter a valid email address'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate phone number
        if not validate_phone_number(phone_number):
            return Response(
                {
                    'success': False,
                    'error': 'Please enter a valid phone number'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if email already exists
        if Waitlist.objects.filter(email=email).exists():
            return Response(
                {
                    'success': False,
                    'error': 'This email is already on the waitlist'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create waitlist entry
        waitlist_entry = Waitlist.objects.create(
            name=name,
            email=email,
            phone_number=phone_number,
            message=message,
            is_store=is_store,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response(
            {
                'success': True,
                'message': 'Successfully joined the waitlist!',
                'data': {
                    'id': waitlist_entry.id,
                    'name': waitlist_entry.name,
                    'email': waitlist_entry.email,
                    'joined_at': waitlist_entry.created_at.isoformat()
                }
            },
            status=status.HTTP_201_CREATED
        )
        
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': 'An error occurred while processing your request'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def waitlist_stats(request):
    """
    API endpoint to get waitlist statistics (optional)
    """
    try:
        total_entries = Waitlist.objects.count()
        
        return Response(
            {
                'success': True,
                'data': {
                    'total_entries': total_entries,
                    'message': f'{total_entries} people have joined the waitlist!'
                }
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': 'An error occurred while fetching statistics'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    



# views.py
import csv
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.serializers import serialize
from django.utils import timezone
from .models import ContactMessage, Waitlist
import json


def admin_dashboard(request):
    """
    Render the admin dashboard page
    """
    return render(request, 'admin/dashboard.html')


@require_http_methods(["GET"])
def dashboard_data(request):
    """
    API endpoint to get all dashboard data in single call
    """
    try:
        # Get waitlist data
        waitlist_queryset = Waitlist.objects.all().order_by('-created_at')
        waitlist_data = []
        
        for item in waitlist_queryset:
            waitlist_data.append({
                'id': item.id,
                'name': item.name,
                'email': item.email,
                'phone_number': item.phone_number,
                'message': item.message,
                'is_email_sent': item.is_email_sent,
                'is_in_whatsapp_channel': item.is_in_whatsapp_channel,
                'is_in_whatsapp_group': item.is_in_whatsapp_group,
                'is_notified': item.is_notified,
                'is_store': item.is_store,
                'created_at': item.created_at.isoformat(),
                'updated_at': item.updated_at.isoformat(),
                'ip_address': item.ip_address,
                'user_agent': item.user_agent,
                'days_since_joined': item.days_since_joined,
                'communication_status': item.communication_status
            })
        
        # Get contact messages data
        contact_queryset = ContactMessage.objects.all().order_by('-created_at')
        contact_data = []
        
        for item in contact_queryset:
            contact_data.append({
                'id': item.id,
                'first_name': item.first_name,
                'last_name': item.last_name,
                'email': item.email,
                'subject': item.get_subject_display(),
                'message': item.message,
                'status': item.status,
                'created_at': item.created_at.isoformat(),
                'updated_at': item.updated_at.isoformat(),
                'ip_address': item.ip_address,
                'user_agent': item.user_agent,
                'full_name': item.full_name,
                'is_new': item.is_new,
                'days_since_created': item.days_since_created
            })
        
        response_data = {
            'waitlist': waitlist_data,
            'contact_messages': contact_data,
            'stats': {
                'total_waitlist': len(waitlist_data),
                'total_contact_messages': len(contact_data),
                'waitlist_email_sent': len([w for w in waitlist_data if w['is_email_sent']]),
                'waitlist_whatsapp_channel': len([w for w in waitlist_data if w['is_in_whatsapp_channel']]),
                'waitlist_store_interest': len([w for w in waitlist_data if w['is_store']]),
                'contact_new': len([c for c in contact_data if c['status'] == 'new']),
                'contact_read': len([c for c in contact_data if c['status'] == 'read']),
                'contact_replied': len([c for c in contact_data if c['status'] == 'replied']),
                'contact_closed': len([c for c in contact_data if c['status'] == 'closed']),
            }
        }
        
        return JsonResponse(response_data, safe=False)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def export_waitlist_csv(request):
    """
    Export waitlist data as CSV
    """
    try:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="waitlist-data-{timezone.now().strftime("%Y-%m-%d")}.csv"'
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow([
            'ID',
            'Name',
            'Email',
            'Phone Number',
            'Message',
            'Email Sent',
            'In WhatsApp Channel',
            'In WhatsApp Group',
            'Notified',
            'Store Interest',
            'Created At',
            'Updated At',
            'IP Address',
            'User Agent',
            'Days Since Joined',
            'Communication Status'
        ])
        
        # Write data
        waitlist_items = Waitlist.objects.all().order_by('-created_at')
        for item in waitlist_items:
            writer.writerow([
                item.id,
                item.name,
                item.email,
                item.phone_number,
                item.message,
                item.is_email_sent,
                item.is_in_whatsapp_channel,
                item.is_in_whatsapp_group,
                item.is_notified,
                item.is_store,
                item.created_at.isoformat(),
                item.updated_at.isoformat(),
                item.ip_address,
                item.user_agent,
                item.days_since_joined,
                item.communication_status
            ])
        return response

    except Exception as e:
        return HttpResponse(f"Error exporting waitlist: {str(e)}", status=500)


# Export contact messages as CSV
@require_http_methods(["GET"])
def export_contact_csv(request):
    """
    Export contact messages as CSV
    """
    try:
        response = HttpResponse(content_type='text/csv')
        date_str = timezone.now().strftime('%Y-%m-%d')
        response['Content-Disposition'] = f'attachment; filename="contact-messages-{date_str}.csv"'

        writer = csv.writer(response)

        # Write header
        writer.writerow([
            'ID',
            'First Name',
            'Last Name',
            'Email',
            'Subject',
            'Message',
            'Status',
            'Created At',
            'Updated At',
            'IP Address',
            'User Agent',
            'Days Since Created',
            'Is New',
            'Full Name'
        ])

        # Write data
        contact_items = ContactMessage.objects.all().order_by('-created_at')
        for item in contact_items:
            writer.writerow([
                item.id,
                item.first_name,
                item.last_name,
                item.email,
                item.get_subject_display(),
                item.message,
                item.status,
                item.created_at.isoformat(),
                item.updated_at.isoformat(),
                item.ip_address,
                item.user_agent,
                item.days_since_created,
                item.is_new,
                item.full_name
            ])
        return response

    except Exception as e:
        return HttpResponse(f"Error exporting contact messages: {str(e)}", status=500)
