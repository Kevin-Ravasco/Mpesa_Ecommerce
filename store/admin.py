from django.contrib import admin

from .models import Customer, Product, Order, OrderItem, ShippingAddress


class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'email']


class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'digital', 'image']
    search_fields = ['name', 'price', 'digital', 'image']
    list_filter = ['price', 'digital']


class OrderAdmin(admin.ModelAdmin):
    list_display = ['customer', 'date_ordered', 'complete']


class ShippingAdmin(admin.ModelAdmin):
    list_display = ['customer', 'order', 'city', 'state', 'zipcode', 'date_added']


admin.site.register(Customer, CustomerAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem)
admin.site.register(ShippingAddress, ShippingAdmin)