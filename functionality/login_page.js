const signup_button = document.getElementById("signup-form-submit");

document.addEventListener("DOMContentLoaded", () => {
    signup_button.addEventListener("click", () => {
        const signup_html = signup_button.dataset.redirect;
        window.location.href = signup_html;
    })
})