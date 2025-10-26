import bcrypt, os, re
from datetime import datetime, date, time, timedelta, timezone
from dotenv import load_dotenv
from supabase import create_client, Client
from postgrest.exceptions import APIError
import secrets
import hashlib
VALID_ROOM_TYPES = {'single','double','suite','deluxe','economy'}

PAYMENT_METHOD ={'credit_card', 'paypal', 'bank_transfer', 'cash'}

PAYMENT_STATUS = {'pending', 'completed', 'failed', 'refunded'}

load_dotenv()
url: str = os.environ.get("supabase_url")
key: str = os.environ.get("supabase_key")

supabase: Client = create_client(url, key)

def password_hash_function(pwd: str) -> str:
   salt = bcrypt.gensalt()
   hashed_bytes = bcrypt.hashpw(pwd.encode('utf-8'), salt)
   return hashed_bytes.decode('utf-8')

def create_newuser(firstname: str, lastname: str, username: str, email: str, phone_number: str, password: str):
    
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
    if not re.fullmatch(regex, email):
        print("Invalid Email format.")
        return "Error: Invalid Email format." 

    try:
        hashed_password = password_hash_function(password)
    except Exception as e:
        print(f"Error during password hashing: {e}")
        return "Error: Password hashing failed."
        
    try:
        response = (
            supabase.table("users")
            .insert({
                "firstname": firstname,
                "lastname": lastname,
                "username": username,
                "email": email,
                "phone_number": phone_number,
                "password": hashed_password
            })
            .execute()
        )
        
        print(f"Successfully created user: {response.data[0]['username']}")
        return response

    except APIError as e:
        if "duplicate key value violates unique constraint" in e.message:
            if "users_email_key" in e.message:
                 print("Error: Email already exists.")
                 return "Error: Email already exists."
            if "users_username_key" in e.message:
                 print("Error: Username already exists.")
                 return "Error: Username already exists."
            if "users_phone_number_key" in e.message:
                print("Error: Phone number already exists.")
                return "Error: Phone number already exists."
        
        print(f"Database error: {e.message}")
        return f"Error: {e.message}"
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return "Error: An unexpected error occurred."


def create_room(room_number: str, room_type: str, price_per_night: float):
    """
    Creates a new room in the 'rooms' table with pre-validation.
    """
    if not room_number:
        print("Error: Room number cannot be empty.")
        return "Error: Room number cannot be empty."

    if room_type not in VALID_ROOM_TYPES:
        print(f"Error: Invalid room type '{room_type}'.")
        return f"Error: Invalid room type. Must be one of {VALID_ROOM_TYPES}."

    if price_per_night <= 0:
        print(f"Error: Price must be greater than 0. Got: {price_per_night}")
        return "Error: Price must be greater than 0."

    try:
        response = (
            supabase.table("rooms")
            .insert({
                "room_number": room_number,
                "room_type": room_type,
                "price_per_night": price_per_night
            })
            .execute()
        )

        print(f"Successfully created room: {response.data[0]['room_number']}")
        return response

    except APIError as e:

        if "duplicate key value violates unique constraint" in e.message:
            if "rooms_room_number_key" in e.message:
                 print(f"Error: Room number '{room_number}' already exists.")
                 return f"Error: Room number '{room_number}' already exists."
        
        print(f"Database error: {e.message}")
        return f"Error: {e.message}"
    except Exception as e:

        print(f"An unexpected error occurred: {e}")
        return "Error: An unexpected error occurred."
    

def create_booking(user_id: int, room_id: int, check_in_str: str, check_out_str: str):
    """
    Creates a new booking after validating price, dates, and availability.
    """
    
    # --- 1. Validate Dates (Python-side) ---
    try:
        # Note: Use datetime.combine to avoid timezone issues.
        # We book from the start of check-in day to the start of check-out day.
        check_in_date = datetime.strptime(check_in_str, "%Y-%m-%d").date()
        check_out_date = datetime.strptime(check_out_str, "%Y-%m-%d").date()
    except ValueError:
        print("Error: Invalid date format. Use YYYY-MM-DD.")
        return "Error: Invalid date format. Use YYYY-MM-DD."

    if check_in_date < date.today():
        print("Error: Check-in date must be in the future.")
        return "Error: Check-in date must be in the future."
        
    if check_out_date <= check_in_date:
        print("Error: Check-out date must be after check-in date.")
        return "Error: Check-out date must be after check-in date."

    # --- 2. Fetch Room Data (Get Price) ---
    try:
        room_response = (
            supabase.table("rooms")
            .select("price_per_night")
            .eq("room_id", room_id)
            .execute()
        )
        if not room_response.data:
            print(f"Error: Room with ID {room_id} not found.")
            return f"Error: Room with ID {room_id} not found."
        
        room_per_day_price = float(room_response.data[0]['price_per_night'])

    except APIError as e:
        print(f"Database error fetching room: {e.message}")
        return f"Error: {e.message}"
    except Exception as e:
        print(f"Unexpected error: {e}")
        return f"Error: {e}"

    # --- 3. Check for Booking Conflicts (Critical Logic) ---
    try:
        conflict_response = (
            supabase.table("bookings")
            .select("booking_id", count='exact')
            .eq("room_id", room_id)
            .in_("booking_status", ["confirmed", "pending"])
            .lt("check_in_date", check_out_str)
            .gt("check_out_date", check_in_str)
            .execute()
        )

        if conflict_response.count > 0:
            print("Error: Room is already booked for these dates.")
            return "Error: Room is already booked for these dates."

    except APIError as e:
        print(f"Database error checking conflicts: {e.message}")
        return f"Error: {e.message}"

    # --- 4. Calculate Price ---
    num_nights = (check_out_date - check_in_date).days
    total_price = room_per_day_price * num_nights

    # --- 5. Insert the Booking ---
    try:
        booking_response = (
            supabase.table("bookings")
            .insert({
                "user_id": user_id,
                "room_id": room_id,
                "room_per_day_price": room_per_day_price,
                "check_in_date": check_in_str,
                "check_out_date": check_out_str,
                "total_price": total_price
            })
            .execute()
        )
        
        print(f"Booking created successfully: ID {booking_response.data[0]['booking_id']}")
        return booking_response

    except APIError as e:
        if "foreign key constraint" in e.message:
            if "bookings_user_id_fkey" in e.message:
                print(f"Error: User with ID {user_id} not found.")
                return f"Error: User with ID {user_id} not found."
        
        print(f"Database error creating booking: {e.message}")
        return f"Error: {e.message}"
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return "Error: An unexpected error occurred."


def check_reservation(
    room_type: str, 
    booking_status: str,
    firstname: str = None, 
    lastname: str = None, 
    email: str = None, 
    phonenumber: str = None
):
    """
    Finds a reservation for check-in TODAY, matching the
    customer's details and a *specific status*.
    """
    if room_type not in VALID_ROOM_TYPES:
        print(f"Error: Invalid room type '{room_type}'.")
        return f"Error: Invalid room type. Must be one of {VALID_ROOM_TYPES}."

    if email:
        regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
        if not re.fullmatch(regex, email):
            print("Invalid Email format.")
            return "Error: Invalid Email format."
            
    today_str = date.today().isoformat() 

    try:
        # 1. Start building the base query
        query = (
            supabase.table("bookings")
            .select(
                "booking_id",
                "check_in_date",
                "check_out_date",
                "total_price",
                "users ( user_id, firstname, lastname, email )",
                "rooms ( room_number, room_type )"
            )
            .eq("booking_status", booking_status) 
            .eq("check_in_date", today_str)
            .eq("rooms.room_type", room_type)
        )
        
        # --- START FIX ---
        # 2. Apply user filters directly
        if phonenumber:
            query = query.eq("users.phone_number", phonenumber)
        if email:
            query = query.eq("users.email", email)
        if firstname and lastname:
            # The 'and' filter syntax is different, but this works
            query = query.filter(f"and(users.firstname.eq.{firstname},users.lastname.eq.{lastname})", "is", "null")

        # 3. Check that *at least one* filter was added
        if not (phonenumber or email or (firstname and lastname)):
            print("Error: At least one identifier (phone, email, or full name) must be provided.")
            return "Error: No identifier provided."
        
        # 4. Now execute the correctly built query
        response = query.execute()
        # --- END FIX ---
        
        if response.data:
            print(f"Successfully found {len(response.data)} matching reservation(s).")
            return response.data
        else:
            print(f"No bookings with status '{booking_status}' found for today.")
            return []

    except APIError as e:
        print(f"Database error: {e.message}")
        return f"Error: {e.message}"
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return "Error: An unexpected error occurred."

# SELECT room_id, room_number, price_per_night FROM rooms
#WHERE is_available = true AND room_type = 'suite';
def find_available_rooms_for_dates(room_type: str, check_in_str: str, check_out_str: str):
    """
    Finds all rooms of a specific type that are available
    for a given date range.
    """
    
    try:
        check_in_date = datetime.strptime(check_in_str, "%Y-%m-%d").date()
        check_out_date = datetime.strptime(check_out_str, "%Y-%m-%d").date()
    except ValueError:
        print("Error: Invalid date format. Use YYYY-MM-DD.")
        return "Error: Invalid date format. Use YYYY-MM-DD."

    if check_in_date < date.today():
        return "Error: Check-in date must be in the future."
        
    if check_out_date <= check_in_date:
        return "Error: Check-out date must be after check-in date."
    
    if room_type not in VALID_ROOM_TYPES:
        print(f"Error: Invalid room type '{room_type}'.")
        return f"Error: Invalid room type. Must be one of {VALID_ROOM_TYPES}."
    try:
        # --- 3. Find all conflicting booking room_ids ---
        # This is the "overlap" query.
        conflict_response = (
            supabase.table("bookings")
            .select("room_id")
            .in_("booking_status", ["confirmed", "pending"])
            .lt("check_in_date", check_out_str)
            .gt("check_out_date", check_in_str)
            .execute()
        )

        conflicting_room_ids = {booking['room_id'] for booking in conflict_response.data}
        
        rooms_query = (
            supabase.table("rooms")
            .select("room_id, room_number, price_per_night")
            .eq("is_available", True)
            .eq("room_type", room_type)
        )
        
        # --- 5. Filter out the conflicting rooms ---
        if conflicting_room_ids:
            rooms_query = rooms_query.not_("room_id", "in", list(conflicting_room_ids))
            
        available_rooms_response = rooms_query.execute()

        if available_rooms_response.data:
            print(f"Found {len(available_rooms_response.data)} available rooms.")
            return available_rooms_response.data
        else:
            print(f"No rooms of type '{room_type}' are available for those dates.")
            return []

    except APIError as e:
        print(f"Database error: {e.message}")
        return f"Error: {e.message}"
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return "Error: An unexpected error occurred."
    
def get_user_upcoming_bookings_by_email(email: str):
    """
    Fetches all 'confirmed' bookings for a user (via email)
    that are for today or in the future.
    """
    
    # --- 1. Validate Email ---
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
    if not re.fullmatch(regex, email):
        print("Invalid Email format.")
        return "Error: Invalid Email format!"

    # --- 2. Get Today's Date ---
    today_str = date.today().isoformat()

    try:
        # --- 3. Execute Query ---
        response = (
            supabase.table("bookings")
            .select(
                "booking_id, check_in_date, check_out_date, total_price, "
                "rooms ( room_number, room_type ), "  # Select from joined rooms
                "users ( email, firstname, lastname )"   # Select from joined users
            )
            
            # --- THE FIX ---
            # Filter on the 'users' table using dot-notation
            .eq("users.email", email) 
            
            # Continue with original filters
            .eq("booking_status", "confirmed")
            .gte("check_in_date", today_str)
            
            .execute()
        )
        
        # --- 4. Handle Response ---
        if response.data:
            print(f"Found {len(response.data)} upcoming bookings for user {email}.")
            return response.data
        else:
            print(f"No upcoming confirmed bookings found for user {email}.")
            return []

    except APIError as e:
        print(f"Database error: {e.message}")
        return f"Error: {e.message}"
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return "Error: An unexpected error occurred."
    
def update_user_profile(user_id: int, firstname: str = None, lastname: str = None, email: str = None, phone_number: str = None):
    update_data = {}
    if firstname is not None:
        update_data["firstname"] = firstname
    if lastname is not None:
        update_data["lastname"] = lastname
    if email is not None:
        regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
        if not re.fullmatch(regex, email):
            print("Invalid Email format.")
            return "Error: Invalid Email format."
        update_data["email"] = email
    if phone_number is not None:
        update_data["phone_number"] = phone_number

    if not update_data:
        print("No data provided to update.")
        return "No data provided to update."

    try:
        response = (
            supabase.table("users")
            .update(update_data)
            .eq("user_id", user_id)
            .execute()
        )
        print(f"Successfully updated profile for user {user_id}")
        return response
    
    except APIError as e:
        if "duplicate key value violates unique constraint" in e.message:
            if "users_email_key" in e.message:
                 return "Error: That email is already taken."
            if "users_phone_number_key" in e.message:
                return "Error: That phone number is already taken."
        
        print(f"Database error: {e.message}")
        return f"Error: {e.message}"
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return "Error: An unexpected error occurred."

# --- Add these to your logic.py file ---

def get_user_by_email(email: str):
    """
    Finds a single user and their ID based on email.
    """
    try:
        response = (
            supabase.table("users")
            .select("user_id, firstname, email")
            .eq("email", email)
            .limit(1) # Ensure we only get one
            .execute()
        )
        if response.data:
            return response.data[0] # Return the user object
        else:
            return None # No user found
    except APIError as e:
        print(f"Error fetching user: {e.message}")
        return None

def hash_token(token: str) -> str:
    """Hashes a token using SHA-256 for secure DB storage."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

def send_reset_email(email: str, token: str):
    """
    --- MOCK FUNCTION ---
    This is where you would integrate with an email service
    like SendGrid, Mailgun, or Supabase's built-in Auth emailer.
    """
    reset_link = f"url+token"
    print("--- SIMULATING EMAIL ---")
    print(f"To: {email}")
    print(f"Subject: Reset Your Password")
    print(f"Click here: {reset_link}")
    print("--- END SIMULATION ---")
    return True

def request_password_reset(email: str):
    """
    Starts the "Forgot Password" process.
    Finds the user, generates a token, and sends the reset email.
    """
    # 1. Find the user
    user = get_user_by_email(email)
    

    if not user:
        print(f"Password reset requested for non-existent user: {email}")
        return "Success: If an account with this email exists, a reset link has been sent."

    try:
        # 2. Generate a secure token
        token = secrets.token_urlsafe(32) # A 32-byte secure token
        token_hash = hash_token(token) # Hash it for database storage
        
        # 3. Set an expiry time (e.g., 1 hour from now)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        # 4. Store the *hash* in the database
        (
            supabase.table("password_resets")
            .insert({
                "user_id": user['user_id'],
                "token_hash": token_hash,
                "expires_at": expires_at.isoformat()
            })
            .execute()
        )
        
        # 5. Send the *plain-text* token to the user
        send_reset_email(email, token)
        
        return "Success: If an account with this email exists, a reset link has been sent."

    except APIError as e:
        print(f"Database error during password reset: {e.message}")
        return "Error: An internal error occurred."
    except Exception as e:
        print(f"Unexpected error: {e}")
        return "Error: An internal error occurred."
    
def verify_and_reset_password(token: str, new_password: str):
    """
    Verifies a password reset token and updates the user's password.
    """
    # 1. Hash the token provided by the user
    token_hash = hash_token(token)
    
    try:
        # 2. Find the token in the database
        response = (
            supabase.table("password_resets")
            .select("user_id, expires_at")
            .eq("token_hash", token_hash)
            .limit(1)
            .execute()
        )
        
        if not response.data:
            print("Invalid or expired token used.")
            return "Error: Invalid or expired token."
            
        reset_request = response.data[0]
        expires_at = datetime.fromisoformat(reset_request['expires_at'])
        user_id = reset_request['user_id']
        
        # 3. Check if it's expired
        if expires_at < datetime.now(timezone.utc):
            print("Expired token used.")
            return "Error: Invalid or expired token."
            
        # 4. If valid, update the user's password
        # This re-uses the secure function we already built!
        update_result = update_user_password(
            user_id=user_id, 
            new_password=new_password
        )
        
        if "Error" in str(update_result):
            return "Error: Could not update password."
            
        # 5. Invalidate the token by deleting it
        (
            supabase.table("password_resets")
            .delete()
            .eq("token_hash", token_hash)
            .execute()
        )
        
        print(f"Successfully reset password for user {user_id}")
        return "Success: Your password has been reset."

    except APIError as e:
        print(f"Database error: {e.message}")
        return "Error: An internal error occurred."
    except Exception as e:
        print(f"Unexpected error: {e}")
        return "Error: An internal error occurred."

def update_user_password(user_id: int , new_password: str):
    '''
    write a regular expression to check the password strength.
    '''
    if not new_password or len(new_password) < 8:
        print("Error: Password must be at least 8 characters.")
        return "Error: Password must be at least 8 characters."
        
    try:
        hashed_password = password_hash_function(new_password)
        response = (
            supabase.table("users")
            .update({"password": hashed_password})
            .eq("user_id", user_id)
            .execute()
        )
        print(f"Successfully updated password for user {user_id}")
        return response
    
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return "Error: An unexpected error occurred."

def confirm_payment(booking_id: int, user_id: int, amount: float, payment_method: str, transaction_id: str
):
    """
    Calls the Postgres transaction function to log a payment
    and confirm the booking atomically.
    """
    if payment_method not in PAYMENT_METHOD:
        return "Error: Invalid payment method"
        
    try:
        supabase.rpc('process_payment_and_confirm', {
            'booking_id_to_confirm': booking_id,
            'user_id_for_payment': user_id,
            'payment_amount': amount,
            'method': payment_method,
            'new_transaction_id': transaction_id
        }).execute()
        
        print(f"Successfully confirmed booking {booking_id}")
        return "Success"

    except APIError as e:
        print(f"Error during transaction: {e.message}")
        print("Transaction was rolled back.")
        return f"Error: {e.message}"
    except Exception as e:
        return f"Error: An unexpected error occurred."
    

def process_check_in_payment(
    email: str, 
    room_type: str, 
    payment_method: str, 
    transaction_id: str
):
    """
    This is the main workflow function.
    1. Finds a pending booking using user details.
    2. Extracts the internal IDs.
    3. Calls the transaction function to confirm payment.
    """
    
    print(f"Finding pending check-in for {email}...")
    reservations = check_reservation(room_type=room_type, email=email, booking_status="pending")
    
    if isinstance(reservations, str):
        return f"Find step failed: {reservations}"
    
    if not reservations:
        return "Error: No pending reservation found for today with those details."
    
    if len(reservations) > 1:
        return "Error: Found multiple pending reservations. Please contact staff."

    booking_to_confirm = reservations[0]


    try:

        internal_booking_id = booking_to_confirm['booking_id']
        internal_user_id = booking_to_confirm['users']['user_id']
        price_to_charge = booking_to_confirm['total_price']
    except (KeyError, TypeError) as e:
        print(f"Error: Found booking, but it's missing key data: {e}")
        return "Error: Found booking, but data was incomplete."

    print(f"Found booking {internal_booking_id}. Ready to charge ${price_to_charge}.")
    
    # --- STEP 4: ACT ---
    print(f"Processing payment for booking {internal_booking_id}...")
    confirmation_result = confirm_payment(
        booking_id=internal_booking_id,
        user_id=internal_user_id,
        amount=price_to_charge,
        payment_method=payment_method,
        transaction_id=transaction_id
    )
    
    # This will return "Success" or an error message
    return confirmation_result


def cancel_pending_booking(booking_id: int):
    """
    Deletes a booking record IF its status is 'pending'.
    Any related reviews will be auto-deleted by the DB (ON DELETE CASCADE).
    """
    try:
        response = (
            supabase.table("bookings")
            .delete()
            .eq("booking_id", booking_id)
            .eq("booking_status", "pending")
            .execute()
        )
        
        if response.data:
            print(f"Successfully canceled pending booking {booking_id}.")
            return "Success"
        else:

            print(f"Error: No pending booking found with ID {booking_id} to cancel.")
            return "Error: Booking not found or was not pending."

    except APIError as e:
        print(f"Database error: {e.message}")
        return f"Error: {e.message}"
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return "Error: An unexpected error occurred."
    

def delete_room(room_id: int):
    try:
        response = (
            supabase.table("rooms")
            .delete()
            .eq("room_id", room_id)
            .execute()
        )
        
        if response.data:
            print(f"Successfully deleted room {room_id}.")
            return "Success"
        else:
            print(f"Error: No room found with ID {room_id}.")
            return "Error: Room not found."

    except APIError as e:
        # This is the crucial part: catching the foreign key violation
        if "violates foreign key constraint" in e.message and "on table \"bookings\"" in e.message:
            print(f"Error: Cannot delete room {room_id} because it has existing bookings.")
            print("This is the 'ON DELETE RESTRICT' safeguard working correctly.")
            return "Error: Room has existing bookings."
        else:
            # Handle other, unexpected database errors
            print(f"Database error: {e.message}")
            return f"Error: {e.message}"
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return "Error: An unexpected error occurred."
    
def delete_user(user_id: int):
    """
    Deletes a user.
    Related records in bookings, reviews, and payments will
    have their 'user_id' field set to NULL (ON DELETE SET NULL).
    """
    try:
        response = (
            supabase.table("users")
            .delete()
            .eq("user_id", user_id)
            .execute()
        )
        
        if response.data:
            print(f"Successfully deleted user {user_id}.")
            print("Related historical records have been anonymized (user_id set to NULL).")
            return "Success"
        else:
            print(f"Error: No user found with ID {user_id}.")
            return "Error: User not found."

    except APIError as e:
        print(f"Database error: {e.message}")
        return f"Error: {e.message}"
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return "Error: An unexpected error occurred."
    
def get_user_for_login(email: str):

    try:
        response = (
            supabase.table("users")
            .select("user_id, password") # Only select what's needed
            .eq("email", email)
            .limit(1)
            .execute()
        )
        if response.data:
            return response.data[0] # Returns {'user_id': 1, 'password': '...'}
        else:
            return None
    except APIError as e:
        print(f"Error fetching user for login: {e.message}")
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a stored bcrypt hash.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        print(f"Error verifying password: {e}")
        return False