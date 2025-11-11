const loginForm = document.getElementById("login-form");
const loginButton = document.getElementById("login-form-submit");
const loginErrorMsg = document.getElementById("login-error-msg");
const loginFormField = document.getElementById("login-form-field");

const loginHolder = document.getElementById("login-holder");

const loginErrorMsgHolder = document.getElementById("login-error-msg-holder");

//Taking the loginButton and attaching an action to it, e
loginButton.addEventListener("click", (e) => {
    e.preventDefault();
    const username = loginForm.username.value;
    const password = loginForm.password.value;

    if (username == "user" && password == "web_dev") {
        alert("Success");
        location.reload()
    } else {
        loginHolder.style.marginTop = "15px"

        loginErrorMsgHolder.style.display = "grid"
        loginErrorMsg.style.opacity = "100"
    }
})