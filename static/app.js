// =============================
// OPEN CAMERA IN NEW TAB
// =============================
document.getElementById("objectBtn")?.addEventListener("click", () => {
  window.open("camera.html", "_blank"); // opens laptop camera in new tab
});

// =============================
// CORE DOM ELEMENTS
// =============================
const chatArea    = document.getElementById("chatArea");
const userInput   = document.getElementById("userInput");
const sendBtn     = document.getElementById("sendBtn");
const micBtn      = document.getElementById("micBtn");
const locationBtn = document.getElementById("locationBtn");

// =============================
// POPULAR SITES MAP
// =============================
const popularSites = {
  youtube: "https://www.youtube.com",
  google: "https://www.google.com",
  gmail: "https://mail.google.com",
  facebook: "https://www.facebook.com",
  twitter: "https://www.twitter.com",
  whatsapp: "https://web.whatsapp.com",
  insta: "https://www.instagram.com",
  instagram: "https://www.instagram.com"
};

function normalizeTarget(t) {
  return (t || "")
    .trim()
    .toLowerCase()
    .replace(/[.,!?;:]+$/g, "");
}

// =============================
// SPEAK FUNCTION
// =============================
function speak(text, lang = "en-US") {
  if (!text || !window.speechSynthesis) return;
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang;
  window.speechSynthesis.speak(utterance);
}

// =============================
// ADD CHAT MESSAGE
// =============================
function addMessage(text, type = "bot") {
  if (!text) return;
  const bubble = document.createElement("div");
  bubble.className = type === "user" ? "bubble user" : "bubble bot";
  bubble.innerHTML = marked.parse(text);
  chatArea.appendChild(bubble);
  chatArea.scrollTo({ top: chatArea.scrollHeight, behavior: "smooth" });
}

// =============================
// ASK JARVIS (AI + Apps + Websites)
// =============================
async function askJarvis(message) {
  addMessage(message, "user");
  userInput.value = "";
  const lower = normalizeTarget(message);

  // --- Open popular websites directly ---
  if (lower.startsWith("open ")) {
    const target = normalizeTarget(message.slice(5));
    const url = popularSites[target];
    if (url) {
      const newWin = window.open(url, "_blank");
      if (newWin) {
        const say = `Opening ${target}`;
        addMessage(`🌐 ${say}`, "bot");
        speak(say);
      } else {
        addMessage("❌ Popup blocked! Allow popups to open this site.", "bot");
      }
      return;
    }
  }

  // --- Call backend for AI replies ---
  try {
    const res = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    });
    const data = await res.json();
    const reply = data.reply || "⚠️ Empty reply.";
    addMessage(reply, "bot");
    if (lower === "read") speak(reply);
  } catch (err) {
    addMessage("❌ Error connecting to server.", "bot");
  }
}

// =============================
// EVENTS
// =============================
sendBtn?.addEventListener("click", () => {
  const text = userInput.value.trim();
  if (text) askJarvis(text);
});

userInput?.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    sendBtn.click();
  }
});

// 🎤 VOICE INPUT
micBtn?.addEventListener("click", () => {
  const Rec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Rec) {
    addMessage("❌ Speech recognition not supported in this browser.", "bot");
    return;
  }
  const recognition = new Rec();
  recognition.lang = "en-US";
  recognition.start();
  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    askJarvis(transcript);
  };
  recognition.onerror = (e) => {
    addMessage("❌ Voice input error: " + e.error, "bot");
  };
});

// 📍 LOCATION → Show on Google Maps
locationBtn?.addEventListener("click", () => {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        const mapsUrl = `https://www.google.com/maps?q=${lat},${lon}`;
        window.open(mapsUrl, "_blank");
      },
      (error) => {
        addMessage("❌ Unable to fetch location: " + error.message, "bot");
      }
    );
  } else {
    addMessage("❌ Geolocation not supported in this browser.", "bot");
  }
});

// =============================
// GREETING ON LOAD
// =============================
const greetingText = (() => {
  const hour = new Date().getHours();
  if (hour < 12) return "🌅 Good Morning!";
  if (hour < 17) return "☀️ Good Afternoon!";
  if (hour < 21) return "🌇 Good Evening!";
  return "🌙 Good Night!";
})();
addMessage(greetingText, "bot");
speak(greetingText);
