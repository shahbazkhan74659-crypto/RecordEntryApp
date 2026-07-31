from django import forms

from .models import Entry


class EntryForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = ['vehicle_number', 'rolls', 'workers', 'net_kg', 'remark']
