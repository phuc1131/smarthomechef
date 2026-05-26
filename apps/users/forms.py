from django import forms
from django.core.exceptions import ValidationError


class PasswordChangeForm(forms.Form):
    """Form for changing password"""
    old_password = forms.CharField(
        label='Mật khẩu cũ',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nhập mật khẩu cũ',
        })
    )
    new_password = forms.CharField(
        label='Mật khẩu mới',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nhập mật khẩu mới (tối thiểu 8 ký tự)',
        })
    )
    confirm_password = forms.CharField(
        label='Xác nhận mật khẩu mới',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Xác nhận mật khẩu mới',
        })
    )

    def clean_new_password(self):
        new_password = self.cleaned_data.get('new_password')
        if len(new_password) < 8:
            raise ValidationError('Mật khẩu phải có ít nhất 8 ký tự.')
        return new_password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password and confirm_password:
            if new_password != confirm_password:
                raise ValidationError('Mật khẩu mới không khớp. Vui lòng thử lại.')

        return cleaned_data


class PasswordResetForm(forms.Form):
    """Form for password reset via email"""
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nhập email của bạn',
        })
    )
