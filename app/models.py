# models.py
from django.db import models
from django.core.validators import EmailValidator
from django.utils import timezone


class ContactMessage(models.Model):
    """
    Model to store contact form messages from users
    """
    
    SUBJECT_CHOICES = [
        ('general', 'General Inquiry'),
        ('support', 'Customer Support'),
        ('partnership', 'Partnership'),
        ('feedback', 'Feedback'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('read', 'Read'),
        ('replied', 'Replied'),
        ('closed', 'Closed'),
    ]
    
    # User Information
    first_name = models.CharField(
        max_length=100,
        verbose_name="First Name",
        help_text="User's first name"
    )
    
    last_name = models.CharField(
        max_length=100,
        verbose_name="Last Name",
        help_text="User's last name"
    )
    
    email = models.EmailField(
        verbose_name="Email Address",
        validators=[EmailValidator()],
        help_text="User's email address"
    )
    
    # Message Details
    subject = models.CharField(
        max_length=20,
        choices=SUBJECT_CHOICES,
        verbose_name="Subject",
        help_text="Message subject category"
    )
    
    message = models.TextField(
        verbose_name="Message",
        help_text="User's message content"
    )
    
    # System Fields
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='new',
        verbose_name="Status",
        help_text="Current status of the message"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
        help_text="When the message was submitted"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At",
        help_text="When the message was last updated"
    )
    
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="IP Address",
        help_text="User's IP address when message was sent"
    )
    
    user_agent = models.TextField(
        null=True,
        blank=True,
        verbose_name="User Agent",
        help_text="User's browser information"
    )
    
    class Meta:
        verbose_name = "Contact Message"
        verbose_name_plural = "Contact Messages"
        ordering = ['-created_at']
        db_table = 'contact_messages'
        
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.get_subject_display()}"
    
    @property
    def full_name(self):
        """Return the full name of the user"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_new(self):
        """Check if the message is new/unread"""
        return self.status == 'new'
    
    @property
    def days_since_created(self):
        """Calculate days since message was created"""
        return (timezone.now() - self.created_at).days
    
    def mark_as_read(self):
        """Mark message as read"""
        self.status = 'read'
        self.save(update_fields=['status', 'updated_at'])
    
    def mark_as_replied(self):
        """Mark message as replied"""
        self.status = 'replied'
        self.save(update_fields=['status', 'updated_at'])
    
    def close_message(self):
        """Close the message"""
        self.status = 'closed'
        self.save(update_fields=['status', 'updated_at'])


class Waitlist(models.Model):
    """
    Model to store waitlist entries from users
    """
    
    # User Information
    name = models.CharField(
        max_length=150,
        verbose_name="Full Name",
        help_text="User's full name"
    )
    
    email = models.EmailField(
        unique=True,
        verbose_name="Email Address",
        validators=[EmailValidator()],
        help_text="User's email address"
    )
    
    phone_number = models.CharField(
        max_length=20,
        verbose_name="Phone Number",
        help_text="User's phone number"
    )
    
    message = models.TextField(
        blank=True,
        null=True,
        verbose_name="Message",
        help_text="Optional message from user"
    )
    
    # Communication Status
    is_email_sent = models.BooleanField(
        default=False,
        verbose_name="Email Sent",
        help_text="Whether welcome email has been sent"
    )
    
    is_in_whatsapp_channel = models.BooleanField(
        default=False,
        verbose_name="In WhatsApp Channel",
        help_text="Whether user is added to WhatsApp channel"
    )
    
    is_in_whatsapp_group = models.BooleanField(
        default=False,
        verbose_name="In WhatsApp Group",
        help_text="Whether user is added to WhatsApp group"
    )
    
    is_notified = models.BooleanField(
        default=False,
        verbose_name="Notified",
        help_text="Whether user has been notified about updates"
    )
    
    is_store = models.BooleanField(
        default=False,
        verbose_name="Store",
        help_text="Whether user is interested in store/shop"
    )
    
    # System Fields
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
        help_text="When the user joined waitlist"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At",
        help_text="When the record was last updated"
    )
    
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="IP Address",
        help_text="User's IP address when joined"
    )
    
    user_agent = models.TextField(
        null=True,
        blank=True,
        verbose_name="User Agent",
        help_text="User's browser information"
    )
    
    class Meta:
        verbose_name = "Waitlist Entry"
        verbose_name_plural = "Waitlist Entries"
        ordering = ['-created_at']
        db_table = 'waitlist_entries'
    
    def __str__(self):
        return f"{self.name} - {self.email}"
    
    @property
    def days_since_joined(self):
        """Calculate days since user joined waitlist"""
        return (timezone.now() - self.created_at).days
    
    @property
    def communication_status(self):
        """Get summary of communication status"""
        status = []
        if self.is_email_sent:
            status.append("Email Sent")
        if self.is_in_whatsapp_channel:
            status.append("WhatsApp Channel")
        if self.is_in_whatsapp_group:
            status.append("WhatsApp Group")
        if self.is_notified:
            status.append("Notified")
        if self.is_store:
            status.append("Store Interest")
        return ", ".join(status) if status else "No Communication"
    
    def mark_email_sent(self):
        """Mark email as sent"""
        self.is_email_sent = True
        self.save(update_fields=['is_email_sent', 'updated_at'])
    
    def add_to_whatsapp_channel(self):
        """Mark user as added to WhatsApp channel"""
        self.is_in_whatsapp_channel = True
        self.save(update_fields=['is_in_whatsapp_channel', 'updated_at'])
    
    def add_to_whatsapp_group(self):
        """Mark user as added to WhatsApp group"""
        self.is_in_whatsapp_group = True
        self.save(update_fields=['is_in_whatsapp_group', 'updated_at'])
    
    def mark_notified(self):
        """Mark user as notified"""
        self.is_notified = True
        self.save(update_fields=['is_notified', 'updated_at'])
    
    def mark_store_interest(self):
        """Mark user as interested in store"""
        self.is_store = True
        self.save(update_fields=['is_store', 'updated_at'])