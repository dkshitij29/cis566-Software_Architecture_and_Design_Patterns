const password = document.getElementById("password-field");
const password_retype = document.getElementById("retype-password-field");

const check = document.getElementById("welcome-msg");

window.addEventListener("load", () => {
    password.setCustomValidity(
        "Password must have at least 8 characters, 1 uppercase, 1 lowercase, 1 number, and 1 special character."
        );
    password_retype.setCustomValidity("Passwords must match.")
});

function checkInputs() {
    if (password.validity.valueMissing) {
        // Required field message
        password.setCustomValidity("Password is required.");
    } 
    else if (password.validity.patternMismatch) {
        // Custom message instead of “Please match the requested format”
        password.setCustomValidity(
        "Password must have at least 8 characters, 1 uppercase, 1 lowercase, 1 number, and 1 special character."
        );
    } 
    else {
        // Clear message when valid
        password.setCustomValidity("");
    }

    if (password_retype.validity.valueMissing) {
        password_retype.setCustomValidity("Passwords must match.")
    }
    else if (password.value !== password_retype.value) {
        password_retype.setCustomValidity("Passwords must match!")
    }
    else {
        password_retype.setCustomValidity("");
    }
}

password_retype.addEventListener("input", checkInputs);
password.addEventListener("input", checkInputs);