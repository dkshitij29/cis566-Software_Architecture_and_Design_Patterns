# test_integration.py
import pytest
import logic  # Your logic.py file
from datetime import date, timedelta
import os
from supabase import create_client, Client
from dotenv import load_dotenv


test_data = {
    "user_id": None,
    "room_id": None,
    "booking_id": None,
    "user_email": "integration_test@example.com",
    "room_number": "INT-101",
    "room_type": "suite"
}

# --- Helper Function to Clean DB ---
# We need a direct connection to wipe the tables
load_dotenv()
url: str = os.environ.get("supabase_url")
key: str = os.environ.get("supabase_key")
supabase: Client = create_client(url, key)

def clean_database():
    """Wipes all tables in the correct order."""
    print("\n--- CLEANING DATABASE ---")
    # We must delete in the order of dependencies
    # (child tables first)
    try:
        supabase.table("payments").delete().gt("payment_id", 0).execute()
        supabase.table("reviews").delete().gt("review_id", 0).execute()
        supabase.table("password_resets").delete().gt("id", 0).execute()
        # Bookings depends on users and rooms
        supabase.table("bookings").delete().gt("booking_id", 0).execute()
        # Now we can delete the parent tables
        supabase.table("users").delete().gt("user_id", 0).execute()
        supabase.table("rooms").delete().gt("room_id", 0).execute()
    except Exception as e:
        print(f"Error cleaning database: {e}")
        pass
    print("--- DATABASE CLEAN ---")

# --- Integration Tests ---

@pytest.mark.run(order=1)
def test_01_start_fresh():
    """WIPES ALL DATA before tests begin."""
    clean_database()
    assert True

@pytest.mark.run(order=2)
def test_02_create_user():
    """Tests creating a new user."""
    result = logic.create_newuser(
        "Integration", "Test", "int-test",
        test_data["user_email"], "5555555555", "aStrongPassword123!"
    )
    # Check that the API call returned a successful response object
    assert hasattr(result, 'data') and result.data
    test_data["user_id"] = result.data[0]['user_id']
    print(f"Created user ID: {test_data['user_id']}")

@pytest.mark.run(order=3)
def test_03_create_user_duplicate():
    """Tests that creating a duplicate user fails correctly."""
    result = logic.create_newuser(
        "Another", "User", "int-test2",
        test_data["user_email"], "5555555556", "aStrongPassword123!"
    )
    assert result == "Error: Email already exists."

@pytest.mark.run(order=4)
def test_04_create_room():
    """Tests creating a new room."""
    result = logic.create_room(test_data["room_number"], test_data["room_type"], 250.00)
    assert hasattr(result, 'data') and result.data
    test_data["room_id"] = result.data[0]['room_id']
    print(f"Created room ID: {test_data['room_id']}")

@pytest.mark.run(order=5)
def test_05_create_booking_for_today():
    """Tests creating a 'pending' booking for today."""
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    
    result = logic.create_booking(
        test_data["user_id"], test_data["room_id"], today, tomorrow
    )
    assert hasattr(result, 'data') and result.data
    test_data["booking_id"] = result.data[0]['booking_id']
    print(f"Created booking ID: {test_data['booking_id']}")

@pytest.mark.run(order=6)
def test_06_create_booking_conflict():
    """Tests that booking the same room on the same day fails."""
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    
    result = logic.create_booking(
        test_data["user_id"], test_data["room_id"], today, tomorrow
    )
    assert result == "Error: Room is already booked for these dates."

@pytest.mark.run(order=7)
def test_07_process_check_in_payment():
    """Tests the full check-in workflow. This uses the fixed check_reservation."""
    result = logic.process_check_in_payment(
        email=test_data["user_email"],
        room_type=test_data["room_type"],
        payment_method="credit_card",
        transaction_id="txn_integration_test_123"
    )
    assert result == "Success"

@pytest.mark.run(order=8)
def test_08_check_booking_is_confirmed():
    """Verifies that the booking from the previous test is now 'confirmed'."""
    response = supabase.table("bookings").select("booking_status").eq("booking_id", test_data["booking_id"]).execute()
    assert response.data[0]['booking_status'] == 'confirmed'
    print("Booking is now CONFIRMED.")

@pytest.mark.run(order=9)
def test_09_delete_room_fails_due_to_restrict():
    """Tests the ON DELETE RESTRICT safeguard."""
    result = logic.delete_room(test_data["room_id"])
    assert result == "Error: Room has existing bookings."
    print("ON DELETE RESTRICT successfully prevented room deletion.")

@pytest.mark.run(order=10)
def test_10_delete_user():
    """Tests deleting the user."""
    result = logic.delete_user(test_data["user_id"])
    assert result == "Success"

@pytest.mark.run(order=11)
def test_11_check_booking_is_anonymized():
    """Tests the ON DELETE SET NULL behavior."""
    response = supabase.table("bookings").select("user_id").eq("booking_id", test_data["booking_id"]).execute()
    # The user_id should now be NULL
    assert response.data[0]['user_id'] is None
    print("Booking has been successfully anonymized (user_id is NULL).")

@pytest.mark.run(order=12)
def test_12_final_cleanup():
    """WIPES ALL DATA after tests are complete."""
    clean_database()
    assert True