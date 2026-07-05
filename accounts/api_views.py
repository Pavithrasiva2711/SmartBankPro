from decimal import Decimal
from django.http import HttpResponse
from .pdf_utils import generate_bank_statement
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Sum
from rest_framework import filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from .serializers import ( RegisterSerializer, LoginSerializer, TransactionSerializer,)
from .models import Customer, Transaction
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListAPIView
from django_filters.rest_framework import DjangoFilterBackend
from django.core.mail import send_mail
from rest_framework.permissions import AllowAny
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from openpyxl import Workbook
class RegisterAPIView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):

        serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():

            # Save User and Customer
            user = serializer.save()
            customer = user.customer

            # Load HTML Template
            html_content = render_to_string(
                "emails/welcome_email.html",
                {
                    "customer": customer
                }
            )

            # Plain Text Version
            text_content = strip_tags(html_content)

            # Create Email
            email = EmailMultiAlternatives(
                subject="Welcome to SmartBank Pro",
                body=text_content,
                from_email=None,
                to=[user.email],
            )

            # Attach HTML
            email.attach_alternative(html_content, "text/html")

            # Send Email
            email.send()

            return Response(
                {
                    "message": "Customer Registered Successfully"
                },
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
class LoginAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):

        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():

            user = serializer.validated_data["user"]

            return Response({
                "message": "Login Successful",
                "username": user.username,
                "full_name": user.customer.full_name,
                "account_number": user.customer.account_number,
                "balance": str(user.customer.balance)
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)  
class DashboardAPIView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):

        customer = request.user.customer

        transactions = customer.transactions.order_by("-created_at")[:5]

        total_deposit = customer.transactions.filter(
            transaction_type="Deposit"
        ).aggregate(total=Sum("amount"))["total"] or 0

        total_withdraw = customer.transactions.filter(
            transaction_type="Withdraw"
        ).aggregate(total=Sum("amount"))["total"] or 0

        return Response({

            "customer_name": customer.full_name,
            "account_number": customer.account_number,
            "account_type": customer.account_type,
            "balance": customer.balance,
            "total_deposit": total_deposit,
            "total_withdraw": total_withdraw,
            "total_transactions": customer.transactions.count(),

            "recent_transactions": [
                {
                    "type": t.transaction_type,
                    "amount": t.amount,
                    "balance_after": t.balance_after,
                    "date": t.created_at,
                    "status": t.status
                }
                for t in transactions
            ]
        })
class DepositAPIView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):

        customer = request.user.customer
        amount = Decimal(request.data.get("amount"))

        if amount <= 0:
            return Response(
                {"error": "Amount must be greater than zero."},
                status=status.HTTP_400_BAD_REQUEST
            )

        customer.balance += amount
        customer.save()

        Transaction.objects.create(
            customer=customer,
            transaction_type="Deposit",
            amount=amount,
            balance_after=customer.balance,
            status="Success"
        )
        print("Customer Email:", customer.email)
        # Send Email
        send_mail(
            subject="Deposit Successful - SmartBank Pro",
            message=f"""
Dear {customer.full_name},

Your deposit has been processed successfully.

Transaction Details
----------------------------
Amount Deposited : ₹{amount}
Current Balance  : ₹{customer.balance}

Thank you for banking with SmartBank Pro.

Regards,
SmartBank Pro Team
""",
            from_email=None,
            recipient_list=[customer.user.email],
            fail_silently=False,
        )

        return Response({
            "message": "Deposit Successful",
            "new_balance": customer.balance
        })
class WithdrawAPIView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):

        customer = request.user.customer
        amount = Decimal(request.data.get("amount"))

        if amount <= 0:
            return Response(
                {"error": "Amount must be greater than zero."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if customer.balance < amount:
            return Response(
                {"error": "Insufficient Balance."},
                status=status.HTTP_400_BAD_REQUEST
            )

        customer.balance -= amount
        customer.save()

        Transaction.objects.create(
            customer=customer,
            transaction_type="Withdraw",
            amount=amount,
            balance_after=customer.balance,
            status="Success"
        )

        send_mail(
            subject="Withdrawal Successful - SmartBank Pro",
            message=f"""
Dear {customer.full_name},

Your withdrawal has been processed successfully.

Transaction Details
----------------------------
Amount Withdrawn : ₹{amount}
Current Balance  : ₹{customer.balance}

Thank you for banking with SmartBank Pro.

Regards,
SmartBank Pro Team
""",
            from_email=None,
            recipient_list=[customer.user.email],
            fail_silently=False,
        )

        return Response(
            {
                "message": "Withdrawal Successful",
                "new_balance": customer.balance
            },
            status=status.HTTP_200_OK
        )
class TransferAPIView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):

        sender = request.user.customer
        receiver_account = request.data.get("receiver_account")
        amount = Decimal(request.data.get("amount"))
        remarks = request.data.get("remarks", "")

        try:
            receiver = Customer.objects.get(account_number=receiver_account)

            if amount <= 0:
                return Response(
                    {"error": "Amount must be greater than zero."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if sender.account_number == receiver.account_number:
                return Response(
                    {"error": "Cannot transfer to your own account."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if sender.balance < amount:
                return Response(
                    {"error": "Insufficient balance."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            with transaction.atomic():

                sender.balance -= amount
                sender.save()

                receiver.balance += amount
                receiver.save()

                sender_transaction = Transaction.objects.create(
                    customer=sender,
                    transaction_type="Transfer",
                    amount=amount,
                    balance_after=sender.balance,
                    receiver_account=receiver.account_number,
                    remarks=remarks,
                    status="Success"
                )

                Transaction.objects.create(
                    customer=receiver,
                    transaction_type="Received",
                    amount=amount,
                    balance_after=receiver.balance,
                    receiver_account=sender.account_number,
                    remarks=remarks,
                    status="Success"
                )

            # Send Email to Sender
            send_mail(
                subject="Money Transfer Successful - SmartBank Pro",
                message=f"""
Dear {sender.full_name},

Your money transfer has been completed successfully.

Transfer Details
----------------------------
Receiver Account : {receiver.account_number}
Amount Transferred : ₹{amount}
Current Balance : ₹{sender.balance}
Reference Number : {sender_transaction.reference_number}

Thank you for banking with SmartBank Pro.

Regards,
SmartBank Pro Team
""",
                from_email=None,
                recipient_list=[sender.user.email],
                fail_silently=False,
            )

            return Response({
                "message": "Money transferred successfully.",
                "sender_balance": sender.balance,
                "receiver_account": receiver.account_number
            })

        except Customer.DoesNotExist:
            return Response(
                {"error": "Receiver account not found."},
                status=status.HTTP_404_NOT_FOUND
            )
class TransactionPagination(PageNumberPagination):

    page_size = 5
    page_size_query_param = "page_size"
    max_page_size = 20
class TransactionHistoryAPIView(ListAPIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    serializer_class = TransactionSerializer
    pagination_class = TransactionPagination

    filter_backends = [
        filters.SearchFilter,
        DjangoFilterBackend,
        filters.OrderingFilter,
    ]

    search_fields = [
        "transaction_type",
        "remarks",
    ]

    filterset_fields = [
        "transaction_type",
        "status",
    ]

   
    ordering_fields = [
        "amount",
        "created_at",
        "transaction_type",
    ]

    ordering = ["-created_at"]

    def get_queryset(self):
        customer = self.request.user.customer
        return customer.transactions.order_by("-created_at")
class ProfileAPIView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):

        customer = request.user.customer

        return Response({
            "full_name": customer.full_name,
            "email": customer.email,
            "mobile": customer.mobile,
            "account_number": customer.account_number,
            "account_type": customer.account_type,
            "balance": customer.balance,
            "address": customer.address,
            "date_of_birth": customer.date_of_birth,
        })
class ChangePasswordAPIView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):

        user = request.user

        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")

        if not user.check_password(old_password):
            return Response(
                {"error": "Old password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()

        return Response({
            "message": "Password changed successfully."
        })
class UpdateProfileAPIView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):

        customer = request.user.customer

        customer.mobile = request.data.get("mobile", customer.mobile)
        customer.email = request.data.get("email", customer.email)
        customer.address = request.data.get("address", customer.address)

        customer.save()

        return Response({
            "message": "Profile updated successfully.",
            "profile": {
                "full_name": customer.full_name,
                "email": customer.email,
                "mobile": customer.mobile,
                "address": customer.address
            }
        })
class BalanceAPIView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):

        customer = request.user.customer

        return Response({
            "customer_name": customer.full_name,
            "account_number": customer.account_number,
            "account_type": customer.account_type,
            "available_balance": customer.balance
        })
class AccountStatementAPIView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):

        customer = request.user.customer

        transactions = customer.transactions.order_by("-created_at")

        return Response({
            "customer_name": customer.full_name,
            "account_number": customer.account_number,
            "statement": [
                {
                    "transaction_type": t.transaction_type,
                    "amount": t.amount,
                    "balance_after": t.balance_after,
                    "status": t.status,
                    "remarks": t.remarks,
                    "date": t.created_at,
                }
                for t in transactions
            ]
        })
class DeleteAccountAPIView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request):

        confirmation = request.data.get("confirmation")

        if confirmation != "DELETE":
            return Response(
                {
                    "error": "Type DELETE in confirmation field to deactivate your account."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user
        customer = user.customer

        user.is_active = False
        user.save()

        return Response({
            "message": "Account deactivated successfully.",
            "account_number": customer.account_number
        })
class BankStatementPDFAPIView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):

        customer = request.user.customer

        transactions = customer.transactions.order_by("-created_at")

        pdf = generate_bank_statement(customer, transactions)

        response = HttpResponse(pdf, content_type="application/pdf")

        response["Content-Disposition"] = (
            f'attachment; filename="Statement_{customer.account_number}.pdf"'
        )

        return response
class BankStatementExcelAPIView(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):

        customer = request.user.customer
        transactions = customer.transactions.all().order_by("-created_at")

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Bank Statement"

        # Header Row
        sheet.append([
            "Date",
            "Transaction Type",
            "Amount",
            "Balance After",
            "Status"
        ])

        # Transaction Data
        for transaction in transactions:
            sheet.append([
                transaction.created_at.strftime("%d-%m-%Y %H:%M"),
                transaction.transaction_type,
                float(transaction.amount),
                float(transaction.balance_after),
                transaction.status,
            ])

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        response["Content-Disposition"] = (
            'attachment; filename="Bank_Statement.xlsx"'
        )

        workbook.save(response)

        return response