#!/usr/bin/env python3
"""
Simülasyon tablolarını oluştur
"""
import sys
sys.path.append('.')

from storage.create_simulation_tables import create_simulation_tables

if __name__ == "__main__":
    if create_simulation_tables():
        print("✅ Simülasyon tabloları başarıyla oluşturuldu!")
    else:
        print("❌ Hata: Tablolar oluşturulamadı!")