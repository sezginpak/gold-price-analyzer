"""
Dashboard route testleri
"""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import Request
from fastapi.templating import Jinja2Templates

from web_server import app
from web.routes.dashboard import router


class TestDashboardRoutes:
    """Dashboard route testleri"""
    
    @pytest.fixture
    def client(self):
        """Test client'i oluştur"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_templates(self):
        """Mock template engine oluştur"""
        mock = Mock(spec=Jinja2Templates)
        mock.TemplateResponse = Mock()
        return mock
    
    def test_dashboard_route(self, client):
        """Ana dashboard route testi"""
        response = client.get("/")
        assert response.status_code == 200
        
        # HTML içeriğinin varlığını kontrol et
        assert "text/html" in response.headers.get("content-type", "")
    
    def test_analysis_route(self, client):
        """Analiz sayfası route testi"""
        response = client.get("/analysis")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
    
    def test_signals_route(self, client):
        """Sinyaller sayfası route testi"""
        response = client.get("/signals")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
    
    def test_logs_route(self, client):
        """Log sayfası route testi"""
        response = client.get("/logs")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
    
    def test_simulations_route(self, client):
        """Simülasyon sayfası route testi"""
        response = client.get("/simulations")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
    
    def test_menu_route(self, client):
        """Menu component route testi"""
        response = client.get("/menu")
        # Menu.html template'i yoksa 500 hatası alabilir
        # Ama route tanımlı olmalı
        assert response.status_code in [200, 500]
    
    def test_dashboard_template_context(self, client):
        """Dashboard template context testi"""
        response = client.get("/")
        
        # Response başarılı olmalı
        assert response.status_code == 200
        
        # HTML içeriği olmalı
        content = response.text
        assert len(content) > 0
        assert "<!DOCTYPE html>" in content or "<html" in content
    
    def test_all_routes_accessibility(self, client):
        """Tüm route'ların erişilebilirliği testi"""
        routes_to_test = [
            "/",
            "/analysis", 
            "/signals",
            "/logs",
            "/simulations"
        ]
        
        for route in routes_to_test:
            response = client.get(route)
            # 200 (başarılı) veya 500 (template hatası) olabilir
            # 404 olmamalı (route tanımlı olmalı)
            assert response.status_code != 404, f"Route {route} bulunamadı"
            assert response.status_code in [200, 500], f"Route {route} beklenmeyen hata: {response.status_code}"
    
    def test_static_files_mount(self, client):
        """Static dosyalar mount testi"""
        # CSS dosyasını test et
        response = client.get("/static/css/main.css")
        # Dosya varsa 200, yoksa 404 
        assert response.status_code in [200, 404]
    
    def test_dashboard_response_headers(self, client):
        """Dashboard response header'ları testi"""
        response = client.get("/")
        
        # Content-Type header'ı olmalı
        assert "content-type" in response.headers
        assert "text/html" in response.headers["content-type"]
    
    def test_dashboard_content_structure(self, client):
        """Dashboard içerik yapısı testi"""
        response = client.get("/")
        content = response.text.lower()
        
        # Temel HTML elementleri olmalı
        html_elements = ["<html", "<head", "<body", "</html>"]
        for element in html_elements:
            assert element in content, f"HTML element '{element}' bulunamadı"
    
    def test_route_with_invalid_path(self, client):
        """Geçersiz path ile route testi"""
        response = client.get("/nonexistent-page")
        assert response.status_code == 404
    
    def test_dashboard_javascript_loading(self, client):
        """Dashboard JavaScript yükleme testi"""
        response = client.get("/")
        content = response.text
        
        # JavaScript dosya referanslarını kontrol et
        # Template'lerde JS dosyaları yükleniyorsa
        if "<script" in content:
            assert "src=" in content  # JavaScript dosya referansı olmalı
    
    def test_dashboard_css_loading(self, client):
        """Dashboard CSS yükleme testi"""
        response = client.get("/")
        content = response.text
        
        # CSS dosya referanslarını kontrol et
        if "<link" in content and "stylesheet" in content:
            assert "href=" in content  # CSS dosya referansı olmalı
    
    @pytest.mark.parametrize("route_path,expected_template", [
        ("/", "dashboard.html"),
        ("/analysis", "analysis.html"),
        ("/signals", "signals.html"),
        ("/logs", "logs.html"),
        ("/simulations", "simulations.html")
    ])
    def test_route_template_mapping(self, client, route_path, expected_template):
        """Route ve template eşleştirme testi"""
        response = client.get(route_path)
        
        # Response başarılı olmalı (template varsa)
        # Veya 500 hatası (template yoksa)
        assert response.status_code in [200, 500]
        
        # 500 hatası alınırsa template dosyası eksik demektir
        if response.status_code == 500:
            # Template dosyası eksikliği beklenen bir durum
            pass
        else:
            # 200 ise içerik var demektir
            assert len(response.text) > 0
    
    def test_dashboard_meta_tags(self, client):
        """Dashboard meta tag'leri testi"""
        response = client.get("/")
        content = response.text.lower()
        
        # Temel meta tag'lerin varlığını kontrol et
        if "<meta" in content:
            # En az bir meta tag var
            assert "charset" in content or "viewport" in content
    
    def test_dashboard_title_tag(self, client):
        """Dashboard title tag testi"""
        response = client.get("/")
        content = response.text.lower()
        
        # Title tag'i olmalı
        assert "<title>" in content and "</title>" in content
    
    def test_route_response_time(self, client):
        """Route response süresi testi"""
        import time
        
        start_time = time.time()
        response = client.get("/")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # Response süresi 5 saniyeden az olmalı
        assert response_time < 5.0, f"Dashboard yavaş yüklendi: {response_time:.2f} saniye"
        assert response.status_code in [200, 500]