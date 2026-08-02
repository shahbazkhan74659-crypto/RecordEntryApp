from django import forms

from .models import Entry


class EntryForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = [
            'date', 'vehicle_number', 'loading_roll', 'net_kg_loading_roll',
            'weight_roll', 'net_kg_weight_roll', 'workers', 'remark',
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'vehicle_number': forms.TextInput(attrs={'autocapitalize': 'characters'}),
            'remark': forms.Textarea(attrs={'rows': 4}),
        }
