const loginForm = document.getElementById("login-form");

loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("email-field").value;
    const password = document.getElementById("password-field").value;
    const formData = new URLSearchParams();
    formData.append("username", email); 
    formData.append("password", password);

    try {
        const response = await fetch(`${API_BASE_URL}/users/login`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: formData
        });
        const data = await response.json();

        if (response.ok) {
            localStorage.setItem("accessToken", data.access_token);
            // CRITICAL CHANGE: Redirect to Admin Dashboard
            window.location.href = "admin_dashboard.html"; 
        } else {
            alert("Login failed: " + data.detail);
        }
    } catch (error) {
        console.error("Error:", error);
    }
});