import logic  # Your logic.py file
import os
from datetime import datetime, timedelta
from typing import List, Optional
from datetime import datetime, date, time, timedelta, timezone
from fastapi import FastAPI, Body, Depends, HTTPException, status, APIRouter, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, ConfigDict
from jose import JWTError, jwt
from fastapi.middleware.cors import CORSMiddleware

print(logic.supabase)

app = FastAPI(title="Hotel Reservation API")

origins = [
    "http://localhost",
    "http://localhost:3000", 
    "http://localhost:5173", 
    "http://localhost:8080", 
    "http://localhost:5000",
    "https://hotel-app-v1.onrender.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --- END BLOCK ---

SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")


class UserCreate(BaseModel):
    firstname: str
    lastname: str
    username: str
    email: EmailStr
    phone_number: str
    password: str

class UserResponse(BaseModel):
    firstname: str
    lastname: str
    username: str
    email: str
    phone_number: str
    class Config:
        orm_mode = True

class RoomCreate(BaseModel):
    room_number: str
    room_type: str
    price_per_night: float

class RoomResponse(BaseModel):
    room_id: int
    room_number: str
    room_type: str
    price_per_night: float
    class Config:
        orm_mode = True

class BookingCreate(BaseModel):
    user_id: int
    room_id: int
    check_in_str: str
    check_out_str: str

class CheckInRequest(BaseModel):
    email: EmailStr
    room_type: str
    payment_method: str
    transaction_id: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[int] = None

class BookingCreate(BaseModel):
    room_id: int
    check_in_str: str  # "YYYY-MM-DD"
    check_out_str: str # "YYYY-MM-DD"

class BookingResponse(BaseModel):
    booking_id: int
    user_id: int
    room_id: int
    booking_status: str
    total_price: float
    class Config:
        orm_mode = True

# --- Security & Authentication Functions ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Dependency to get the current user from a token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError:
        raise credentials_exception
    
    return token_data.user_id


# --- API Routers (Organizing Endpoints) ---

users_router = APIRouter(
    prefix="/users",
    tags=["Users & Authentication"]
)

rooms_router = APIRouter(
    prefix="/rooms",
    tags=["Rooms & Availability"]
)

bookings_router = APIRouter(
    prefix="/bookings",
    tags=["Bookings & Check-In"]
)

# --- User & Auth Endpoints ---

@users_router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(user: UserCreate):
    """
    Create a new user.
    """
    result = logic.create_newuser(
        user.firstname, user.lastname, user.username, 
        user.email, user.phone_number, user.password
    )
    
    if "Error:" in str(result):
        if "already exists" in result:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result)

    return result.data[0]

@users_router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Log a user in by verifying their email and password.
    Returns a JWT access token.
    """
    user = logic.get_user_for_login(form_data.username) # Using email as username
    
    if not user or not logic.verify_password(form_data.password, user['password']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"user_id": user['user_id']}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@users_router.put("/me", response_model=UserResponse)
def update_own_profile(
    updates: UserCreate, # Re-use UserCreate, or make a new UserUpdate model
    current_user_id: int = Depends(get_current_user)
):
    """
    Update the *currently logged in* user's profile.
    """
    result = logic.update_user_profile(
        user_id=current_user_id,
        firstname=updates.firstname,
        lastname=updates.lastname,
        email=updates.email,
        phone_number=updates.phone_number
    )
    if "Error:" in str(result):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result)
    return result.data[0]

@users_router.post("/forgot-password")
def forgot_password(request: PasswordResetRequest):
    """
    Starts the password reset process by sending an email.
    """
    result = logic.request_password_reset(request.email)
    if "Error:" in str(result):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result)
    return {"message": result} # Returns the generic success message

@users_router.post("/reset-password")
def reset_password(request: PasswordResetConfirm):
    """
    Completes the password reset process using the token.
    """
    result = logic.verify_and_reset_password(request.token, request.new_password)
    if "Error:" in str(result):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result)
    return {"message": result}


@users_router.delete("/me", status_code=status.HTTP_200_OK)
def delete_my_account(current_user_id: int = Depends(get_current_user)):
    """
    Deletes the currently logged-in user's account. (Requires authentication)
    Related records (bookings) are handled by database policies (SET NULL).
    """
    result = logic.delete_user(current_user_id)

    if "Error:" in result:
        if "not found" in result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result)

    return {"message": "Success: Your account and associated data have been deleted."}

# --- Room Endpoints ---

@rooms_router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_new_room(room: RoomCreate, current_user_id: int = Depends(get_current_user)):
    """
    Create a new room. (Protected - requires login).
    """
    
    result = logic.create_room(room.room_number, room.room_type, room.price_per_night)
    
    if "Error:" in str(result):
        if "already exists" in result:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result)
    
    return result.data[0]

@rooms_router.get("/available", response_model=List[RoomResponse])
def get_available_rooms(room_type: str, check_in: str, check_out: str):
    """
    Finds available rooms for a given date range and type.
    Example: /rooms/available?room_type=suite&check_in=2025-11-20&check_out=2025-11-25
    """
    result = logic.find_available_rooms_for_dates(room_type, check_in, check_out)
    
    if "Error:" in str(result):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result)
    
    return result 

@rooms_router.delete("/{room_id}", status_code=status.HTTP_200_OK)
def delete_room_endpoint(room_id: int, current_user_id: int = Depends(get_current_user)):
    """
    Deletes a room by ID. (Protected - requires login/Admin access)
    Fails if the room has existing bookings (ON DELETE RESTRICT).
    """    
    result = logic.delete_room(room_id)

    if "Error:" in result:
        if "Room has existing bookings" in result:

            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result) 
        if "not found" in result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result)

    return {"message": "Success: Room deleted."}

# --- Bookings Endpoints ---


@bookings_router.get("/my-upcoming", status_code=status.HTTP_200_OK)
def get_my_upcoming_bookings(current_user_id: int = Depends(get_current_user)):
    """
    Fetches all confirmed bookings for the logged-in user that are for today or in the future.
    """

    user_email = logic.get_user_email_by_id(current_user_id)
    if not user_email:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Error: User not found or email could not be retrieved.")


    result = logic.get_user_upcoming_bookings_by_email(user_email)
    
    if "Error:" in str(result):

        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result)


    return result


@bookings_router.delete("/{booking_id}/cancel", status_code=status.HTTP_200_OK)
def cancel_booking_endpoint(booking_id: int, current_user_id: int = Depends(get_current_user)):
    """
    Cancels a booking if its status is 'pending'. (Requires authentication)
    """
    
    result = logic.cancel_pending_booking(booking_id)

    if "Error:" in result:
        if "Booking not found or was not pending" in result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result)

    return {"message": "Success: Pending booking has been canceled."}

@bookings_router.post("/check-in", status_code=status.HTTP_200_OK)
def process_check_in(request: CheckInRequest):
    """
    The main business workflow:
    Finds a pending booking, logs payment, and confirms the booking.
    """
    result = logic.process_check_in_payment(
        request.email, request.room_type, 
        request.payment_method, request.transaction_id
    )
    
    if "Error:" in str(result):
        if "No pending reservation" in result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result)
        
    return {"message": result}

# --- Main App Setup ---


@app.get("/")
async def root():
    return {"message": "Hotel Reservation API is working. Visit /docs for documentation."}

@bookings_router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking_endpoint(
    booking: BookingCreate, 
    current_user_id: int = Depends(get_current_user)
):
    """
    Create a new 'pending' booking for the currently logged-in user.
    """
    result = logic.create_booking(
        user_id=current_user_id,
        room_id=booking.room_id,
        check_in_str=booking.check_in_str,
        check_out_str=booking.check_out_str
    )
    
    if "Error:" in str(result):
        if "not found" in result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result)
        if "already booked" in result:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result)

    return result.data[0]

app.include_router(users_router)
app.include_router(rooms_router)
app.include_router(bookings_router)

