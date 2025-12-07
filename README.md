# CIS 566: Hotel Reservation System API

A robust, RESTful API designed for a Hotel Management System. This project demonstrates **Layered Architecture**, **Role-Based Access Control (RBAC)**, and secure integration with a cloud database.

## 📂 Repository Structure

```text
├── backend/                # Application Source Code
│   ├── logic.py            # Business Logic & Data Access Layer (DAL)
│   ├── main.py             # Presentation Layer (FastAPI Controllers)
│   ├── render.yaml         # Cloud Deployment Configuration
│   ├── requirements.txt    # Python Dependencies
│   └── test_*.py           # Unit & Integration Tests
├── database/               # Database Configuration
│   ├── db.config           # Schema definitions
│   └── data.config         # Seeding data
└── README.md
```

## Software Architecture

This project follows a strict **Layered Architecture** to ensure Separation of Concerns (SoC):

1.  **Presentation Layer (`main.py`):** Handles HTTP requests, input validation (Pydantic models), and routing. It depends entirely on the Logic layer and knows nothing about the database.
2.  **Business Logic Layer (`logic.py`):** Contains the core domain rules (e.g., date validation, price calculation, conflict detection). acts as a **Facade** for the database interactions.
3.  **Data Persistence Layer (Supabase/PostgreSQL):** Handles data storage, atomic transactions, and stored procedures (RPCs).

### Design Patterns Implemented

  * **Singleton:** The Supabase client in `logic.py` is instantiated once and reused throughout the application lifecycle.
  * **Facade:** `logic.py` provides a simplified interface for complex database queries and error handling, hiding the complexity of Supabase/SQL from the API routes.
  * **Dependency Injection:** utilized heavily in `main.py` (via `Depends()`) to inject authentication dependencies (`get_current_user`, `get_current_admin`) into route handlers.
  * **DTO (Data Transfer Object):** Pydantic models (`UserCreate`, `BookingResponse`) are used to transfer data between the client and the server, ensuring strict typing.

## Key Features

  * **Authentication & Security:**
      * OAuth2 with JWT (JSON Web Tokens).
      * Secure password hashing using `bcrypt`.
      * Password reset flow via email tokens.
  * **Role-Based Access Control:**
      * **Guests:** Can view rooms.
      * **Users:** Can book rooms, manage their profile, and view booking history.
      * **Admins:** Can add/delete rooms and process guest check-ins.
  * **Booking Engine:**
      * Prevents double-booking via date-range conflict detection.
      * Atomic transactions for payment processing and confirmation.
      * Supports cancellation logic for pending bookings.

## Getting Started

### Prerequisites

  * Python 3.9+
  * A Supabase account (for PostgreSQL)

### 1\. Clone the Repository

```bash
git clone https://github.com/dkshitij29/cis566-Software_Architecture_and_Design_Patterns.git
cd cis566-Software_Architecture_and_Design_Patterns
```

### 2\. Environment Setup

Navigate to the backend directory and set up a virtual environment:

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3\. Configuration (.env)

Create a `.env` file inside the `backend/` folder with the following credentials:

```ini
supabase_url="YOUR_SUPABASE_PROJECT_URL"
supabase_key="YOUR_SUPABASE_ANON_KEY"
SECRET_KEY="YOUR_GENERATED_SECRET_KEY"
```

### 4\. Database Setup

Ensure your Supabase instance has the necessary tables (`users`, `rooms`, `bookings`, `password_resets`) and the `process_payment_and_confirm` RPC function. Refer to `database/db.config` for the schema.

### 5\. Run the Application

```bash
fastapi dev main.py
# OR
uvicorn main:app --reload
```

The API will start at `http://127.0.0.1:8000`. Access the **Swagger UI** documentation at `http://127.0.0.1:8000/docs`.

## 🧪 Testing

The project includes integration and logic tests using `pytest`.

```bash
# Run all tests
cd backend
./test.sh
```

## API Endpoints Overview

| Method | Endpoint | Description | Access |
| :--- | :--- | :--- | :--- |
| **POST** | `/users/signup` | Register a new user | Public |
| **POST** | `/users/login` | Login and retrieve JWT | Public |
| **GET** | `/rooms/available` | Search rooms by date | Public |
| **POST** | `/bookings/` | Create a pending booking | User |
| **POST** | `/bookings/check-in` | Process payment & confirm | **Admin** |
| **POST** | `/rooms/` | Add a new room | **Admin** |
| **DELETE**| `/rooms/{id}` | Delete a room | **Admin** |

## Deployment

The application includes a `render.yaml` configuration for easy deployment on **Render.com**. It is configured to run as a Web Service with a Docker or Python environment.