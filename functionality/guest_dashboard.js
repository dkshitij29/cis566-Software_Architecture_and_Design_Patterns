document.addEventListener('DOMContentLoaded', () => {
  const itemInput = document.getElementById('itemInput');
  const addItemBtn = document.getElementById('addItemBtn');
  const myList = document.getElementById('myList');
  const searchInput = document.getElementById('searchInput');
  const filterSelect = document.getElementById('filterSelect');

  // REMOVE AFTER INTEGRATION : This populated the view with three default bookings for testing
  const allBookings = [
    { bookingNo: "1001", roomType: "King Bed Deluxe", sleeps: "2", bedAmt: "1", bedType: "King", checkInDate: "2025-12-18", checkOutDate: "2024-12-22", bookedDate: "2024-11-01" },
    { bookingNo: "1002", roomType: "Double Suite w/ Balcony", sleeps: "4", bedAmt: "2", bedType: "Queen", checkInDate: "2025-11-15", checkOutDate: "2023-11-18", bookedDate: "2023-10-15" },
    { bookingNo: "1003", roomType: "Single Economy Room", sleeps: "1", bedAmt: "1", bedType: "Twin", checkInDate: "2025-12-21", checkOutDate: "2025-12-23", bookedDate: "2025-12-01" },
    { bookingNo: "1004", roomType: "King Suite", sleeps: "2", bedAmt: "1", bedType: "King", checkInDate: "2025-10-01", checkOutDate: "2025-10-03", bookedDate: "2025-09-01" }
  ];

  const cutoffDate = new Date("2025-12-20");
  const currentBookings = allBookings.filter(b => new Date(b.checkOutDate) >= cutoffDate);
  const pastBookings = allBookings.filter(b => new Date(b.checkOutDate) < cutoffDate);

  function populateList(bookings) {
    myList.innerHTML = ""; // clear current list
    bookings.forEach(b => createBookingItem(b));
  }
  // REMOVE ABOVE AFTER INTEGRATION 

  const historyBtn = document.getElementById("toggle");
  const cardTitle = document.getElementById("view-title");

  const currentTitle = "UPCOMING/CURRENT STAYS";
  const pastTitle = "BOOKING HISTORY";

  function showCurrentBookings() {
    cardTitle.textContent = currentTitle;
    historyBtn.textContent = "View " + pastTitle;
    populateList(currentBookings);
  }
  function showPastBookings() {
    cardTitle.textContent = pastTitle;
    historyBtn.textContent = "View " + currentTitle;
    populateList(pastBookings);
  }

  // Toggle button click
  let showingCurrent = true; // track which list is currently shown

  historyBtn.addEventListener("click", () => {
    if (showingCurrent) {
      searchInput.value = "";
      filterSelect.selectedIndex = 0;
      showPastBookings();
    } else {
      searchInput.value = "";
      filterSelect.selectedIndex = 0;
      showCurrentBookings();
    }
    showingCurrent = !showingCurrent; // flip state
  });

// Initial load
  cardTitle.textContent = currentTitle;
  historyBtn.textContent = "View " + pastTitle;
  populateList(currentBookings);
//END POPULATING LIST//

//CREATING A BOOKING ITEM : will change after integration 
  function createBookingItem(data) {
    const listItem = document.createElement('li');

    listItem.innerHTML = `
      <div class="icon">
        <i class='bxr  bx-desk'></i> 
      </div>
      <div>
        <div class="headers">
          <p class="booking-number" data-booking-no = "${data.bookingNo}">Booking No. ${data.bookingNo}</p>
          <h3 class="cell-sub" id="sleep-occu">Sleeps</h3>
          <h3 class="cell-sub" id="bed-type">Beds</h3>
          <h3 class="cell-sub" id="check-dates">In/Check Out</h3>
        </div>
        <div class="cell-info">
          <div class="cell" id = "cell-1">
            <h3 class="room-type">${data.roomType}</h3>
            <p class="booked-date">Booked ${data.bookedDate}</p>
          </div>
          <div class="cell" id = "cell-2">
            <p class="sleeping-occu-data">${data.sleeps}</p>
          </div>
          <div class="cell" id = "cell-3">
            <p class="beds-info">${data.bedAmt} ${data.bedType}</p>
          </div>
          <div class="cell" id = "cell-4">
            <p class="stay-dates">${data.checkInDate} - ${data.checkOutDate}</p>
          </div>
        </div>
      </div>
    `;
    myList.appendChild(listItem);
  }
//END CREATE A BOOKING

//SEARCH FUNCTIONALITY 
  function filterBookings() {
    const searchText = searchInput.value.toLowerCase();
    const filterBy = filterSelect.value || "All";

    const items = myList.querySelectorAll('li');

    items.forEach(li => {
      let targetText = '';

      if (filterBy === 'Booking No.') {
        const booking = li.querySelector('.booking-number');
        targetText = booking ? booking.dataset.bookingNo.toLowerCase() : '';
      } else if (filterBy === 'Room Desc') {
        const roomDesc = li.querySelector('.room-type');
        targetText = roomDesc ? roomDesc.textContent.toLowerCase() : '';
      } else if (filterBy === 'Check In Date') {
        const dateText = li.querySelector('.stay-dates')?.textContent || '';
        const checkIn = dateText.split('-')[0].trim().toLowerCase();
        targetText = checkIn;
      } else if (filterBy === 'Check Out Date') {
        const dateText = li.querySelector('.stay-dates')?.textContent || '';
        const checkOut = dateText.split('-')[1].trim().toLowerCase();
        targetText = checkOut;
      } else if (filterBy === 'Booking Date') {
        const bookingDate = li.querySelector('.booked-date');
        targetText = bookingDate ? bookingDate.textContent.toLowerCase() : '';
      } else if (filterBy === 'Occupancy') {
        const sleepingOccu = li.querySelector('.sleeping-occu-data');
        targetText = sleepingOccu ? sleepingOccu.textContent.toLowerCase() : '';
      } else if (filterBy === 'Bed Options') {
        const bedsInfo = li.querySelector('.beds-info');
        targetText = bedsInfo ? bedsInfo.textContent.toLowerCase() : '';
      } else { // "all"
        targetText = li.textContent.toLowerCase();
      }

      if (targetText.includes(searchText)) {
        li.style.display = '';
      } else {
        li.style.display = 'none';
      }
    });
  }
  
  searchInput.addEventListener('input', filterBookings);
  filterSelect.addEventListener('change', filterBookings);
//END SEARCH SELECTION

//SIDEBAR SELECTION
  const pages = document.querySelectorAll('.page');
  const sidebarLinks = document.querySelectorAll('.sidebar-link ul li a');

  function showPage(pageId) {
      pages.forEach(p => p.classList.remove('active'));
      document.getElementById(pageId).classList.add('active');
  }

  // On launch → open Dashboard
  showPage("main-container");
  // Automatically select the Dashboard link on page load
  const dashboardLink = Array.from(sidebarLinks).find(
      link => link.innerText.trim() === "Dashboard"
  );
  if (dashboardLink) {
      dashboardLink.classList.add("active");
  }

  // Sidebar click switching
  sidebarLinks.forEach(link => {
      link.addEventListener('click', () => {

          sidebarLinks.forEach(l => l.classList.remove("active"));
          link.classList.add("active");

          const text = link.innerText.trim();

          if (text === "Dashboard") showPage("main-container");
          if (text === "Book a Room") showPage("book-a-room");
          if (text === "Settings") showPage("settings");
      });
  });
//END SIDEBAR SELECTION


//ON CLICK LIST ITEM 
  
//
});
