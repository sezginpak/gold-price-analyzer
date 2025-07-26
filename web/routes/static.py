"""
Static dosya ve özel endpoint route'ları
"""
from fastapi import APIRouter
from fastapi.staticfiles import StaticFiles

router = APIRouter()

# Not: Static files mount işlemi main app'de yapılacak
# Burada sadece diğer static-related endpoint'ler olabilir