from django import forms


class MpesaPaymentForm(forms.Form):
    phone = forms.IntegerField(label='Enter Number', widget=forms.NumberInput(
        attrs={'class': 'form-control', 'placeholder': 'format 2547123456789'}))