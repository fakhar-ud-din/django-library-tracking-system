from celery import shared_task
from datetime import datetime
from django.db.models import Q

from .models import Loan
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_loan_notification(loan_id):
    try:
        loan = Loan.objects.get(id=loan_id)
        member_email = loan.member.user.email
        book_title = loan.book.title
        send_mail(
            subject='Book Loaned Successfully',
            message=f'Hello {loan.member.user.username},\n\nYou have successfully loaned "{book_title}".\nPlease return it by the due date.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[member_email],
            fail_silently=False,
        )
    except Loan.DoesNotExist:
        pass

@shared_task
def send_overdue_loan_notification(loan_id, user_email, username, book_title):
    send_mail(
        subject=f'Overdue loan - Return {book_title}',
        message=f'Hello {username},\n\Please return loaned book "{book_title}".\n',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user_email],
        fail_silently=False,
    )

@shared_task
def check_overdue_loans():
    todays_date = datetime.now()
    overdue_loans = Loan.objects.filter(Q(due_date__lt=todays_date), is_returned=False)
    
    for loan in overdue_loans:
        send_overdue_loan_notification.delay(
            loan.id, loan.member.user.email, 
            loan.member.user.username, loan.book.title
            )