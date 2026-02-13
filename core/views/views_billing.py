import razorpay
from django.conf import settings
from django.http import JsonResponse
from core.models import Institution, BillingRecord
from django.utils import timezone
from datetime import timedelta

client = razorpay.Client(auth=(settings.RAZORPAY_KEY, settings.RAZORPAY_SECRET))


def create_order(request, institution_id):

    institution = Institution.objects.get(id=institution_id)

    amount = 49900  # ₹499 Pro plan example (in paise)

    order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": "1"
    })

    return JsonResponse({
        "order_id": order["id"],
        "amount": amount,
        "key": settings.RAZORPAY_KEY
    })



