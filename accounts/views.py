from decimal import Decimal
import random
import google.generativeai as genai
from django.conf import settings
from .models import Customer, Transaction
from openpyxl import Workbook
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum
from .forms import UserRegistrationForm, CustomerForm
from .pdf_utils import generate_bank_statement
from django.http import JsonResponse
from django.db.models import Sum
import json
from django.contrib.auth.decorators import login_required

@login_required
def profile(request):

    customer = Customer.objects.get(user=request.user)

    return render(request, "profile.html", {
        "customer": customer
    })
@login_required
def ask_ai(request):

    if request.method == "POST":

        data = json.loads(request.body)

        question = data.get("message")

        customer = request.user.customer

        # Last 5 Transactions
        transactions = Transaction.objects.filter(
            customer=customer
        ).order_by("-created_at")[:5]

        transaction_history = ""

        for t in transactions:

            transaction_history += f"""
Type : {t.transaction_type}
Amount : ₹{t.amount}
Status : {t.status}
Date : {t.created_at.strftime("%d-%m-%Y %H:%M")}
Receiver : {t.receiver_account}
--------------------------------
"""

        # Totals
        total_deposit = Transaction.objects.filter(
            customer=customer,
            transaction_type="Deposit"
        ).aggregate(total=Sum("amount"))["total"] or 0

        total_withdraw = Transaction.objects.filter(
            customer=customer,
            transaction_type="Withdraw"
        ).aggregate(total=Sum("amount"))["total"] or 0

        total_transfer = Transaction.objects.filter(
            customer=customer,
            transaction_type="Transfer"
        ).aggregate(total=Sum("amount"))["total"] or 0

        prompt = f"""
You are SmartBank Pro AI Assistant.

Customer Details

Name : {customer.full_name}

Account Number : {customer.account_number}

Account Type : {customer.account_type}

Current Balance : ₹{customer.balance}

Total Deposited : ₹{total_deposit}

Total Withdrawn : ₹{total_withdraw}

Total Transferred : ₹{total_transfer}

Recent Transactions

{transaction_history}

Rules

1. Answer ONLY using the above banking data.

2. If the user asks balance, use Current Balance.

3. If the user asks deposits, use Total Deposited.

4. If the user asks withdrawals, use Total Withdrawn.

5. If the user asks transfers, use Total Transferred.

6. If the user asks recent transactions, summarize them.

7. Never make up banking information.

Customer Question:

{question}
"""

        model = genai.GenerativeModel("gemini-2.5-flash")

        response = model.generate_content(prompt)

        return JsonResponse({
            "reply": response.text
        })

    return JsonResponse({
        "reply": "Invalid Request"
    })
from .models import Customer, Transaction
genai.configure(api_key=settings.GEMINI_API_KEY)
from django.http import HttpResponse

def test_ai(request):
    return HttpResponse("AI Test Working")
@login_required
def chatbot(request):
    return render(request, "chatbot.html")
@login_required
def transaction_history(request):

    customer = request.user.customer

    transactions = customer.transactions.order_by("-created_at")

    search = request.GET.get("search")

    from_date = request.GET.get("from_date")
    to_date = request.GET.get("to_date")

    if search:
        transactions = transactions.filter(
            transaction_type__icontains=search
        )

    if from_date:
        transactions = transactions.filter(
            created_at__date__gte=from_date
        )

    if to_date:
        transactions = transactions.filter(
            created_at__date__lte=to_date
        )

    return render(
        request,
        "transaction_history.html",
        {
            "transactions": transactions,
            "search": search,
            "from_date": from_date,
            "to_date": to_date,
        }
    )
@login_required
def deposit(request):

    if request.method == "POST":

        try:
            amount = Decimal(request.POST.get("amount"))

            if amount <= 0:
                messages.error(request, "Amount must be greater than zero.")
                return redirect("dashboard")

            customer = request.user.customer
            customer.balance += amount
            customer.save()

            Transaction.objects.create(
                customer=customer,
                transaction_type="Deposit",
                amount=amount,
                balance_after=customer.balance,
                status="Success"
            )

            messages.success(request, "₹{} deposited successfully.".format(amount))

        except Exception as e:
            messages.error(request, str(e))

    return redirect("dashboard")

@login_required
def withdraw(request):

    if request.method == "POST":

        try:

            amount = Decimal(request.POST.get("amount"))
            customer = request.user.customer

            if amount <= 0:
                messages.error(request, "Amount must be greater than zero.")
                return redirect("dashboard")

            if customer.balance < amount:
                messages.error(request, "Insufficient Balance.")
                return redirect("dashboard")

            customer.balance -= amount
            customer.save()

            Transaction.objects.create(
                customer=customer,
                transaction_type="Withdraw",
                amount=amount,
                balance_after=customer.balance,
                status="Success"
            )

            messages.success(request, "₹{} withdrawn successfully.".format(amount))

        except Exception as e:
            messages.error(request, str(e))

    return redirect("dashboard")

def generate_account_number():
    """
    Generate a unique account number.
    Example: SBP12345678
    """

    while True:
        account_number = "SBP" + str(random.randint(10000000, 99999999))

        if not Customer.objects.filter(account_number=account_number).exists():
            return account_number

def register(request):

    if request.method == "POST":

        user_form = UserRegistrationForm(request.POST)
        customer_form = CustomerForm(request.POST)

        if user_form.is_valid() and customer_form.is_valid():

            user = user_form.save(commit=False)
            user.set_password(user_form.cleaned_data["password"])
            user.save()

            customer = customer_form.save(commit=False)
            customer.user = user
            customer.email = user.email
            customer.account_number = generate_account_number()
            customer.save()

            messages.success(request, "Registration successful. Please login.")

            return redirect("login")

    else:

        user_form = UserRegistrationForm()
        customer_form = CustomerForm()

    return render(request, "register.html", {
        "user_form": user_form,
        "customer_form": customer_form
    })

def login_view(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user:

            login(request, user)

            return redirect("dashboard")

        else:

            messages.error(request, "Invalid username or password.")

    return render(request, "login.html")

@login_required
def dashboard(request):

    customer = request.user.customer

    transactions = customer.transactions.order_by("-created_at")[:5]

    total_deposit = customer.transactions.filter(
        transaction_type="Deposit"
    ).aggregate(total=Sum("amount"))["total"] or 0

    total_withdraw = customer.transactions.filter(
        transaction_type="Withdraw"
    ).aggregate(total=Sum("amount"))["total"] or 0

    total_transfer = customer.transactions.filter(
        transaction_type="Transfer"
    ).aggregate(total=Sum("amount"))["total"] or 0

    last_transaction = customer.transactions.order_by("-created_at").first()

    # AI Financial Insights
    net_savings = total_deposit - total_withdraw

    if total_deposit > 0:
        savings_rate = round((net_savings / total_deposit) * 100, 2)
    else:
        savings_rate = 0

    if savings_rate >= 70:
        ai_message = "Excellent savings habit. Keep it up! 🎉"
    elif savings_rate >= 40:
        ai_message = "Good financial management. 👍"
    else:
        ai_message = "Try to reduce unnecessary spending. 💡"

    context = {
        "customer": customer,
        "transactions": transactions,
        "total_deposit": total_deposit,
        "total_withdraw": total_withdraw,
        "total_transfer": total_transfer,
        "total_transactions": customer.transactions.count(),
        "last_transaction": last_transaction,

        # AI Insights
        "net_savings": net_savings,
        "savings_rate": savings_rate,
        "ai_message": ai_message,
    }

    return render(request, "dashboard.html", context)


def home(request):
    return render(request, "home.html")

@login_required
def transfer_money(request):

    customer = request.user.customer

    if request.method == "POST":

        print("Transfer button clicked")

        try:

            receiver_account = request.POST.get("receiver_account").strip()
            remarks = request.POST.get("remarks")
            amount = Decimal(request.POST.get("amount"))

            if amount <= 0:
                messages.error(request, "Amount must be greater than zero.")
                return redirect("transfer")

            if receiver_account == customer.account_number:
                messages.error(request, "You cannot transfer to your own account.")
                return redirect("transfer")

            receiver = Customer.objects.filter(
                account_number=receiver_account
            ).first()

            if receiver is None:
                messages.error(request, "Receiver account not found.")
                return redirect("transfer")

            if customer.balance < amount:
                messages.error(request, "Insufficient balance.")
                return redirect("transfer")

            with transaction.atomic():

                customer.balance -= amount
                customer.save()

                receiver.balance += amount
                receiver.save()

                Transaction.objects.create(
                    customer=customer,
                    transaction_type="Transfer",
                    amount=amount,
                    balance_after=customer.balance,
                    receiver_account=receiver.account_number,
                    remarks=remarks,
                    status="Success"
                )

                Transaction.objects.create(
                    customer=receiver,
                    transaction_type="Received",
                    amount=amount,
                    balance_after=receiver.balance,
                    receiver_account=customer.account_number,
                    remarks=remarks,
                    status="Success"
                )

            messages.success(request, "Money transferred successfully.")

            return redirect("dashboard")

        except Exception as e:

            messages.error(request, str(e))

            return redirect("transfer")

    return render(request, "transfer.html")
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("login")
@staff_member_required
def admin_dashboard(request):

    total_customers = Customer.objects.count()

    total_balance = Customer.objects.aggregate(
        total=Sum("balance")
    )["total"] or 0

    total_deposit = Transaction.objects.filter(
        transaction_type="Deposit"
    ).aggregate(total=Sum("amount"))["total"] or 0

    total_withdraw = Transaction.objects.filter(
        transaction_type="Withdraw"
    ).aggregate(total=Sum("amount"))["total"] or 0

    total_transfer = Transaction.objects.filter(
        transaction_type="Transfer"
    ).aggregate(total=Sum("amount"))["total"] or 0

    context = {
        "total_customers": total_customers,
        "total_balance": total_balance,
        "total_deposit": total_deposit,
        "total_withdraw": total_withdraw,
        "total_transfer": total_transfer,
    }

    return render(request, "admin_dashboard.html", context)
from django.contrib.auth.decorators import login_required

@login_required
def download_statement_pdf(request):

    customer = request.user.customer

    transactions = customer.transactions.order_by("-created_at")

    pdf = generate_bank_statement(customer, transactions)

    response = HttpResponse(
        pdf,
        content_type="application/pdf"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="Statement_{customer.account_number}.pdf"'
    )

    return response


@login_required
def download_statement_excel(request):

    customer = request.user.customer

    transactions = customer.transactions.order_by("-created_at")

    workbook = Workbook()

    sheet = workbook.active

    sheet.title = "Bank Statement"

    sheet.append([
        "Date",
        "Transaction Type",
        "Amount",
        "Balance After",
        "Status"
    ])

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