from django.contrib import admin
# Importujemy Twoje modele. Jeśli masz konflikt nazwy Group, użyj aliasu:
from .models import Bill, Friend, Person, FriendRequest, Group as MyGroup

# Rejestracja modeli w panelu
admin.site.register(Bill)
admin.site.register(Friend)
admin.site.register(Person)
admin.site.register(FriendRequest)

# Rejestrujemy Twoją grupę pod nazwą "User Groups" żeby się nie myliło
@admin.register(MyGroup)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator', 'member_count')
    
    def member_count(self, obj):
        return obj.members.count()
    member_count.short_description = 'Liczba członków'