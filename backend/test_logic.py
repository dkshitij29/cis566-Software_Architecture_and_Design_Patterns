# test_logic.py
import pytest
from unittest.mock import MagicMock, patch
from postgrest.exceptions import APIError
from datetime import datetime, timedelta, timezone

import logic
import secrets

@pytest.fixture
def mock_supabase():
    """Mocks the entire Supabase client and query builder chain."""
    
    # We patch 'logic.supabase' so all functions in the logic file
    # will use this mock instead of the real one.
    with patch('logic.supabase', MagicMock()) as mock_client:
        mock_query = MagicMock()
        mock_client.table.return_value = mock_query
        mock_query.insert.return_value = mock_query
        mock_query.select.return_value = mock_query
        mock_query.update.return_value = mock_query
        mock_query.delete.return_value = mock_query
        mock_query.eq.return_value = mock_query
        mock_query.in_.return_value = mock_query
        mock_query.lt.return_value = mock_query
        mock_query.gt.return_value = mock_query
        mock_query.gte.return_value = mock_query
        mock_query.not_.return_value = mock_query
        mock_query.or_.return_value = mock_query
        mock_query.rpc.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        # This is the final object returned by .execute()
        mock_response = MagicMock()
        mock_query.execute.return_value = mock_response
        
        # Make the mock client and its response available to tests
        yield mock_client, mock_response


@patch('logic.password_hash_function', MagicMock(return_value="hashed_password_123"))
def test_create_newuser_success(mock_supabase):
    """Tests a successful user creation."""
    mock_client, mock_response = mock_supabase
    
    # Define what the DB will return on success
    mock_response.data = [{'username': 'testuser', 'user_id': 1}]
    
    result = logic.create_newuser(
        "Test", "User", "testuser", "test@example.com", "1234567890", "password123"
    )
    
    # Check that the insert call was made with the correct, hashed data
    logic.supabase.table("users").insert.assert_called_with({
        "firstname": "Test",
        "lastname": "User",
        "username": "testuser",
        "email": "test@example.com",
        "phone_number": "1234567890",
        "password": "hashed_password_123"
    })
    assert result == mock_response

def test_create_newuser_invalid_email():
    """Tests the email validation guard clause."""
    result = logic.create_newuser(
        "Test", "User", "testuser", "not-an-email", "1234567890", "password123"
    )
    assert result == "Error: Invalid Email format."

@patch('logic.password_hash_function', MagicMock(return_value="hashed_password_123"))
def test_create_newuser_duplicate_email(mock_supabase):
    """Tests the APIError handling for duplicate emails."""
    mock_client, mock_response = mock_supabase
    
    # Make .execute() raise the specific error
    mock_client.table("users").insert().execute.side_effect = APIError({
        "message": "duplicate key value violates unique constraint \"users_email_key\""
    })
    
    result = logic.create_newuser(
        "Test", "User", "testuser", "test@example.com", "1234567890", "password123"
    )
    assert result == "Error: Email already exists."

@patch('logic.check_reservation')
@patch('logic.confirm_payment')
def test_process_check_in_payment_success(mock_confirm_payment, mock_check_reservation):
    """
    Tests the *entire* check-in workflow orchestrator.
    This is the most important test for your business logic.
    """
    
    # 1. Setup Mocks
    # Mock the "finder" to return one pending booking
    mock_check_reservation.return_value = [
        {
            "booking_id": 15,
            "total_price": 350.50,
            "users": {
                "user_id": 42
            }
        }
    ]
    # Mock the "action" to return success
    mock_confirm_payment.return_value = "Success"
    
    # 2. Call the Orchestrator
    result = logic.process_check_in_payment(
        email="test@example.com",
        room_type="suite",
        payment_method="credit_card",
        transaction_id="txn_123"
    )
    
    # 3. Assertions
    # Was the finder called *correctly*?
    mock_check_reservation.assert_called_with(
        room_type="suite",
        email="test@example.com",
        booking_status="pending"  # Crucial check
    )
    
    # Was the action called with the *correct internal IDs*?
    mock_confirm_payment.assert_called_with(
        booking_id=15,
        user_id=42,
        amount=350.50,
        payment_method="credit_card",
        transaction_id="txn_123"
    )
    
    # Did the orchestrator return the final success message?
    assert result == "Success"

@patch('logic.check_reservation')
def test_process_check_in_payment_not_found(mock_check_reservation):
    """Tests the check-in workflow when no booking is found."""
    # Mock the finder to return an empty list
    mock_check_reservation.return_value = []
    
    result = logic.process_check_in_payment(
        email="test@example.com",
        room_type="suite",
        payment_method="credit_card",
        transaction_id="txn_123"
    )
    
    assert result == "Error: No pending reservation found for today with those details."

@patch('logic.get_user_by_email')
@patch('logic.send_reset_email')
def test_request_password_reset_success(mock_send_email, mock_get_user, mock_supabase):
    """Tests the first half of the password reset flow."""
    mock_client, mock_response = mock_supabase
    
    # Mock the user finder
    mock_get_user.return_value = {"user_id": 42, "email": "test@example.com"}
    
    result = logic.request_password_reset("test@example.com")
    
    # Check that we stored a token in the DB
    logic.supabase.table("password_resets").insert.assert_called_once()
    # Check that we *sent* an email
    mock_send_email.assert_called_once()
    assert result == "Success: If an account with this email exists, a reset link has been sent."

@patch('logic.update_user_password')
def test_verify_and_reset_password_success(mock_update_password, mock_supabase):
    """Tests the second half of the password reset flow."""
    mock_client, mock_response = mock_supabase
    
    # Mock the DB response for finding the token
    valid_time = datetime.now(timezone.utc) + timedelta(minutes=30)
    mock_response.data = [{
        "user_id": 42,
        "expires_at": valid_time.isoformat()
    }]
    
    # Mock the password update action
    mock_update_password.return_value = "Success"
    
    result = logic.verify_and_reset_password("real_token_123", "aNewPassword123!")
    
    # Check that the password was updated with the correct user_id
    mock_update_password.assert_called_with(
        user_id=42, 
        new_password="aNewPassword123!"
    )
    # Check that the delete() method was called once
    logic.supabase.table().delete.assert_called_once()

    # Check that execute() was called twice (once for select, once for delete)
    assert logic.supabase.table().execute.call_count == 2

    assert result == "Success: Your password has been reset."

def test_verify_and_reset_password_expired(mock_supabase):
    """Tests an expired token."""
    mock_client, mock_response = mock_supabase
    
    # Mock the DB response with a token that expired 1 hour ago
    expired_time = datetime.now(timezone.utc) - timedelta(hours=1)
    mock_response.data = [{
        "user_id": 42,
        "expires_at": expired_time.isoformat()
    }]
    
    result = logic.verify_and_reset_password("expired_token_456", "aNewPassword123!")
    
    assert result == "Error: Invalid or expired token."