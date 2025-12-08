const signupForm = document.getElementById("login-info-form"); // ensure ID matches HTML

signupForm.addEventListener("submit", async (e) => {
    e.preventDefault(); // STOP the page from reloading

    // 1. Gather data
    const formData = {
        email: document.getElementById("email-field").value,
        password: document.getElementById("password-field").value,
        firstname: document.getElementById("firstname-field").value,
        lastname: document.getElementById("lastname-field").value,
        username: document.getElementById("email-field").value, // logic.py needs username, using email is fine
        phone_number: "000-000-0000" // You might need to add this field to your HTML or hardcode it for now
    };

    try {
        const response = await fetch(`${API_BASE_URL}/users/signup`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (response.ok) {
            alert("Account created! Please login.");
            window.location.href = "guest_login_page.html";
        } else {
            // Backend returned an error (e.g. 409 Conflict)
            alert("Error: " + data.detail); 
        }
    } catch (error) {
        console.error("Network error:", error);
        alert("Could not connect to server.");
    }
});