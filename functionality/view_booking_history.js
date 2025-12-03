const historyBtn = document.querySelector(".view-all-stays-btn")
const cardTitle = document.getElementById("view-title")


document.addEventListener("DOMContentLoaded", () => {
    const historyBtn = document.querySelector(".view-all-stays-btn");
    const cardTitle = document.getElementById("view-title");

    const current = "UPCOMING/CURRENT STAYS";
    const all = "BOOKING HISTORY";

    historyBtn.addEventListener("click", () => {
        if (cardTitle.textContent === current) {
            cardTitle.textContent = all;
            historyBtn.textContent = "View " + current;
        } else {
            cardTitle.textContent = current;
            historyBtn.textContent = "View " + all;
        }
    });
});
