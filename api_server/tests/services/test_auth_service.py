# # tests/services/test_auth_service.py
# import pytest
# import json
# import string
# import urllib
# from unittest.mock import Mock, AsyncMock, patch, MagicMock
# from fastapi import Request
# from fastapi.responses import RedirectResponse
# from core.messages.error_codes import ErrorCode
# from core.messages.http_status import HTTP_500_INTERNAL_SERVER_ERROR

# from core.api_models import AuthData_API, AppUser_API, AppUserUpdate_API
# from core.exceptions.handler import APIException
# from core.messages import *
# from services.auth_service import AuthService


# class TestAuthService:
#     """Test suite for AuthService"""
    
#     @pytest.fixture
#     def mock_auth_client(self):
#         """Create mock auth client"""
#         client = Mock(spec=['login', 'change_password', 'delete_user', 'register_user'])
#         client.login = AsyncMock()
#         client.change_password = AsyncMock()
#         client.delete_user = AsyncMock()
#         client.register_user = AsyncMock()
#         return client
    
#     @pytest.fixture
#     def mock_user_service(self):
#         """Create mock user service"""
#         service = Mock()
#         service.get_user_by_email = Mock()
#         service.create_user = AsyncMock()
#         service.update_user_password = Mock()
#         return service
    
#     @pytest.fixture
#     def auth_service(self, mock_auth_client, mock_user_service):
#         """Create auth service with mocked dependencies"""
#         # Patch the AuthClient import to return our mock instead of a real instance
#         with patch('services.auth_service.AuthClient', return_value=mock_auth_client):
#             service = AuthService()
#             service.user_service = mock_user_service
#             service.auth_client = mock_auth_client
#             return service
    
#     @pytest.fixture
#     def mock_request(self):
#         """Create mock request"""
#         request = Mock(spec=Request)
#         request.session = {}
#         return request
    
#     @pytest.fixture
#     def sample_auth_data(self):
#         """Sample authentication data"""
#         return AuthData_API(
#             id_app_user=1,
#             app_user_name="testuser",
#             app_user_password="password123"
#         )
    
#     @pytest.fixture
#     def sample_token_response(self):
#         """Sample token response from auth server"""
#         return {
#             "access_token": "eyJhbGciOiJIUzI1NiIs...",
#             "token_type": "bearer",
#             "expires_in": 3600
#         }
    
#     @pytest.fixture
#     def sample_app_user(self):
#         """Sample AppUser object"""
#         user = Mock()
#         user.id_app_user = 1
#         user.app_user_name = "testuser"
#         user.app_user_email = "test@example.com"
#         user.app_user_password = "hashed_password"
#         user.app_user_person_id = None
#         user.app_user_preferences = None
#         user.app_user_image_url = "https://example.com/photo.jpg"
#         user.app_user_type_id = 2
#         # Remove _sa_instance_state if present
#         if hasattr(user, '_sa_instance_state'):
#             del user._sa_instance_state
#         return user
    
#     # ==================== generate_random_password Tests ====================
    
#     def test_generate_random_password_length(self):
#         """Test password generation with default length"""
#         password = AuthService.generate_random_password()
#         assert len(password) == 32
    
#     def test_generate_random_password_custom_length(self):
#         """Test password generation with custom length"""
#         password = AuthService.generate_random_password(16)
#         assert len(password) == 16
    
#     def test_generate_random_password_unique(self):
#         """Test that generated passwords are unique"""
#         password1 = AuthService.generate_random_password()
#         password2 = AuthService.generate_random_password()
#         assert password1 != password2
    
#     def test_generate_random_password_contains_valid_chars(self):
#         """Test that password contains valid characters"""
#         password = AuthService.generate_random_password()
#         valid_chars = set(string.ascii_letters + string.digits + string.punctuation)
#         assert all(c in valid_chars for c in password)
    
#     # ==================== create_redirect_response Tests ====================
    
#     def test_create_redirect_response_success(self):
#         """Test creating redirect response with success data"""
#         data = {"user": {"id": 1, "name": "John"}}
#         response = AuthService.create_redirect_response(data)
        
#         location = response.headers.get("location", "")
#         assert "verdelia://auth/callback?data=" in location
#         assert response.status_code == 307
    
#     def test_create_redirect_response_error(self):
#         """Test creating redirect response with error"""
#         error_msg = "Authentication failed"
#         response = AuthService.create_redirect_response({}, error=error_msg)
        
#         location = response.headers.get("location", "")
#         decoded_location = urllib.parse.unquote(location)
#         assert f"verdelia://auth/callback?error={error_msg}" in decoded_location
#         assert response.status_code == 307
    
#     def test_create_redirect_response_json_encoding(self):
#         """Test that data is properly JSON encoded"""
#         data = {"user": {"id": 1, "name": "John", "date": "2024-01-01"}}
#         response = AuthService.create_redirect_response(data)
        
#         location = response.headers.get("location", "")
#         url_parts = urllib.parse.urlparse(location)
#         query_params = urllib.parse.parse_qs(url_parts.query)
        
#         assert 'data' in query_params
#         decoded_data = json.loads(urllib.parse.unquote(query_params['data'][0]))
#         assert decoded_data == data
    
#     # ==================== OAuth User Info Tests ====================
    
#     @pytest.mark.asyncio
#     async def test_get_oauth_user_info_google(self, auth_service):
#         """Test getting Google user info"""
#         token = {"userinfo": {"sub": "123", "email": "test@gmail.com", "name": "Test User", "picture": "url"}}
        
#         result = await auth_service.get_oauth_user_info("google", token)
        
#         assert result is not None
#         assert result["id"] == "123"
#         assert result["email"] == "test@gmail.com"
#         assert result["provider"] == "google"
    
#     @pytest.mark.asyncio
#     async def test_get_oauth_user_info_google_fallback(self, auth_service):
#         """Test Google user info fallback to userinfo endpoint"""
#         token = {"access_token": "test_token"}
        
#         # Create a proper async response with json() that returns a coroutine
#         mock_response = AsyncMock()
#         mock_response.status_code = 200
#         # Make json() return the dict directly, not a coroutine
#         mock_response.json = MagicMock(return_value={
#             "id": "123",
#             "email": "test@gmail.com",
#             "name": "Test User",
#             "picture": "url"
#         })
        
#         # Create a mock client that works as a context manager
#         mock_client = AsyncMock()
#         mock_client.get = AsyncMock(return_value=mock_response)
#         mock_client.__aenter__ = AsyncMock(return_value=mock_client)
#         mock_client.__aexit__ = AsyncMock(return_value=None)
        
#         with patch('httpx.AsyncClient', return_value=mock_client):
#             result = await auth_service._get_google_user_info(token)
            
#             assert result is not None
#             assert result["id"] == "123"
#             assert result["provider"] == "google"
    
#     @pytest.mark.asyncio
#     async def test_get_oauth_user_info_facebook(self, auth_service):
#         """Test getting Facebook user info"""
#         token = {"access_token": "test_token"}
        
#         mock_response = AsyncMock()
#         mock_response.status_code = 200
#         mock_response.json = MagicMock(return_value={
#             "id": "456",
#             "email": "test@facebook.com",
#             "name": "FB User",
#             "picture": {"data": {"url": "fb_url"}}
#         })
        
#         mock_client = AsyncMock()
#         mock_client.get = AsyncMock(return_value=mock_response)
#         mock_client.__aenter__ = AsyncMock(return_value=mock_client)
#         mock_client.__aexit__ = AsyncMock(return_value=None)
        
#         with patch('httpx.AsyncClient', return_value=mock_client):
#             result = await auth_service._get_facebook_user_info(token)
            
#             assert result is not None
#             assert result["id"] == "456"
#             assert result["provider"] == "facebook"
    
#     @pytest.mark.asyncio
#     async def test_get_oauth_user_info_instagram(self, auth_service):
#         """Test getting Instagram user info"""
#         token = {"access_token": "test_token"}
        
#         mock_response = AsyncMock()
#         mock_response.status_code = 200
#         mock_response.json = MagicMock(return_value={
#             "id": "789",
#             "username": "insta_user",
#             "account_type": "business"
#         })
        
#         mock_client = AsyncMock()
#         mock_client.get = AsyncMock(return_value=mock_response)
#         mock_client.__aenter__ = AsyncMock(return_value=mock_client)
#         mock_client.__aexit__ = AsyncMock(return_value=None)
        
#         with patch('httpx.AsyncClient', return_value=mock_client):
#             result = await auth_service._get_instagram_user_info(token)
            
#             assert result is not None
#             assert result["id"] == "789"
#             assert result["username"] == "insta_user"
#             assert result["provider"] == "instagram"
    
#     @pytest.mark.asyncio
#     async def test_get_oauth_user_info_unsupported_provider(self, auth_service):
#         """Test unsupported provider returns None"""
#         result = await auth_service.get_oauth_user_info("twitter", {})
#         assert result is None
    
#     # ==================== OAuth Login Handler Tests ====================
    
#     @pytest.mark.asyncio
#     async def test_handle_oauth_login_success(self, auth_service, mock_request):
#         """Test successful OAuth login redirect"""
#         mock_oauth_client = AsyncMock()
#         mock_oauth_client.authorize_redirect = AsyncMock(return_value=RedirectResponse(url="https://google.com"))
        
#         result = await auth_service.handle_oauth_login("google", mock_request, mock_oauth_client)
        
#         assert isinstance(result, RedirectResponse)
#         mock_oauth_client.authorize_redirect.assert_called_once()
    
    
#     # ==================== OAuth Callback Tests ====================
    
#     @pytest.mark.asyncio
#     async def test_handle_oauth_callback_success(self, auth_service, mock_request, sample_app_user):
#         """Test successful OAuth callback"""
#         mock_oauth_client = AsyncMock()
#         mock_oauth_client.authorize_access_token = AsyncMock(return_value={"access_token": "token"})
        
#         with patch.object(auth_service, 'get_oauth_user_info', AsyncMock(return_value={
#             "id": "123", "email": "test@example.com", "name": "Test User", "picture": "url"
#         })):
#             with patch.object(auth_service, 'get_or_create_oauth_user', AsyncMock(return_value=sample_app_user)):
#                 result = await auth_service.handle_oauth_callback("google", mock_request, mock_oauth_client)
                
#                 assert isinstance(result, RedirectResponse)
#                 location = result.headers.get("location", "")
#                 assert "verdelia://auth/callback?data=" in location
    
#     @pytest.mark.asyncio
#     async def test_handle_oauth_callback_no_user_info(self, auth_service, mock_request):
#         """Test OAuth callback when user info retrieval fails"""
#         mock_oauth_client = AsyncMock()
#         mock_oauth_client.authorize_access_token = AsyncMock(return_value={"access_token": "token"})
        
#         with patch.object(auth_service, 'get_oauth_user_info', AsyncMock(return_value=None)):
#             result = await auth_service.handle_oauth_callback("google", mock_request, mock_oauth_client)
            
#             assert isinstance(result, RedirectResponse)
#             location = result.headers.get("location", "")
#             assert "error=Failed%20to%20retrieve%20user%20information" in location
    
#     @pytest.mark.asyncio
#     async def test_handle_oauth_callback_exception(self, auth_service, mock_request):
#         """Test OAuth callback with exception"""
#         mock_oauth_client = AsyncMock()
#         mock_oauth_client.authorize_access_token = AsyncMock(side_effect=Exception("Auth failed"))
        
#         result = await auth_service.handle_oauth_callback("google", mock_request, mock_oauth_client)
        
#         assert isinstance(result, RedirectResponse)
#         location = result.headers.get("location", "")
#         assert "error=Auth%20failed" in location
    
#     # ==================== get_or_create_oauth_user Tests ====================
    
#     @pytest.mark.asyncio
#     async def test_get_or_create_oauth_user_existing(self, auth_service, mock_user_service):
#         """Test getting existing OAuth user"""
#         user_info = {"email": "existing@example.com", "picture": "url"}
#         existing_user = Mock()
#         existing_user.id_app_user = 1
#         mock_user_service.get_user_by_email.return_value = existing_user
        
#         result = await auth_service.get_or_create_oauth_user(user_info, "google")
        
#         assert result == existing_user
#         mock_user_service.get_user_by_email.assert_called_once_with("existing@example.com")
#         mock_user_service.create_user.assert_not_called()
    
#     @pytest.mark.asyncio
#     async def test_get_or_create_oauth_user_new(self, auth_service, mock_user_service):
#         """Test creating new OAuth user"""
#         user_info = {"email": "new@example.com", "picture": "url", "name": "New User"}
#         mock_user_service.get_user_by_email.return_value = None
#         new_user = Mock()
#         new_user.id_app_user = 2
#         mock_user_service.create_user.return_value = new_user
        
#         with patch.object(auth_service, 'generate_random_password', return_value="random_pass"):
#             result = await auth_service.get_or_create_oauth_user(user_info, "google")
            
#             assert result is not None
#             mock_user_service.create_user.assert_called_once()
    
#     @pytest.mark.asyncio
#     async def test_get_or_create_oauth_user_instagram_no_email(self, auth_service, mock_user_service):
#         """Test creating Instagram user without email"""
#         user_info = {"id": "12345", "username": "insta_user"}
#         mock_user_service.get_user_by_email.return_value = None
#         new_user = Mock()
#         new_user.id_app_user = 3
#         mock_user_service.create_user.return_value = new_user
        
#         with patch.object(auth_service, 'generate_random_password', return_value="random_pass"):
#             result = await auth_service.get_or_create_oauth_user(user_info, "instagram")
            
#             assert result is not None
#             mock_user_service.create_user.assert_called_once()
    
#     # ==================== prepare_user_response Tests ====================
    
#     def test_prepare_user_response_from_object(self, auth_service, sample_app_user):
#         """Test preparing user response from object with __dict__"""
#         token = {"access_token": "token123"}
#         result = auth_service.prepare_user_response(sample_app_user, token)
        
#         assert result["success"] is True
#         assert result["token"] == token
#         assert "app_user_password" not in result["user"]
#         assert result["user"]["id_app_user"] == 1
    
#     def test_prepare_user_response_from_dict(self, auth_service):
#         """Test preparing user response from dictionary"""
#         user = {"id_app_user": 1, "app_user_name": "John", "app_user_password": "secret"}
        
#         token = {"access_token": "token123"}
#         result = auth_service.prepare_user_response(user, token)
        
#         assert result["success"] is True
#         assert "app_user_password" not in result["user"]
#         assert result["user"]["id_app_user"] == 1
    
    
#     # ==================== login_user Tests ====================
    
#     @pytest.mark.asyncio
#     async def test_login_user_success(self, auth_service, mock_auth_client, sample_auth_data, sample_token_response):
#         """Test successful user login"""
#         mock_auth_client.login.return_value = sample_token_response
        
#         result = await auth_service.login_user(sample_auth_data)
        
#         assert result == sample_token_response
#         mock_auth_client.login.assert_called_once_with(
#             username=sample_auth_data.app_user_name,
#             user_id=sample_auth_data.id_app_user,
#             password=sample_auth_data.app_user_password
#         )
    
#     @pytest.mark.asyncio
#     async def test_login_user_failure(self, auth_service, mock_auth_client, sample_auth_data):
#         """Test failed user login"""
#         from core.exceptions.handler import AuthServiceUnavailableException
#         mock_auth_client.login.side_effect = AuthServiceUnavailableException("Invalid credentials")
        
#         with pytest.raises(AuthServiceUnavailableException):
#             await auth_service.login_user(sample_auth_data)
    
#     # ==================== change_user_password Tests ====================
    
#     @pytest.mark.asyncio
#     async def test_change_user_password_success(self, auth_service, mock_auth_client, mock_user_service):
#         """Test successful password change"""
#         mock_auth_client.change_password.return_value = {"hashed_password": "new_hash"}
#         mock_user_service.update_user_password.return_value = Mock()
        
#         # Create a proper AppUserUpdate_API object
#         user_update = AppUserUpdate_API(
#             id_app_user=1,
#             username="testuser",
#             new_password="newpass123",
#             app_user_name="testuser",
#             app_user_password="newpass123",
#             app_user_person_id=None,
#             app_user_preferences=None,
#             app_user_email="test@example.com",
#             app_user_image_url=None,
#             app_user_type_id=2
#         )
        
#         # Mock the AppUserUpdate_API constructor
#         with patch('core.api_models.AppUserUpdate_API', return_value=user_update):
#             result = await auth_service.change_user_password(
#                 user_id=1,
#                 username="testuser",
#                 new_password="newpass123",
#                 token="valid_token"
#             )
            
#             assert result is not None
    
#     @pytest.mark.asyncio
#     async def test_change_user_password_failure(self, auth_service, mock_auth_client):
#         """Test failed password change"""
#         mock_auth_client.change_password.side_effect = Exception("Auth server error")
        
#         with pytest.raises(Exception):
#             await auth_service.change_user_password(
#                 user_id=1, username="testuser", new_password="newpass123", token="token"
#             )
    
#     # ==================== delete_user Tests ====================
    
#     @pytest.mark.asyncio
#     async def test_delete_user_success(self, auth_service, mock_auth_client):
#         """Test successful user deletion"""
#         mock_auth_client.delete_user = AsyncMock()
        
#         await auth_service.delete_user(user_id=1, username="testuser", password="pass123")
        
#         mock_auth_client.delete_user.assert_called_once_with(1, "testuser", "pass123")
    
#     @pytest.mark.asyncio
#     async def test_delete_user_failure(self, auth_service, mock_auth_client):
#         """Test failed user deletion"""
#         mock_auth_client.delete_user = AsyncMock(side_effect=Exception("Deletion failed"))
        
#         with pytest.raises(Exception):
#             await auth_service.delete_user(user_id=1, username="testuser", password="pass123")
    
#     # ==================== logout_user Tests ====================
    
#     def test_logout_user(self, auth_service, mock_request):
#         """Test user logout"""
#         mock_request.session = {"user": "test_user", "token": "abc123"}
        
#         result = auth_service.logout_user(mock_request)
        
#         assert result["success"] is True
#         assert result["message"] == "Logged out successfully"
#         assert mock_request.session == {}

