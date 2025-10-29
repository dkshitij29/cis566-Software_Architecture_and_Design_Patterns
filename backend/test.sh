#!/bin/bash

# --- Dynamic Configuration ---
BASE_URL="https://cis566-software-architecture-and-design-oqof.onrender.com"
#BASE_URL="http://127.0.0.1:8000"
TIMESTAMP=$(date +%s)
USER_EMAIL="user_$TIMESTAMP@example.com"
USERNAME="user_$TIMESTAMP"
PASSWORD="testpassword123"
TODAY_DATE=$(date +"%Y-%m-%d")
TOMORROW_DATE=$(date -v+1d +"%Y-%m-%d") # For macOS/BSD
# For Linux, use: TOMORROW_DATE=$(date -d "+1 day" +"%Y-%m-%d")

# --- Global Variables (will be set by script) ---
TOKEN=""
SINGLE_ROOM_ID=""

# Helper function to check if curl failed (e.g., connection refused)
check_curl_error() {
  if [ $? -ne 0 ]; then
    echo "!!! FATAL ERROR: curl command failed. Is the server running? !!!"
    exit 1
  fi
}

echo "--- API Test Script ---"
echo "Base URL: $BASE_URL"
echo "Today: $TODAY_DATE"
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

# Check if signup failed
DETAIL=$(echo "$SIGNUP_RESPONSE" | jq -r .detail)
if [ -n "$DETAIL" ] && [ "$DETAIL" != "null" ]; then
    echo "!!! FATAL ERROR: Signup failed: $DETAIL !!!"
    exit 1
fi
echo "----------------------"


# --- 3. Log In and Capture Token ---
echo "3. Logging in as new user (POST /users/login)"
LOGIN_RESPONSE=$(curl -s -X 'POST' \
  "$BASE_URL/users/login" \
  -H 'accept: application/json' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d "grant_type=password&username=$USER_EMAIL&password=$PASSWORD")
check_curl_error

# Parse the token
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
echo "5. Creating Rooms (POST /rooms/)"

# Create a 'single' room for today's test
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
if [ "$SINGLE_ROOM_ID" == "null" ] || [ -z "$SINGLE_ROOM_ID" ]; then
    echo "!!! FATAL ERROR: Could not create 'single' room. !!!"
    echo "$SINGLE_ROOM_RESPONSE" | jq .
    exit 1
fi
echo "Created 'single' room (ID: $SINGLE_ROOM_ID):"
echo "$SINGLE_ROOM_RESPONSE" | jq .
echo "----------------------"


# --- 6. Test Availability (Today) ---
echo "6. Checking 'single' room availability for today (GET /rooms/available)"
curl -s -X 'GET' \
  "$BASE_URL/rooms/available?room_type=single&check_in=$TODAY_DATE&check_out=$TOMORROW_DATE" \
  -H 'accept: application/json' | jq .
check_curl_error
echo "----------------------"


# --- 7. Test Booking (Today) ---
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


# --- 8. Test Availability (Conflict) ---
echo "8. Re-checking 'single' room availability (should now be empty)"
curl -s -X 'GET' \
  "$BASE_URL/rooms/available?room_type=single&check_in=$TODAY_DATE&check_out=$TOMORROW_DATE" \
  -H 'accept: application/json' | jq .
check_curl_error
echo "----------------------"


# --- 9. Test Check-In Flow ---
echo "9. Processing Check-In for today's 'single' room (POST /bookings/check-in)"
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


# --- 10. Test Password Reset Flow (Interactive) ---
echo "10. Testing Password Reset Flow"
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
echo "!!! ACTION REQUIRED !!!"
echo "Check your FastAPI server console for the password reset token."
read -p "Paste the token here and press Enter: " RESET_TOKEN

if [ -z "$RESET_TOKEN" ]; then
    echo "No token provided. Skipping password reset."
else
    echo "   (Submitting new password 'newPass123' with token...)"
    curl -s -X 'POST' \
      "$BASE_URL/users/reset-password" \
      -H 'accept: application/json' \
      -H 'Content-Type: application/json' \
      -d "{
    \"token\": \"$RESET_TOKEN\",
    \"new_password\": \"newPass123\"
    }" | jq .
    check_curl_error
fi
echo "----------------------"


# --- 11. Test New Login ---
echo "11. Attempting login with new password 'newPass123'"
curl -s -X 'POST' \
  "$BASE_URL/users/login" \
  -H 'accept: application/json' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d "grant_type=password&username=$USER_EMAIL&password=newPass123" | jq .
check_curl_error
echo "----------------------"
echo "--- Test Script Complete ---"