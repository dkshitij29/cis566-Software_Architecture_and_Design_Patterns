import bcrypt, os, re, logging
from datetime import datetime, date, time, timedelta, timezone
from dotenv import load_dotenv
from supabase import create_client, Client
from postgrest.exceptions import APIError
import secrets
import hashlib

your_frontend = "frontend url"

logging.basicConfig(
    level=logging.INFO,  # Default level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


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
        logger.warning(f"Invalid Email format for attempt: {email}")
        return "Error: Invalid Email format." 

    try:
        hashed_password = password_hash_function(password)
    except Exception as e:
        logger.error(f"Error during password hashing: {e}", exc_info=True)
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
        
        user_email = response.data[0]['email']
        logger.info(f"Successfully created user. Email: {user_email}, UserID: {response.data[0]['user_id']}")
        return response

    except APIError as e:
        if "duplicate key value violates unique constraint" in e.message:
            if "users_email_key" in e.message:
                 logger.warning(f"Signup failed: Email already exists ({email})")
                 return "Error: Email already exists."
            if "users_username_key" in e.message:
                 logger.warning(f"Signup failed: Username already exists ({username})")
                 return "Error: Username already exists."
            if "users_phone_number_key" in e.message:
                logger.warning(f"Signup failed: Phone number already exists ({phone_number})")
                return "Error: Phone number already exists."
        
        logger.error(f"Database error on user creation: {e.message}", exc_info=True)
        return f"Error: {e.message}"
    except Exception as e:
        logger.critical(f"An unexpected error occurred during user creation: {e}", exc_info=True)
        return "Error: An unexpected error occurred."


def create_room(room_number: str, room_type: str, price_per_night: float):
    """
    Creates a new room in the 'rooms' table with pre-validation.
    """
    if not room_number:
        logger.warning("Create room failed: Room number was empty.")
        return "Error: Room number cannot be empty."

    if room_type not in VALID_ROOM_TYPES:
        logger.warning(f"Create room failed: Invalid room type '{room_type}'.")
        return f"Error: Invalid room type. Must be one of {VALID_ROOM_TYPES}."

    if price_per_night <= 0:
        logger.warning(f"Create room failed: Price must be greater than 0. Got: {price_per_night}")
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

        logger.info(f"Successfully created room: {response.data[0]['room_number']} (ID: {response.data[0]['room_id']})")
        return response

    except APIError as e:

        if "duplicate key value violates unique constraint" in e.message:
            if "rooms_room_number_key" in e.message:
                 logger.warning(f"Create room failed: Room number '{room_number}' already exists.")
                 return f"Error: Room number '{room_number}' already exists."
        
        logger.error(f"Database error on room creation: {e.message}", exc_info=True)
        return f"Error: {e.message}"
    except Exception as e:

        logger.critical(f"An unexpected error occurred during room creation: {e}", exc_info=True)
        return "Error: An unexpected error occurred."
    

def create_booking(user_id: int, room_id: int, check_in_str: str, check_out_str: str):
    """
    Creates a new booking after validating price, dates, and availability.
    """
    logger.debug(f"Attempting to create booking for user_id: {user_id}, room_id: {room_id}")

    try:
        check_in_date = datetime.strptime(check_in_str, "%Y-%m-%d").date()
        check_out_date = datetime.strptime(check_out_str, "%Y-%m-%d").date()
    except ValueError:
        logger.warning(f"Invalid date format on booking creation. Got: {check_in_str}, {check_out_str}")
        return "Error: Invalid date format. Use YYYY-MM-DD."

    if check_in_date < date.today():
        logger.warning(f"Booking failed: Check-in date in the past. Got: {check_in_date}")
        return "Error: Check-in date must be in the future."
        
    if check_out_date <= check_in_date:
        logger.warning(f"Booking failed: Check-out date not after check-in. Got: {check_in_date} -> {check_out_date}")
        return "Error: Check-out date must be after check-in date."

    try:
        room_response = (
            supabase.table("rooms")
            .select("price_per_night")
            .eq("room_id", room_id)
            .execute()
        )
        if not room_response.data:
            logger.warning(f"Booking failed: Room with ID {room_id} not found.")
            return f"Error: Room with ID {room_id} not found."
        
        room_per_day_price = float(room_response.data[0]['price_per_night'])
        logger.debug(f"Found room {room_id}, price_per_night: {room_per_day_price}")

    except APIError as e:
        logger.error(f"Database error fetching room {room_id}: {e.message}", exc_info=True)
        return f"Error: {e.message}"
    except Exception as e:
        logger.error(f"Unexpected error fetching room {room_id}: {e}", exc_info=True)
        return f"Error: {e}"

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
        
        logger.debug(f"Conflict check for room {room_id} ({check_in_str} to {check_out_str}) found {conflict_response.count} conflicts.")

        if conflict_response.count > 0:
            logger.warning(f"Booking failed: Room {room_id} is already booked for these dates.")
            return "Error: Room is already booked for these dates."

    except APIError as e:
        logger.error(f"Database error checking booking conflicts: {e.message}", exc_info=True)
        return f"Error: {e.message}"


    num_nights = (check_out_date - check_in_date).days
    total_price = room_per_day_price * num_nights
    logger.debug(f"Booking calculation: {num_nights} nights at ${room_per_day_price}/night = ${total_price}")


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
        
        logger.info(f"Booking created successfully: ID {booking_response.data[0]['booking_id']} for user {user_id}")
        return booking_response

    except APIError as e:
        if "foreign key constraint" in e.message:
            if "bookings_user_id_fkey" in e.message:
                logger.warning(f"Booking failed: User with ID {user_id} not found.")
                return f"Error: User with ID {user_id} not found."
        
        logger.error(f"Database error creating booking: {e.message}", exc_info=True)
        return f"Error: {e.message}"
    except Exception as e:
        logger.critical(f"An unexpected error occurred during booking creation: {e}", exc_info=True)
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
    logger.debug(f"Checking reservation for today. Room type: {room_type}, Status: {booking_status}, Email: {email}")
    
    if room_type not in VALID_ROOM_TYPES:
        logger.warning(f"Invalid room type '{room_type}' in check_reservation.")
        return f"Error: Invalid room type. Must be one of {VALID_ROOM_TYPES}."

    if email:
        regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
        if not re.fullmatch(regex, email):
            logger.warning(f"Invalid Email format in check_reservation: {email}")
            return "Error: Invalid Email format."
            
    today_str = date.today().isoformat() 
    logger.debug(f"Searching for check-in date: {today_str}")

    try:

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
        

        if phonenumber:
            query = query.eq("users.phone_number", phonenumber)
        if email:
            query = query.eq("users.email", email)
        if firstname and lastname:
            query = query.filter(f"and(users.firstname.eq.{firstname},users.lastname.eq.{lastname})", "is", "null")


        if not (phonenumber or email or (firstname and lastname)):
            logger.warning("check_reservation failed: No identifier (phone, email, or name) was provided.")
            return "Error: No identifier provided."
        

        response = query.execute()
        
        if response.data:
            logger.info(f"Successfully found {len(response.data)} matching reservation(s) for {email or phonenumber}.")
            return response.data
        else:
            logger.info(f"No bookings with status '{booking_status}' found for today for {email or phonenumber}.")
            return []

    except APIError as e:
        logger.error(f"Database error in check_reservation: {e.message}", exc_info=True)
        return f"Error: {e.message}"
    except Exception as e:
        logger.critical(f"An unexpected error occurred in check_reservation: {e}", exc_info=True)
        return "Error: An unexpected error occurred."


def find_available_rooms_for_dates(room_type: str, check_in_str: str, check_out_str: str):
    """
    Finds all rooms of a specific type that are available
    for a given date range.
    """
    logger.debug(f"Finding available rooms. Type: {room_type}, Check-in: {check_in_str}, Check-out: {check_out_str}")
    
    try:
        check_in_date = datetime.strptime(check_in_str, "%Y-%m-%d").date()
        check_out_date = datetime.strptime(check_out_str, "%Y-%m-%d").date()
    except ValueError:
        logger.warning(f"Invalid date format in find_available_rooms. Got: {check_in_str}, {check_out_str}")
        return "Error: Invalid date format. Use YYYY-MM-DD."

    if check_in_date < date.today():
        logger.warning(f"find_available_rooms failed: Check-in date in the past. Got: {check_in_date}")
        return "Error: Check-in date must be in the future."
        
    if check_out_date <= check_in_date:
        logger.warning(f"find_available_rooms failed: Check-out date not after check-in. Got: {check_in_date} -> {check_out_date}")
        return "Error: Check-out date must be after check-in date."
    
    if room_type not in VALID_ROOM_TYPES:
        logger.warning(f"find_available_rooms failed: Invalid room type '{room_type}'.")
        return f"Error: Invalid room type. Must be one of {VALID_ROOM_TYPES}."

    try:

        conflict_response = (
            supabase.table("bookings")
            .select("room_id")
            .in_("booking_status", ["confirmed", "pending"])
            .lt("check_in_date", check_out_str)
            .gt("check_out_date", check_in_str)
            .execute()
        )
        
        conflicting_room_ids = {booking['room_id'] for booking in conflict_response.data}
        logger.debug(f"Found {len(conflicting_room_ids)} conflicting room IDs: {conflicting_room_ids}")
        
        rooms_query = (
            supabase.table("rooms")
            .select("room_id, room_number, room_type, price_per_night")
            .eq("is_available", True)
            .eq("room_type", room_type)
        )
        

        if conflicting_room_ids:
            value_string = f"({','.join(map(str, conflicting_room_ids))})"
            logger.debug(f"Filtering out rooms with IDs: {value_string}")
            rooms_query = rooms_query.filter("room_id", "not.in", value_string)

        available_rooms_response = rooms_query.execute()

        if available_rooms_response.data:
            logger.info(f"Found {len(available_rooms_response.data)} available rooms for type '{room_type}'.")
            return available_rooms_response.data
        else:
            logger.info(f"No rooms of type '{room_type}' are available for those dates.")
            return []

    except APIError as e:
        logger.error(f"Database error in find_available_rooms: {e.message}", exc_info=True)
        return f"Error: {e.message}"
    except Exception as e:
        logger.critical(f"An unexpected error in find_available_rooms: {e}", exc_info=True)
        return "Error: An unexpected error occurred."
    
def get_user_upcoming_bookings_by_email(email: str):
    """
    Fetches all 'confirmed' bookings for a user (via email)
    that are for today or in the future.
    """
    
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
    if not re.fullmatch(regex, email):
        logger.warning(f"Invalid Email format in get_user_upcoming_bookings: {email}")
        return "Error: Invalid Email format!"

    today_str = date.today().isoformat()
    logger.debug(f"Fetching upcoming bookings for {email} on or after {today_str}")

    try:
        response = (
            supabase.table("bookings")
            .select(
                "booking_id, check_in_date, check_out_date, total_price, "
                "rooms ( room_number, room_type ), "
                "users ( email, firstname, lastname )"
            )
            .eq("users.email", email) 
            .eq("booking_status", "confirmed")
            .gte("check_in_date", today_str)
            .execute()
        )
        
        if response.data:
            logger.info(f"Found {len(response.data)} upcoming bookings for user {email}.")
            return response.data
        else:
            logger.info(f"No upcoming confirmed bookings found for user {email}.")
            return []

    except APIError as e:
        logger.error(f"Database error in get_user_upcoming_bookings: {e.message}", exc_info=True)
        return f"Error: {e.message}"
    except Exception as e:
        logger.critical(f"An unexpected error in get_user_upcoming_bookings: {e}", exc_info=True)
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
            logger.warning(f"Invalid email format on profile update for user {user_id}: {email}")
            return "Error: Invalid Email format."
        update_data["email"] = email
    if phone_number is not None:
        update_data["phone_number"] = phone_number

    if not update_data:
        logger.warning(f"No data provided to update for user {user_id}.")
        return "No data provided to update."

    logger.debug(f"Attempting to update profile for user {user_id} with data: {update_data.keys()}")
    try:
        response = (
            supabase.table("users")
            .update(update_data)
            .eq("user_id", user_id)
            .execute()
        )
        logger.info(f"Successfully updated profile for user {user_id}")
        return response
    
    except APIError as e:
        if "duplicate key value violates unique constraint" in e.message:
            if "users_email_key" in e.message:
                 logger.warning(f"Profile update failed: Email already taken ({email})")
                 return "Error: That email is already taken."
            if "users_phone_number_key" in e.message:
                logger.warning(f"Profile update failed: Phone number already taken ({phone_number})")
                return "Error: That phone number is already taken."
        
        logger.error(f"Database error on profile update for user {user_id}: {e.message}", exc_info=True)
        return f"Error: {e.message}"
    except Exception as e:
        logger.critical(f"An unexpected error on profile update for user {user_id}: {e}", exc_info=True)
        return "Error: An unexpected error occurred."

def get_user_by_email(email: str):
    """
    Finds a single user and their ID based on email.
    """
    logger.debug(f"Searching for user by email: {email}")
    try:
        response = (
            supabase.table("users")
            .select("user_id, firstname, email")
            .eq("email", email)
            .limit(1)
            .execute()
        )
        if response.data:
            logger.debug(f"Found user: {response.data[0]}")
            return response.data[0] # Return the user object
        else:
            logger.debug(f"No user found with email: {email}")
            return None # No user found
    except APIError as e:
        logger.error(f"Error fetching user by email {email}: {e.message}", exc_info=True)
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
    reset_link = f"http://{your_frontend}.com/reset-password?token={token}"
    logger.info("--- SIMULATING EMAIL ---")
    logger.info(f"To: {email}")
    logger.info(f"Subject: Reset Your Password")
    logger.info(f"Click here: {reset_link}")
    logger.info(f"token:{token}")
    logger.debug(f"PASSWORD_RESET_TOKEN: {token}")
    logger.info("--- END SIMULATION ---")
    return True

def request_password_reset(email: str):
    """
    Starts the "Forgot Password" process.
    Finds the user, generates a token, and sends the reset email.
    """
    logger.debug(f"Password reset requested for email: {email}")

    user = get_user_by_email(email)
    
    if not user:

        logger.warning(f"Password reset requested for non-existent user: {email}")
        return "Success: If an account with this email exists, a reset link has been sent."

    try:

        token = secrets.token_urlsafe(32)
        token_hash = hash_token(token) 
        

        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        

        (
            supabase.table("password_resets")
            .insert({
                "user_id": user['user_id'],
                "token_hash": token_hash,
                "expires_at": expires_at.isoformat()
            })
            .execute()
        )
        logger.debug(f"Stored reset token hash for user {user['user_id']}")
        

        send_reset_email(email, token)
        
        logger.info(f"Password reset email initiated for user {user['user_id']} ({email})")
        return "Success: If an account with this email exists, a reset link has been sent."

    except APIError as e:
        logger.error(f"Database error during password reset request for {email}: {e.message}", exc_info=True)
        return "Error: An internal error occurred."
    except Exception as e:
        logger.critical(f"Unexpected error during password reset request for {email}: {e}", exc_info=True)
        return "Error: An internal error occurred."
    
def verify_and_reset_password(token: str, new_password: str):
    """
    Verifies a password reset token and updates the user's password.
    """

    token_hash = hash_token(token)
    logger.debug(f"Attempting to verify password reset with token hash: {token_hash[:10]}...")
    
    try:

        response = (
            supabase.table("password_resets")
            .select("user_id, expires_at")
            .eq("token_hash", token_hash)
            .limit(1)
            .execute()
        )
        
        if not response.data:
            logger.warning(f"Invalid or expired token used. Hash: {token_hash[:10]}...")
            return "Error: Invalid or expired token."
            
        reset_request = response.data[0]
        expires_at = datetime.fromisoformat(reset_request['expires_at'])
        user_id = reset_request['user_id']
        

        if expires_at < datetime.now(timezone.utc):
            logger.warning(f"Expired token used for user {user_id}. Expiry: {expires_at}")
            return "Error: Invalid or expired token."
            

        logger.debug(f"Token verified for user {user_id}. Proceeding to password update.")
        update_result = update_user_password(
            user_id=user_id, 
            new_password=new_password
        )
        
        if "Error" in str(update_result):
            logger.error(f"Password update failed for user {user_id} after token verification.")
            return "Error: Could not update password."
            

        (
            supabase.table("password_resets")
            .delete()
            .eq("token_hash", token_hash)
            .execute()
        )
        
        logger.info(f"Successfully reset password for user {user_id}")
        return "Success: Your password has been reset."

    except APIError as e:
        logger.error(f"Database error during password reset verification: {e.message}", exc_info=True)
        return "Error: An internal error occurred."
    except Exception as e:
        logger.critical(f"Unexpected error during password reset verification: {e}", exc_info=True)
        return "Error: An internal error occurred."

def update_user_password(user_id: int , new_password: str):
    '''
    Updates a user's password hash in the database.
    '''
    if not new_password or len(new_password) < 8:
        logger.warning(f"Password update failed for user {user_id}: Password must be at least 8 characters.")
        return "Error: Password must be at least 8 characters."
        
    try:
        hashed_password = password_hash_function(new_password)
        response = (
            supabase.table("users")
            .update({"password": hashed_password})
            .eq("user_id", user_id)
            .execute()
        )
        logger.info(f"Successfully updated password for user {user_id}")
        return response
    
    except Exception as e:
        logger.error(f"An unexpected error occurred during password update for user {user_id}: {e}", exc_info=True)
        return "Error: An unexpected error occurred."

def confirm_payment(booking_id: int, user_id: int, amount: float, payment_method: str, transaction_id: str
):
    """
    Calls the Postgres transaction function to log a payment
    and confirm the booking atomically.
    """
    if payment_method not in PAYMENT_METHOD:
        logger.warning(f"Confirm payment failed: Invalid payment method '{payment_method}'")
        return "Error: Invalid payment method"
        
    logger.debug(f"Calling RPC 'process_payment_and_confirm' for booking {booking_id}")
    try:
        supabase.rpc('process_payment_and_confirm', {
            'booking_id_to_confirm': booking_id,
            'user_id_for_payment': user_id,
            'payment_amount': amount,
            'method': payment_method,
            'new_transaction_id': transaction_id
        }).execute()
        
        logger.info(f"Successfully confirmed booking {booking_id} via RPC.")
        return "Success"

    except APIError as e:
        logger.error(f"Error during RPC transaction for booking {booking_id}: {e.message}", exc_info=True)
        logger.warning("Transaction was rolled back.")
        return f"Error: {e.message}"
    except Exception as e:
        logger.critical(f"Unexpected error in RPC call for booking {booking_id}: {e}", exc_info=True)
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
    
    logger.info(f"Processing check-in for {email}, room type {room_type}")
    reservations = check_reservation(room_type=room_type, email=email, booking_status="pending")
    
    if isinstance(reservations, str):
        logger.warning(f"Check-in failed at 'check_reservation' step: {reservations}")
        return f"Find step failed: {reservations}"
    
    if not reservations:
        logger.warning(f"Check-in failed: No pending reservation found for {email}, {room_type}.")
        return "Error: No pending reservation found for today with those details."
    
    if len(reservations) > 1:
        logger.warning(f"Check-in failed: Found {len(reservations)} pending reservations for {email}. Requires manual intervention.")
        return "Error: Found multiple pending reservations. Please contact staff."

    booking_to_confirm = reservations[0]

    try:
        internal_booking_id = booking_to_confirm['booking_id']
        internal_user_id = booking_to_confirm['users']['user_id']
        price_to_charge = booking_to_confirm['total_price']
    except (KeyError, TypeError) as e:
        logger.error(f"Check-in failed: Found booking, but it's missing key data. Booking: {booking_to_confirm}", exc_info=True)
        return "Error: Found booking, but data was incomplete."

    logger.debug(f"Found booking {internal_booking_id}. Ready to charge ${price_to_charge} to user {internal_user_id}.")
    
    # --- STEP 4: ACT ---
    logger.debug(f"Processing payment for booking {internal_booking_id}...")
    confirmation_result = confirm_payment(
        booking_id=internal_booking_id,
        user_id=internal_user_id,
        amount=price_to_charge,
        payment_method=payment_method,
        transaction_id=transaction_id
    )
    
    if "Success" in confirmation_result:
        logger.info(f"Check-in complete for booking {internal_booking_id}")
    else:
        logger.error(f"Check-in failed at 'confirm_payment' step for booking {internal_booking_id}: {confirmation_result}")
        
    return confirmation_result


def cancel_pending_booking(booking_id: int):
    """
    Deletes a booking record IF its status is 'pending'.
    """
    logger.debug(f"Attempting to cancel pending booking {booking_id}")
    try:
        response = (
            supabase.table("bookings")
            .delete()
            .eq("booking_id", booking_id)
            .eq("booking_status", "pending")
            .execute()
        )
        
        if response.data:
            logger.info(f"Successfully canceled pending booking {booking_id}.")
            return "Success"
        else:
            # This is not an error, just a fact. Could be a 'confirmed' booking or a wrong ID.
            logger.warning(f"Could not cancel booking {booking_id}: No 'pending' booking found with that ID.")
            return "Error: Booking not found or was not pending."

    except APIError as e:
        logger.error(f"Database error on cancel_pending_booking {booking_id}: {e.message}", exc_info=True)
        return f"Error: {e.message}"
    except Exception as e:
        logger.critical(f"An unexpected error on cancel_pending_booking {booking_id}: {e}", exc_info=True)
        return "Error: An unexpected error occurred."
    

def delete_room(room_id: int):
    """
    Deletes a room, protected by 'ON DELETE RESTRICT' from bookings.
    """
    logger.debug(f"Attempting to delete room {room_id}")
    try:
        response = (
            supabase.table("rooms")
            .delete()
            .eq("room_id", room_id)
            .execute()
        )
        
        if response.data:
            logger.info(f"Successfully deleted room {room_id}.")
            return "Success"
        else:
            logger.warning(f"Could not delete room {room_id}: Not found.")
            return "Error: Room not found."

    except APIError as e:
        if "violates foreign key constraint" in e.message and "on table \"bookings\"" in e.message:
            logger.warning(f"Error: Cannot delete room {room_id} because it has existing bookings.")
            logger.debug("This is the 'ON DELETE RESTRICT' safeguard working correctly.")
            return "Error: Room has existing bookings."
        else:
            logger.error(f"Database error on delete_room {room_id}: {e.message}", exc_info=True)
            return f"Error: {e.message}"
    except Exception as e:
        logger.critical(f"An unexpected error on delete_room {room_id}: {e}", exc_info=True)
        return "Error: An unexpected error occurred."
    
def delete_user(user_id: int):
    """
    Deletes a user.
    Related records will be anonymized (ON DELETE SET NULL).
    """
    logger.debug(f"Attempting to delete user {user_id}")
    try:
        response = (
            supabase.table("users")
            .delete()
            .eq("user_id", user_id)
            .execute()
        )
        
        if response.data:
            logger.info(f"Successfully deleted user {user_id}.")
            logger.debug(f"Related historical records for user {user_id} have been anonymized (user_id set to NULL).")
            return "Success"
        else:
            logger.warning(f"Could not delete user {user_id}: Not found.")
            return "Error: User not found."

    except APIError as e:
        logger.error(f"Database error on delete_user {user_id}: {e.message}", exc_info=True)
        return f"Error: {e.message}"
    except Exception as e:
        logger.critical(f"An unexpected error on delete_user {user_id}: {e}", exc_info=True)
        return "Error: An unexpected error occurred."
    
def get_user_for_login(email: str):
    """
    Fetches the minimal user data needed for login verification.
    """
    logger.debug(f"Fetching user for login attempt: {email}")
    try:
        response = (
            supabase.table("users")
            .select("user_id, password") # Only select what's needed
            .eq("email", email)
            .limit(1)
            .execute()
        )
        if response.data:
            logger.debug(f"Found user {response.data[0]['user_id']} for login attempt.")
            return response.data[0] # Returns {'user_id': 1, 'password': '...'}
        else:
            logger.warning(f"Login failed: No user found with email: {email}")
            return None
    except APIError as e:
        logger.error(f"Error fetching user for login {email}: {e.message}", exc_info=True)
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a stored bcrypt hash.
    """
    logger.debug("Verifying password hash...")
    try:
        is_valid = bcrypt.checkpw(
            plain_password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
        logger.debug(f"Password verification result: {is_valid}")
        return is_valid
    except Exception as e:
        logger.error(f"Error verifying password: {e}", exc_info=True)
        return False