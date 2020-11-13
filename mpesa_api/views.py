import datetime

from django.contrib import messages
from django.http import HttpResponse, JsonResponse
import requests
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from requests.auth import HTTPBasicAuth
import json

from store.models import Order
from store.utils import guestOrder
from .models import MpesaPayment, LipaNaMpesaOnline
from .mpesa_credentials import MpesaAccessToken, LipanaMpesaPassword
from .ngrok import NgrokAPIEndpoints
from store.forms import MpesaPaymentForm


def lipa_na_mpesa_online(request):
    customer = request.user.customer
    order = Order.objects.filter(customer=customer, complete=False).first()
    total = order.get_cart_total

    if request.method == 'POST':
        form = MpesaPaymentForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data['phone']
            access_token = MpesaAccessToken.validated_mpesa_access_token
            api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
            headers = {"Authorization": "Bearer %s" % access_token}
            req = {
                "BusinessShortCode": LipanaMpesaPassword.Business_short_code,
                "Password": LipanaMpesaPassword.decode_password,
                "Timestamp": LipanaMpesaPassword.lipa_time,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": 1,
                "PartyA": phone,  # replace with your phone number to get stk push
                "PartyB": LipanaMpesaPassword.Business_short_code,
                "PhoneNumber": phone,  # replace with your phone number to get stk push
                "CallBackURL": "https://sandbox.safaricom.co.ke/mpesa/",
                "AccountReference": "Ecomm Store",
                "TransactionDesc": "Ecomm Store"
            }
            response = requests.post(api_url, json=req, headers=headers)
    messages.success(request, 'Please enter your M-Pesa pin on your phone to complete the payment')
    return redirect(reverse('checkout'))


@csrf_exempt
def register_urls(request):  # We use this method to register our confirmation and validation URL with Safaricom.
    access_token = MpesaAccessToken.validated_mpesa_access_token
    api_url = "https://sandbox.safaricom.co.ke/mpesa/c2b/v1/registerurl"  # we pass the mpesa URL for registering the urls.
    headers = {"Authorization": "Bearer %s" % access_token}  # we pass our mpesa tokens to the header of the request.
    options = {"ShortCode": 600247,
               "ResponseType": "Completed",
               "ConfirmationURL": NgrokAPIEndpoints.ConfirmationUrl,
               # using secure ngrok endpoints, replace with your generated ngrok endpoint
               "ValidationURL": NgrokAPIEndpoints.ValidationUrl}  # using secure ngrok endpoints, replace with your generated ngrok endpoint
    response = requests.post(api_url, json=options, headers=headers)
    return HttpResponse(response.text)


@csrf_exempt
def call_back(request):
    merchant_id = request.data['Body']['stkCallback']['MerchantRequestID']
    checkout_id = request.data['Body']['stkCallback']['CheckoutRequestID']
    result_description = request.data['Body']['stkCallback']['ResultDesc']
    amount = request.data['Body']['stkCallback']['CallbackMetadata']['Item'][0]['Value']
    receipt_no = request.data['Body']['stkCallback']['CallbackMetadata']['Item'][1]['Value']
    date = request.data['Body']['stkCallback']['CallbackMetadata']['Item'][3]['Value']
    phone_number = request.data['Body']['stkCallback']['CallbackMetadata']['Item'][4]['Value']

    transaction = LipaNaMpesaOnline(
        checkout_request_ID=checkout_id,
        merchant_request_ID=merchant_id,
        result_desc=result_description,
        amount=amount,
        receipt_number=receipt_no,
        transaction_date=date,
        phone_number=phone_number,
    )
    transaction.save()
    transaction_id = datetime.datetime.now().timestamp()
    data = json.loads(request.body)

    if request.user.is_authenticated:
        customer = request.user.customer
        order, created = Order.objects.get_or_create(customer=customer, complete=False)
    else:
        customer, order = guestOrder(request, data)

    order.transaction_id = transaction_id

    if amount == order.get_cart_total:
        order.complete = True
    order.save()

    return redirect(reverse('checkout'))


@csrf_exempt
def validation(request):
    context = {
        "ResultCode": 0,  # Note if change 0 to any other number, you reject the payment
        "ResultDesc": "Accepted"
    }
    return JsonResponse(dict(context))  # we turn our context to json format since Mpesa expects json format.


@csrf_exempt
def confirmation(request):  # we use this function to save successfully transaction in our database.
    mpesa_body = request.body.decode('utf-8')  # we get the mpesa transaction from the body by decoding using utf-8
    mpesa_payment = json.loads(
        mpesa_body)  # we use json.loads method which will assist us to access variables in our request.
    payment = MpesaPayment(
        first_name=mpesa_payment['FirstName'],
        last_name=mpesa_payment['LastName'],
        middle_name=mpesa_payment['MiddleName'],
        description=mpesa_payment['TransID'],
        phone_number=mpesa_payment['MSISDN'],
        amount=mpesa_payment['TransAmount'],
        reference=mpesa_payment['BillRefNumber'],
        organization_balance=mpesa_payment['OrgAccountBalance'],
        type=mpesa_payment['TransactionType'],
    )
    payment.save()
    context = {
        "ResultCode": 0,
        "ResultDesc": "Accepted"
    }
    return JsonResponse(dict(context))
