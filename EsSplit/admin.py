from django.contrib import admin
from django.contrib import admin
from .models import Bill, Person, Friend

# To sprawia, że tabele są widoczne w panelu
admin.site.register(Bill)
admin.site.register(Friend)
admin.site.register(Person)
