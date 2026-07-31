from django import forms

from .models import Entry


class EntryForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = ['date', 'vehicle_number', 'rolls', 'workers', 'net_kg', 'remark']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'vehicle_number': forms.TextInput(attrs={'autocapitalize': 'characters'}),
            'remark': forms.Textarea(attrs={'rows': 4}),
        }
