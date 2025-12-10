from django import forms


class AppointmentForm(forms.Form):
    APPLIANCE_CHOICES = [
        ('refrigerator', 'Refrigerator'),
        ('dishwasher', 'Dishwasher'),
        ('washer', 'Washer'),
        ('dryer', 'Dryer'),
        ('oven', 'Oven'),
        ('stove', 'Stove'),
        ('microwave', 'Microwave'),
        ('air_conditioner', 'Air Conditioner'),
        ('other', 'Other'),
    ]
    
    name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full p-2 border border-gray-300 rounded',
            'placeholder': 'Your Full Name'
        })
    )
    
    phone = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full p-2 border border-gray-300 rounded',
            'placeholder': '(123) 456-7890',
            'type': 'tel'
        })
    )
    
    address = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'w-full p-2 border border-gray-300 rounded',
            'placeholder': 'Street Address, City, TX ZIP',
            'rows': 2
        })
    )
    
    appliance_type = forms.ChoiceField(
        choices=APPLIANCE_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full p-2 border border-gray-300 rounded'
        })
    )
    
    issue_description = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'w-full p-2 border border-gray-300 rounded',
            'placeholder': 'Describe the issue with your appliance...',
            'rows': 4
        })
    )

