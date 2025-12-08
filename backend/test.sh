#!/bin/bash

# --- Dynamic Configuration ---
BASE_URL="http://127.0.0.1:8000"
TIMESTAMP=$(date +%s)
USER_EMAIL="user_$TIMESTAMP@example.com"
USERNAME="user_$TIMESTAMP"
PASSWORD="testpassword123"
# Use a new password for the test
NEW_PASSWORD="newPass123" 
TODAY_DATE=$(date +"%Y-%m-%d")

# Check if 'date -v' (macOS/BSD) or 'date -d' (Linux) is available
if date -v+1d +"%Y-%m-%d" &> /dev/null; then
    TOMORROW_DATE=$(date -v+1d +"%Y-%m-%d")
    DAY_AFTER_TOMORROW=$(date -v+2d +"%Y-%m-%d")
else
    TOMORROW_DATE=$(date -d "+1 day" +"%Y-%m-%d")
    DAY_AFTER_TOMORROW=$(date -d "+2 day" +"%Y-%m-%d")
fi

# --- Global Variables (will be set by script) ---
TOKEN=""
SINGLE_ROOM_ID=""
DOUBLE_ROOM_ID=""
PENDING_BOOKING_ID=""

# Helper function to check if curl failed (e.g., connection refused)
check_curl_error() {
  if [ $? -ne 0 ]; then
    echo "!!! FATAL ERROR: curl command failed. Is the server running at $BASE_URL? !!!"
    exit 1
  fi
}

echo "--- API Test Script ---"
echo "Base URL: $BASE_URL"
echo "Today: $TODAY_DATE"
echo "Tomorrow: $TOMORROW_DATE"
echo "----------------------"
echo "Testing with NEW dynamic user:"
echo "  Email: $USER_EMAIL"
echo "  User:  $USERNAME"
echo "----------------------"


# --- 1. Test Root Endpoint ---
echo "1. Testing Root Endpoint (GET /)"
curl -s -X 'GET' "$BASE_URL/" | jq .
check_curl_error
echo "----------------------"


# --- 2. Sign Up New User ---
echo "2. Signing up new user (POST /users/signup)"
SIGNUP_RESPONSE=$(curl -s -X 'POST' \
  "$BASE_URL/users/signup" \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d "{
\"firstname\": \"Test\",
\"lastname\": \"User\",
\"username\": \"$USERNAME\",
\"email\": \"$USER_EMAIL\",
\"phone_number\": \"1234567890\",
\"password\": \"$PASSWORD\"
}")
check_curl_error
echo "$SIGNUP_RESPONSE" | jq .

DETAIL=$(echo "$SIGNUP_RESPONSE" | jq -r .detail)
if [ -n "$DETAIL" ] && [ "$DETAIL" != "null" ]; then
    echo "!!! FATAL ERROR: Signup failed: $DETAIL !!!"
    exit 1
fi
echo "----------------------"


# --- 3. Log In and Capture Token (Original Password) ---
echo "3. Logging in as new user (POST /users/login) with original password"
LOGIN_RESPONSE=$(curl -s -X 'POST' \
  "$BASE_URL/users/login" \
  -H 'accept: application/json' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d "grant_type=password&username=$USER_EMAIL&password=$PASSWORD")
check_curl_error

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r .access_token)

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
    echo "!!! FATAL ERROR: Could not get access token. Login failed. !!!"
    echo "$LOGIN_RESPONSE" | jq .
    exit 1
fi
echo "Successfully captured token!"
echo "----------------------"


# --- 4. Test Update Profile (Authenticated) ---
echo "4. Testing Update Profile (PUT /users/me)"
curl -s -X 'PUT' \
  "$BASE_URL/users/me" \
  -H 'accept: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{
\"firstname\": \"Test\",
\"lastname\": \"Updated\",
\"username\": \"$USERNAME\",
\"email\": \"$USER_EMAIL\",
\"phone_number\": \"555-8888\",
\"password\": \"$PASSWORD\"
}" | jq .
check_curl_error
echo "----------------------"


# --- 5. Create Rooms and Capture ID (Authenticated) ---
echo "5. Creating Test Rooms (POST /rooms/)"

# Create a 'single' room (will be confirmed via check-in)
SINGLE_ROOM_RESPONSE=$(curl -s -X 'POST' \
  "$BASE_URL/rooms/" \
  -H 'accept: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
"room_number": "101",
"room_type": "single",
"price_per_night": 95.0
}')
check_curl_error
SINGLE_ROOM_ID=$(echo "$SINGLE_ROOM_RESPONSE" | jq -r .room_id)
echo "Created 'single' room (ID: $SINGLE_ROOM_ID)"

# Create a 'double' room (will be cancelled)
DOUBLE_ROOM_RESPONSE=$(curl -s -X 'POST' \
  "$BASE_URL/rooms/" \
  -H 'accept: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
"room_number": "201",
"room_type": "double",
"price_per_night": 150.0
}')
check_curl_error
DOUBLE_ROOM_ID=$(echo "$DOUBLE_ROOM_RESPONSE" | jq -r .room_id)
echo "Created 'double' room (ID: $DOUBLE_ROOM_ID)"
echo "----------------------"


# --- 6. Test Availability ---
echo "6. Checking 'single' room availability for today (GET /rooms/available)"
curl -s -X 'GET' \
  "$BASE_URL/rooms/available?room_type=single&check_in=$TODAY_DATE&check_out=$TOMORROW_DATE" \
  -H 'accept: application/json' | jq .
check_curl_error
echo "----------------------"


# --- 7. Create 1st Booking (Check-In Test) ---
echo "7. Booking 'single' room (ID: $SINGLE_ROOM_ID) for today (POST /bookings/)"
curl -s -X 'POST' \
  "$BASE_URL/bookings/" \
  -H 'accept: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{
\"room_id\": $SINGLE_ROOM_ID, 
\"check_in_str\": \"$TODAY_DATE\",
\"check_out_str\": \"$TOMORROW_DATE\"
}" | jq .
check_curl_error
echo "----------------------"


# --- 8. Create 2nd Booking (Cancel Test) ---
echo "8. Booking 'double' room (ID: $DOUBLE_ROOM_ID) for tomorrow (POST /bookings/)"
BOOKING_RESPONSE=$(curl -s -X 'POST' \
  "$BASE_URL/bookings/" \
  -H 'accept: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{
\"room_id\": $DOUBLE_ROOM_ID, 
\"check_in_str\": \"$TOMORROW_DATE\",
\"check_out_str\": \"$DAY_AFTER_TOMORROW\"
}")
check_curl_error
echo "$BOOKING_RESPONSE" | jq .
PENDING_BOOKING_ID=$(echo "$BOOKING_RESPONSE" | jq -r .booking_id)

if [ "$PENDING_BOOKING_ID" == "null" ] || [ -z "$PENDING_BOOKING_ID" ]; then
    echo "!!! FATAL ERROR: Could not create 2nd booking for cancellation test. !!!"
    exit 1
fi
echo "----------------------"


# --- 9. Test Availability (Conflict Check) ---
echo "9. Re-checking 'single' room availability for today (should now be empty)"
curl -s -X 'GET' \
  "$BASE_URL/rooms/available?room_type=single&check_in=$TODAY_DATE&check_out=$TOMORROW_DATE" \
  -H 'accept: application/json' | jq .
check_curl_error
echo "----------------------"


# --- 10. Test Check-In Flow (Confirms 1st Booking) ---
echo "10. Processing Check-In for today's 'single' room (POST /bookings/check-in)"
curl -s -X 'POST' \
  "$BASE_URL/bookings/check-in" \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d "{
\"email\": \"$USER_EMAIL\",
\"room_type\": \"single\",
\"payment_method\": \"paypal\",
\"transaction_id\": \"txn_test_script_123\"
}" | jq .
check_curl_error
echo "----------------------"


# --- 11. Test Upcoming Bookings (Should show 1 confirmed booking) ---
echo "11. Fetching my upcoming bookings (GET /bookings/my-upcoming)"
curl -s -X 'GET' \
  "$BASE_URL/bookings/my-upcoming" \
  -H 'accept: application/json' \
  -H "Authorization: Bearer $TOKEN" | jq .
check_curl_error
echo "----------------------"


# --- 12. Test Cancel Pending Booking ---
echo "12. Cancelling pending booking (ID: $PENDING_BOOKING_ID) (DELETE /bookings/{id}/cancel)"
curl -s -X 'DELETE' \
  "$BASE_URL/bookings/$PENDING_BOOKING_ID/cancel" \
  -H 'accept: application/json' \
  -H "Authorization: Bearer $TOKEN" | jq .
check_curl_error
echo "----------------------"


# --- 13. Test Delete Room (Should Fail due to confirmed booking) ---
echo "13. Testing Delete Room (ID: $SINGLE_ROOM_ID). Should FAIL (409 Conflict - has bookings)."
curl -s -X 'DELETE' \
  "$BASE_URL/rooms/$SINGLE_ROOM_ID" \
  -H 'accept: application/json' \
  -H "Authorization: Bearer $TOKEN" | jq .
check_curl_error
echo "----------------------"

# --- 14. Test Delete Room (Should Succeed since booking was cancelled) ---
echo "14. Testing Delete Room (ID: $DOUBLE_ROOM_ID). Should SUCCEED (no active bookings)."
curl -s -X 'DELETE' \
  "$BASE_URL/rooms/$DOUBLE_ROOM_ID" \
  -H 'accept: application/json' \
  -H "Authorization: Bearer $TOKEN" | jq .
check_curl_error
echo "----------------------"


# --- 15. Test Password Reset Flow (Interactive) ---
echo "15. Testing Password Reset Flow"
echo "    (Requesting reset for $USER_EMAIL...)"
curl -s -X 'POST' \
  "$BASE_URL/users/forgot-password" \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d "{
\"email\": \"$USER_EMAIL\"
}" | jq .
check_curl_error

echo ""
echo "!!! ACTION REQUIRED: Check your FastAPI server console for the password reset token. !!!"
read -p "Paste the token here and press Enter: " RESET_TOKEN

if [ -z "$RESET_TOKEN" ]; then
    echo "No token provided. Skipping password reset."
else
    echo "   (Submitting new password '$NEW_PASSWORD' with token...)"
    curl -s -X 'POST' \
      "$BASE_URL/users/reset-password" \
      -H 'accept: application/json' \
      -H 'Content-Type: application/json' \
      -d "{
    \"token\": \"$RESET_TOKEN\",
    \"new_password\": \"$NEW_PASSWORD\"
    }" | jq .
    check_curl_error
fi
echo "----------------------"


# --- 16. Test New Login (with new password) ---
echo "16. Attempting login with new password '$NEW_PASSWORD'"
LOGIN_RESPONSE_NEW_PASS=$(curl -s -X 'POST' \
  "$BASE_URL/users/login" \
  -H 'accept: application/json' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d "grant_type=password&username=$USER_EMAIL&password=$NEW_PASSWORD")
check_curl_error
echo "$LOGIN_RESPONSE_NEW_PASS" | jq .

# Capture new token for final delete, if successful
TOKEN_NEW=$(echo "$LOGIN_RESPONSE_NEW_PASS" | jq -r .access_token)
if [ "$TOKEN_NEW" != "null" ] && [ -n "$TOKEN_NEW" ]; then
    TOKEN=$TOKEN_NEW
fi
echo "----------------------"


# --- 17. Test Delete User Account ---
echo "17. Deleting user account (DELETE /users/me)"
curl -s -X 'DELETE' \
  "$BASE_URL/users/me" \
  -H 'accept: application/json' \
  -H "Authorization: Bearer $TOKEN" | jq .
check_curl_error
echo "----------------------"

echo "--- Test Script Complete ---"