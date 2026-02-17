import requests
import sys

def test_theme_update_fix():
    """Test the theme settings update fix"""
    base_url = "https://knihovny-galerie.preview.emergentagent.com"
    api_url = f"{base_url}/api"
    
    # First register a new user to get a token
    registration_data = {
        "institution_name": "Test Theme Institution",
        "institution_type": "museum",
        "country": "Czech Republic",
        "email": "themetest@example.com",
        "password": "TestPassword123!"
    }
    
    print("🔧 Testing theme settings update fix...")
    
    # Register
    response = requests.post(f"{api_url}/auth/register", json=registration_data)
    if response.status_code != 200:
        print(f"❌ Registration failed: {response.status_code}")
        return False
    
    token = response.json().get('token')
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    # Test theme update
    theme_data = {
        "primary_color": "#2563EB",
        "secondary_color": "#10B981", 
        "accent_color": "#F59E0B",
        "header_style": "dark",
        "footer_text": "Test Footer Text"
    }
    
    response = requests.put(f"{api_url}/settings/theme", json=theme_data, headers=headers)
    
    if response.status_code == 200:
        print("✅ Theme settings update fix successful!")
        result = response.json()
        print(f"   Updated theme with primary color: {result.get('primary_color')}")
        return True
    else:
        print(f"❌ Theme update failed: {response.status_code}")
        try:
            print(f"   Error: {response.json()}")
        except:
            print(f"   Response: {response.text}")
        return False

if __name__ == "__main__":
    success = test_theme_update_fix()
    sys.exit(0 if success else 1)