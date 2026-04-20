from django.contrib import admin
from .models import Education


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'user',
        'level',
        'institution_name',
        'degree',
        'percentage',
        'city',
        'created_at'
    )

    list_filter = ('level', 'city')

    search_fields = (
        'user__email',
        'institution_name',
        'degree'
    )

    ordering = ('-created_at',)