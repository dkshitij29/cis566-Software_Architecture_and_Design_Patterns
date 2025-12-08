// guest_dashboard.js

// Ensure this runs after config.js so API_BASE_URL is defined
// If you didn't create config.js, uncomment the line below:
// const API_BASE_URL = "http://127.0.0.1:8000";

document.addEventListener('DOMContentLoaded', async () => {
    
    // --- 1. AUTHENTICATION CHECK ---
    const token = localStorage.getItem("accessToken");
    const userEmail = localStorage.getItem("userEmail");

    if (!token) {
        alert("You are not logged in.");
        window.location.href = "guest_login_page.html";
        return;
    }


    const emailDisplay = document.querySelector(".email");
    const nameDisplay = document.querySelector(".user-name");
    if (emailDisplay) emailDisplay.textContent = userEmail || "Guest";
    if (nameDisplay) nameDisplay.textContent = "Welcome Back";

    // --- 2. SIDEBAR NAVIGATION ---
    const pages = document.querySelectorAll('.page');
    const sidebarLinks = document.querySelectorAll('.sidebar-link ul li a');

    function showPage(pageId) {
        pages.forEach(p => p.classList.remove('active'));
        const target = document.getElementById(pageId);
        if (target) target.classList.add('active');
    }

    sidebarLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            // Remove active class from all links
            sidebarLinks.forEach(l => l.classList.remove("active"));
            // Add active class to clicked link
            link.classList.add("active");

            const text = link.innerText.trim();

            if (text === "Dashboard") {
                showPage("main-container");
                fetchMyBookings(); // Refresh data when tab is opened
            }
            if (text === "Book a Room") showPage("book-a-room");
            if (text === "Settings") showPage("settings");
        });
    });

    const defaultLink = Array.from(sidebarLinks).find(link => link.innerText.trim() === "Dashboard");
    if (defaultLink) {
        defaultLink.classList.add("active");
        showPage("main-container");
    fetchMyBookings();
}

    // Logout Button Logic (Sidebar bottom)
    const logoutBtn = document.getElementById("guest-logout-btn"); // Change selector to ID
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            localStorage.clear();
            
            window.location.href = "index.html";
        });
    }


    // --- 3. DASHBOARD: VIEW BOOKINGS & SEARCH ---
    const myList = document.getElementById('myList');
    const historyBtn = document.getElementById("toggle"); // Kept from old code
    const cardTitle = document.getElementById("view-title"); // Kept from old code
    const searchInput = document.getElementById('searchInput'); // Added
    const filterSelect = document.getElementById('filterSelect'); // Added
    
    // A. FETCH DATA FROM ENDPOINT
    async function fetchMyBookings() {
        try {
            // Endpoint defined in main.py: /bookings/my-upcoming
            const response = await fetch(`${API_BASE_URL}/bookings/my-upcoming`, {
                method: "GET",
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "Content-Type": "application/json"
                }
            });

            if (response.ok) {
                const bookings = await response.json();
                populateList(bookings);
            } else {
                console.error("Failed to fetch bookings");
                if (response.status === 401) {
                    alert("Session expired");
                    window.location.href = "guest_login_page.html";
                }
            }
        } catch (error) {
            console.error("Error fetching data:", error);
        }
    }

    // B. RENDER LIST
    function populateList(bookings) {
        myList.innerHTML = ""; // Clear current list

        if (bookings.length === 0) {
            myList.innerHTML = "<p style='padding:20px'>No upcoming bookings found.</p>";
            return;
        }

        bookings.forEach(b => {
            const listItem = document.createElement('li');
            
            // We set data attributes (classes) for easier searching later
            listItem.innerHTML = `
            <div class="icon">
                <i class='bx bx-bed'></i> 
            </div>
            <div style="width: 100%;">
                <div class="headers">
                    <p class="booking-number">Booking #${b.booking_id}</p>
                    <h3 class="cell-sub">Room Type</h3>
                    <h3 class="cell-sub">Total Price</h3>
                    <h3 class="cell-sub">Dates</h3>
                </div>
                <div class="cell-info">
                    <div class="cell">
                        <h3 class="room-type">${b.rooms.room_type.toUpperCase()}</h3>
                        <p class="booked-date">Room ${b.rooms.room_number}</p>
                    </div>
                    <div class="cell">
                        <p class="sleeping-occu-data">$${b.total_price}</p>
                    </div>
                    <div class="cell">
                         <p class="beds-info">Standard</p>
                    </div>
                    <div class="cell">
                        <p class="stay-dates">${b.check_in_date} to ${b.check_out_date}</p>
                    </div>
                     <button onclick="cancelBooking(${b.booking_id})" style="background:red; color:white; border:none; padding:5px; cursor:pointer; margin-left:10px;">Cancel</button>
                </div>
            </div>
            `;
            myList.appendChild(listItem);
        });
    }

    // C. CLIENT-SIDE SEARCH & FILTER LOGIC
    function filterBookings() {
        const searchText = searchInput.value.toLowerCase();
        const filterBy = filterSelect.value || "All";
        const items = myList.querySelectorAll('li');

        items.forEach(li => {
            let targetText = '';

            // Map the dropdown values to the HTML classes
            if (filterBy === 'Booking No.') {
                targetText = li.querySelector('.booking-number')?.textContent || '';
            } else if (filterBy === 'Room Desc') {
                targetText = li.querySelector('.room-type')?.textContent || '';
            } else if (filterBy === 'Check In Date') {
                const dateText = li.querySelector('.stay-dates')?.textContent || '';
                targetText = dateText.split('to')[0].trim(); 
            } else if (filterBy === 'Check Out Date') {
                const dateText = li.querySelector('.stay-dates')?.textContent || '';
                targetText = dateText.split('to')[1] ? dateText.split('to')[1].trim() : '';
            } else { 
                // "All" - searches everything
                targetText = li.textContent;
            }

            if (targetText.toLowerCase().includes(searchText)) {
                li.style.display = '';
            } else {
                li.style.display = 'none';
            }
        });
    }

    // D. HISTORY TOGGLE LOGIC (Kept from old code)
    let showingCurrent = true;
    if (historyBtn) {
        historyBtn.addEventListener("click", () => {
            if (showingCurrent) {
                cardTitle.textContent = "BOOKING HISTORY";
                historyBtn.textContent = "View UPCOMING/CURRENT STAYS";
                myList.innerHTML = "<p style='padding:20px'>Past booking history is not yet available from the server.</p>";
            } else {
                cardTitle.textContent = "UPCOMING/CURRENT STAYS";
                historyBtn.textContent = "View BOOKING HISTORY";
                fetchMyBookings();
            }
            showingCurrent = !showingCurrent;
        });
    }

    // Attach Event Listeners
    if(searchInput) searchInput.addEventListener('input', filterBookings);
    if(filterSelect) filterSelect.addEventListener('change', filterBookings);

    // Initial Load
    fetchMyBookings();

    // --- 4. BOOK A ROOM: SEARCH & RESERVE ---
    const searchForm = document.getElementById('room-search-form');
    const resultsList = document.getElementById('available-rooms-list');

    if (searchForm) {
        searchForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const roomType = document.getElementById('search-room-type').value;
            const checkIn = document.getElementById('search-check-in').value;
            const checkOut = document.getElementById('search-check-out').value;

            // Basic Validation
            if (!roomType || !checkIn || !checkOut) {
                alert("Please fill in all fields");
                return;
            }

            // Call endpoint: /rooms/available
            const url = `${API_BASE_URL}/rooms/available?room_type=${roomType}&check_in=${checkIn}&check_out=${checkOut}`;

            try {
                const response = await fetch(url);
                
                if (!response.ok) {
                    const errText = await response.json();
                    throw new Error(errText.detail || "Search failed");
                }
                
                const rooms = await response.json();
                displaySearchResults(rooms, checkIn, checkOut);

            } catch (err) {
                alert("Error: " + err.message);
            }
        });
    }

    function displaySearchResults(rooms, checkIn, checkOut) {
        if (!resultsList) return;
        resultsList.innerHTML = ""; 

        if (rooms.length === 0) {
            resultsList.innerHTML = "<p style='padding:10px'>No rooms available for these dates.</p>";
            return;
        }

        rooms.forEach(room => {
            const li = document.createElement('li');
            // Adding inline styles for quick formatting - ideally move to CSS
            li.style.display = "flex";
            li.style.justifyContent = "space-between";
            li.style.alignItems = "center";
            li.style.padding = "15px";
            li.style.borderBottom = "1px solid #ddd";
            li.style.background = "#fff";
            
            li.innerHTML = `
                <div>
                    <h3 style="margin:0; font-size:16px;">${room.room_type.toUpperCase()} (Room ${room.room_number})</h3>
                    <p style="margin:0; color:#666;">$${room.price_per_night} / night</p>
                </div>
                <div>
                    <button onclick="bookRoom(${room.room_id}, '${checkIn}', '${checkOut}')" 
                    style="background:#007bff; color:white; border:none; padding:10px 20px; border-radius:4px; cursor:pointer;">
                        BOOK NOW
                    </button>
                </div>
            `;
            resultsList.appendChild(li);
        });
    }


    // --- 5. SETTINGS: UPDATE PROFILE ---
    const settingsForm = document.getElementById('update-profile-form');
    const deleteBtn = document.getElementById('delete-account-btn');

    if (settingsForm) {
        settingsForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            // Prepare Body based on UserCreate/UserUpdate model
            const body = {
                firstname: document.getElementById('update-firstname').value,
                lastname: document.getElementById('update-lastname').value,
                email: document.getElementById('update-email').value,
                phone_number: document.getElementById('update-phone').value,
                // These fields are required by UserCreate schema validation in logic.py
                // even if we are only updating specific fields in the DB query.
                username: document.getElementById('update-email').value, 
                password: "placeholder_password" 
            };

            try {
                const response = await fetch(`${API_BASE_URL}/users/me`, {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${token}`
                    },
                    body: JSON.stringify(body)
                });

                if (response.ok) {
                    alert("Profile Updated Successfully");
                    // Update the local storage email if it changed
                    localStorage.setItem("userEmail", body.email);
                } else {
                    const err = await response.json();
                    alert("Update failed: " + err.detail);
                }
            } catch (err) {
                console.error(err);
                alert("Connection Error");
            }
        });
    }

    if (deleteBtn) {
        deleteBtn.addEventListener('click', async () => {
            if(confirm("Are you sure you want to delete your account? This cannot be undone.")) {
                try {
                    const response = await fetch(`${API_BASE_URL}/users/me`, {
                        method: "DELETE",
                        headers: { "Authorization": `Bearer ${token}` }
                    });

                    if (response.ok) {
                        alert("Account Deleted");
                        localStorage.clear();
                        window.location.href = "guest_login_page.html";
                    } else {
                        alert("Failed to delete account");
                    }
                } catch (err) {
                    console.error(err);
                }
            }
        });
    }

});

// --- GLOBAL FUNCTIONS (Must be outside DOMContentLoaded to be accessible by onclick="") ---

// Function to handle the actual booking request
//
async function bookRoom(roomId, checkIn, checkOut) {
    const token = localStorage.getItem("accessToken");
    if (!token) return window.location.href = "guest_login_page.html";

    const body = {
        room_id: roomId,
        check_in_str: checkIn,
        check_out_str: checkOut
    };

    try {
        const response = await fetch(`${API_BASE_URL}/bookings/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify(body)
        });

        if (response.ok) {
            alert("Booking Successful! Check your Dashboard.");
            window.location.reload(); // Reload to update dashboard
        } else {
            const err = await response.json();
            alert("Booking Failed: " + err.detail);
        }
    } catch (error) {
        console.error("Booking Error:", error);
        alert("An error occurred while booking.");
    }
}

// Function to cancel a booking
//
async function cancelBooking(bookingId) {
    const token = localStorage.getItem("accessToken");
    if(!confirm("Cancel this booking?")) return;

    try {
        const response = await fetch(`${API_BASE_URL}/bookings/${bookingId}/cancel`, {
            method: "DELETE",
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        if (response.ok) {
            alert("Booking Cancelled");
            window.location.reload();
        } else {
            const err = await response.json();
            alert("Could not cancel: " + err.detail);
        }
    } catch (error) {
        console.error(error);
    }
}