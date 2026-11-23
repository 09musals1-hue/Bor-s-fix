// 1. Register the Service Worker
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("./sw.js")
      .then(() => console.log("Service Worker registered"))
      .catch((err) => console.error("Service Worker error:", err));
  });
}

// 2. App Logic (Notes saved locally in the browser)
const form = document.getElementById("note-form");
const input = document.getElementById("note-input");
const list = document.getElementById("note-list");
const statusBadge = document.getElementById("status");

let notes = JSON.parse(localStorage.getItem("pwa-notes")) || [];

function saveAndRender() {
  localStorage.setItem("pwa-notes", JSON.stringify(notes));
  list.innerHTML = "";

  notes.forEach((note, index) => {
    const li = document.createElement("li");
    li.textContent = note;

    const delBtn = document.createElement("button");
    delBtn.textContent = "Delete";
    delBtn.onclick = () => {
      notes.splice(index, 1);
      saveAndRender();
    };

    li.appendChild(delBtn);
    list.appendChild(li);
  });
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  notes.push(text);
  input.value = "";
  saveAndRender();
});

// 3. Update Online/Offline indicator
function updateStatus() {
  if (navigator.onLine) {
    statusBadge.textContent = "Online";
    statusBadge.className = "badge online";
  } else {
    statusBadge.textContent = "Offline";
    statusBadge.className = "badge offline";
  }
}

window.addEventListener("online", updateStatus);
window.addEventListener("offline", updateStatus);

updateStatus();
saveAndRender();