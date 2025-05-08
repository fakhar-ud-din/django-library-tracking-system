from datetime import datetime, timedelta, date

from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Author, Book, Member, Loan
from .serializers import AuthorSerializer, BookSerializer, MemberSerializer, LoanSerializer
from rest_framework.decorators import action
from django.utils import timezone
from django.db.models import Count
from .tasks import send_loan_notification

class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    @action(detail=True, methods=['post'])
    def loan(self, request, pk=None):
        book = self.get_object()
        if book.available_copies < 1:
            return Response({'error': 'No available copies.'}, status=status.HTTP_400_BAD_REQUEST)
        member_id = request.data.get('member_id')
        try:
            member = Member.objects.get(id=member_id)
        except Member.DoesNotExist:
            return Response({'error': 'Member does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
        loan = Loan.objects.create(book=book, member=member)
        book.available_copies -= 1
        book.save()
        send_loan_notification.delay(loan.id)
        return Response({'status': 'Book loaned successfully.'}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def return_book(self, request, pk=None):
        book = self.get_object()
        member_id = request.data.get('member_id')
        try:
            loan = Loan.objects.get(book=book, member__id=member_id, is_returned=False)
        except Loan.DoesNotExist:
            return Response({'error': 'Active loan does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
        loan.is_returned = True
        loan.return_date = timezone.now().date()
        loan.save()
        book.available_copies += 1
        book.save()
        return Response({'status': 'Book returned successfully.'}, status=status.HTTP_200_OK)

class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer
    
    @action(detail=False)
    def top_active(self, request):
        top_members = Member.objects.annotate(number_of_loans=Count('loans')).order_by('number_of_loans')
        if len(top_members) > 5:
            top_members = top_members[:5]
        
        response_data = []
        for mem in top_members:
            response_data.append({
                'id': mem.user.id,
                'email': mem.user.email,
                'username': mem.user.username,
                'active_loans': mem.number_of_loans
            })
        
        return Response(data=response_data, status=status.HTTP_200_OK)

class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer
    
    @action(detail=True, methods=['post'])
    def extend_due_date(self, request, pk=None):
        loan = self.get_object()
        if loan.due_date < date.today():
            return Response(
                {'error': 'Loan already overdue. Cannot extend the deadline'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        extend_days = request.data.get('additional_days')
        if extend_days and extend_days < 0:
            return Response(
                {'error': 'Please provide a positive integer for days.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        print(f"Old due date: {loan.due_date}")
        loan.due_date = datetime.now() + timedelta(days=extend_days)
        loan.save()
        print(f"New due date: {loan.due_date}")
        
        return Response({'due_date': loan.due_date}, status=status.HTTP_200_OK)
