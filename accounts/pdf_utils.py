from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO


def generate_bank_statement(customer, transactions):

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)

    y = 800

    p.setFont("Helvetica-Bold", 18)
    p.drawString(180, y, "SmartBank Pro")

    y -= 40
    p.setFont("Helvetica", 12)

    p.drawString(50, y, f"Customer Name : {customer.full_name}")
    y -= 20

    p.drawString(50, y, f"Account Number : {customer.account_number}")
    y -= 20

    p.drawString(50, y, f"Current Balance : ₹ {customer.balance}")
    y -= 40

    p.setFont("Helvetica-Bold", 13)
    p.drawString(50, y, "Transaction History")

    y -= 30
    p.setFont("Helvetica", 11)

    for transaction in transactions:

        p.drawString(
            50,
            y,
            f"{transaction.created_at.strftime('%d-%m-%Y')} | "
            f"{transaction.transaction_type} | "
            f"₹ {transaction.amount}"
        )

        y -= 20

        if y < 50:
            p.showPage()
            y = 800

    p.save()

    pdf = buffer.getvalue()
    buffer.close()

    return pdf