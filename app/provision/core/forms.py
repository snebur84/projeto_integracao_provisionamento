from django import forms

def get_device_form():
    """
    Factory that returns a ModelForm for DeviceConfig.
    Import DeviceConfig lazily so the file can be created before the model exists.
    """
    from .models import DeviceConfig  # imported lazily
    class DeviceConfigForm(forms.ModelForm):
        class Meta:
            model = DeviceConfig
            fields = '__all__'
    return DeviceConfigForm