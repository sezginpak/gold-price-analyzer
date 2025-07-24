# Deployment Scripts

Bu dizinde iki deployment scripti bulunmaktadır (gitignore edilmiştir):

## 1. quick_deploy.sh
Hızlı deployment için tüm credential'ları içinde barındıran script.

**Kullanım:**
```bash
./quick_deploy.sh
```

## 2. quick_deploy_secure.sh
Environment variable'lar kullanarak daha güvenli deployment.

**Kullanım:**
```bash
# Önce environment variable'ları ayarlayın
export VPS_PASSWORD="your_vps_password"
export GITHUB_TOKEN="your_github_token"

# Sonra scripti çalıştırın
./quick_deploy_secure.sh
```

## Script Özellikleri

Her iki script de şunları yapar:
1. ✅ Uncommitted değişiklikleri kontrol eder
2. 📝 Commit mesajı sorar (veya default kullanır)
3. 📤 GitHub'a push eder
4. 🖥️ VPS'e bağlanır
5. 📥 Son değişiklikleri pull eder
6. 🔄 Servisleri yeniden başlatır
7. ✅ Servis durumlarını kontrol eder

## Not
Bu scriptler güvenlik nedeniyle git'e eklenmemiştir. Lokal olarak saklanmalıdır.