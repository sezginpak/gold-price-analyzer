#!/usr/bin/env python3
"""
Hot reload için güvenli güncelleme scripti
Analizi bozmadan kod güncellemesi yapar
"""
import subprocess
import sys
import os
import time

def check_for_updates():
    """Git güncellemesi var mı kontrol et"""
    subprocess.run(["git", "fetch"], check=True)
    
    local = subprocess.check_output(["git", "rev-parse", "HEAD"]).strip()
    remote = subprocess.check_output(["git", "rev-parse", "@{u}"]).strip()
    
    return local != remote

def get_changed_files():
    """Değişen dosyaları al"""
    result = subprocess.check_output(["git", "diff", "--name-only", "HEAD", "@{u}"])
    return result.decode().strip().split('\n')

def needs_restart(changed_files):
    """Restart gerekli mi?"""
    # Sadece bu dosyalar değiştiyse restart gerekli
    critical_files = [
        'main_with_web.py',
        'main_robust.py',
        'web_server.py',
        'collectors/',
        'analyzers/',
        'storage/'
    ]
    
    for file in changed_files:
        for critical in critical_files:
            if critical in file:
                return True
    
    # Template veya README değişiklikleri restart gerektirmez
    return False

def main():
    if not check_for_updates():
        print("No updates available")
        return
    
    print("Updates found, checking if restart needed...")
    changed = get_changed_files()
    
    # Pull yap
    subprocess.run(["git", "pull"], check=True)
    
    if needs_restart(changed):
        print("Critical files changed, restarting service...")
        subprocess.run(["systemctl", "restart", "gold-analyzer"], check=True)
    else:
        print("Only non-critical files changed, no restart needed")
        # Sadece web template'leri güncellendi, restart gerekmez

if __name__ == "__main__":
    main()