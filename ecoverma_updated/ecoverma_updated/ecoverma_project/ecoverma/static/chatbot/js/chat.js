const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const chatMessages = document.getElementById("chatMessages");
const typingIndicator = document.getElementById("typingIndicator");


function getCSRFToken() {
    const cookie = document.cookie
        .split("; ")
        .find(row => row.startsWith("csrftoken="));
    if (!cookie) return "";
    return decodeURIComponent(cookie.split("=")[1]);
}

function escapeHTML(text) {
    const div = document.createElement("div");
    div.textContent = text == null ? "" : String(text);
    return div.innerHTML;
}

function nowStamp() {
    const d = new Date();
    return d.toLocaleDateString() + " · " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function scrollToBottom() {
    // Scroll now and again after layout (cards/images change the height).
    chatMessages.scrollTop = chatMessages.scrollHeight;
    requestAnimationFrame(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    });
}

function setTyping(show) {
    typingIndicator.style.display = show ? "flex" : "none";
    if (show) scrollToBottom();
}

function appendWrapper(html, className) {
    const wrapper = document.createElement("div");
    wrapper.className = className;
    wrapper.innerHTML = html;
    chatMessages.appendChild(wrapper);
    scrollToBottom();
    return wrapper;
}


function addUserMessage(message) {
    appendWrapper(`
        <div class="message-content">
            <div class="message-name">You</div>
            <div class="message-bubble">${escapeHTML(message)}</div>
            <div class="message-timestamp">${nowStamp()}</div>
        </div>
        <div class="message-avatar user-avatar">👤</div>
    `, "message user-message");
}


/* ---------- card builders for each response "action" ---------- */

function ecoBadge(status, label) {
    const cls = status === "certified" ? "eco-badge eco-certified"
        : status === "eco proxy" ? "eco-badge eco-proxy"
        : "eco-badge eco-unknown";
    return `<span class="${cls}">${escapeHTML(label)}</span>`;
}

function hotelCardsHTML(hotels) {
    if (!hotels || !hotels.length) {
        return `<p class="empty-note">No hotel listings found.</p>`;
    }
    return `<div class="card-grid">` + hotels.map(h => `
        <div class="mini-card hotel-card">
            <div class="mini-card-title">${escapeHTML(h.name)}</div>
            <div class="mini-card-row">
                ${h.stars ? `<span class="stars">${"★".repeat(parseInt(h.stars) || 0)}</span>` : `<span class="muted">Stars unknown</span>`}
            </div>
            ${ecoBadge(h.eco_status, h.eco_label)}
        </div>
    `).join("") + `</div>`;
}

function transportListHTML(stops, verdict) {
    const list = (stops || []).slice(0, 8).map(s =>
        `<li><span class="stop-type">${escapeHTML(s.type)}</span> ${escapeHTML(s.name)}</li>`
    ).join("");
    return `
        <div class="transport-block">
            <p class="verdict-line">Verdict: <strong>${escapeHTML(verdict)}</strong></p>
            ${list ? `<ul class="transport-list">${list}</ul>` : `<p class="empty-note">No nearby stops found in the data.</p>`}
        </div>
    `;
}

function attractionCardsHTML(attractions) {
    if (!attractions || !attractions.length) {
        return `<p class="empty-note">No listed museums or historic sites nearby.</p>`;
    }
    return `<div class="card-grid">` + attractions.map(a => `
        <div class="mini-card attraction-card">
            <div class="mini-card-title">${escapeHTML(a.name)}</div>
            <div class="mini-card-row muted">${escapeHTML(a.kind || "")}</div>
            ${a.summary ? `<p class="mini-card-text">${escapeHTML(a.summary)}</p>` : ""}
            ${a.url ? `<a href="${a.url}" target="_blank" rel="noopener" class="mini-card-link">Read more →</a>` : ""}
        </div>
    `).join("") + `</div>`;
}

function weatherCardHTML(weather) {
    if (!weather) return `<p class="empty-note">Weather unavailable right now.</p>`;
    const current = weather.current || {};
    const days = (weather.daily || []).map(d => `
        <div class="weather-day">
            <div class="weather-date">${escapeHTML(d.date)}</div>
            <div class="weather-temp">${d.temp_max}°C</div>
            <div class="weather-rain">${d.rain_mm} mm rain</div>
            <div class="weather-advice">${escapeHTML(d.advice)}</div>
        </div>
    `).join("");
    return `
        <div class="weather-block">
            <div class="weather-current">Now: <strong>${current.temperature}°C</strong>, wind ${current.wind_speed} km/h</div>
            <div class="weather-days">${days}</div>
        </div>
    `;
}

function itineraryHTML(itinerary) {
    if (!itinerary) return "";
    let html = `<div class="itinerary-block">`;

    if (itinerary.description) {
        html += `<p class="itinerary-description">${escapeHTML(itinerary.description.summary || "")}
            ${itinerary.description.url ? ` <a href="${itinerary.description.url}" target="_blank" rel="noopener">(Wikipedia)</a>` : ""}
        </p>`;
    }

    html += `<div class="itinerary-section"><h4>🌤️ Weather</h4>${weatherCardHTML(itinerary.weather)}</div>`;
    html += `<div class="itinerary-section"><h4>📍 Attractions</h4>${attractionCardsHTML(itinerary.attractions)}</div>`;
    html += `<div class="itinerary-section"><h4>🏨 Hotels</h4>${hotelCardsHTML(itinerary.hotels)}</div>`;
    html += `<div class="itinerary-section"><h4>🚆 Transport</h4>${transportListHTML(null, itinerary.transport_verdict)}</div>`;

    if (itinerary.budget_conversions && itinerary.budget_conversions.length) {
        html += `<div class="itinerary-section"><h4>💱 Your budget elsewhere</h4><ul class="fx-list">`;
        itinerary.budget_conversions.forEach(c => {
            html += `<li>${c.amount} ${c.currency}${c.rate_date ? ` <span class="muted">(ECB rate, ${c.rate_date})</span>` : ""}</li>`;
        });
        html += `</ul></div>`;
    }

    if (itinerary.eco_disclaimer) {
        html += `<p class="eco-disclaimer">ℹ️ ${escapeHTML(itinerary.eco_disclaimer)}</p>`;
    }

    html += `</div>`;
    return html;
}


/* ---------- carbon mini-form ---------- */

let carbonLegCounter = 0;

function carbonFormHTML(vehicleOptions) {
    carbonLegCounter = 0;
    const formId = "carbonForm-" + Date.now();
    const optionsHTML = Object.entries(vehicleOptions || {})
        .map(([value, label]) => `<option value="${value}">${escapeHTML(label)}</option>`)
        .join("");

    return `
        <div class="carbon-form" id="${formId}">
            <div class="carbon-legs">
                ${carbonLegRow(optionsHTML)}
            </div>
            <div class="carbon-form-actions">
                <button type="button" class="secondary-button" onclick="addCarbonLeg('${formId}', \`${optionsHTML.replace(/`/g, "\\`")}\`)">+ Add another leg</button>
                <button type="button" class="primary-button" onclick="submitCarbonForm('${formId}')">Calculate</button>
            </div>
        </div>
    `;
}

function carbonLegRow(optionsHTML) {
    carbonLegCounter += 1;
    return `
        <div class="carbon-leg-row">
            <select class="form-input carbon-vehicle">${optionsHTML}</select>
            <input type="number" min="0" step="0.1" class="form-input carbon-distance" placeholder="Distance (km)">
        </div>
    `;
}

function addCarbonLeg(formId, optionsHTML) {
    const container = document.querySelector(`#${formId} .carbon-legs`);
    if (!container) return;
    const div = document.createElement("div");
    div.innerHTML = carbonLegRow(optionsHTML);
    container.appendChild(div.firstElementChild);
    scrollToBottom();
}

async function submitCarbonForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return;

    const legs = Array.from(form.querySelectorAll(".carbon-leg-row")).map(row => ({
        vehicle_type: row.querySelector(".carbon-vehicle").value,
        distance_km: parseFloat(row.querySelector(".carbon-distance").value),
    })).filter(leg => leg.distance_km > 0);

    if (!legs.length) {
        alert("Add at least one leg with a distance greater than 0.");
        return;
    }

    form.querySelectorAll("button").forEach(b => b.disabled = true);
    setTyping(true);

    try {
        const response = await fetch("/chatbot/api/carbon/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCSRFToken(),
            },
            body: JSON.stringify({ legs }),
        });

        const data = await response.json();
        setTyping(false);

        if (!response.ok) {
            addBotMessage({ text: data.error || "Something went wrong with that calculation." });
            return;
        }

        addBotMessage(data);
    } catch (error) {
        console.error(error);
        setTyping(false);
        addBotMessage({ text: "I couldn't reach the carbon calculator just now. Please try again." });
    }
}


/* ---------- main bot message renderer ---------- */

function addBotMessage(data) {
    const message = data.text || "";
    const buttons = data.buttons || [];

    let extraHTML = "";
    switch (data.action) {
        case "hotel_results":
            extraHTML = hotelCardsHTML(data.hotels);
            break;
        case "transport_results":
            extraHTML = transportListHTML(data.stops, data.verdict);
            break;
        case "attraction_results":
            extraHTML = attractionCardsHTML(data.attractions);
            break;
        case "weather_results":
            extraHTML = weatherCardHTML(data.weather);
            break;
        case "trip_plan":
            extraHTML = itineraryHTML(data.itinerary);
            break;
        case "carbon_form":
            extraHTML = carbonFormHTML(data.vehicle_options);
            break;
        case "carbon_result":
            extraHTML = carbonResultHTML(data);
            break;
    }

    let linksHTML = "";
    if (data.links && data.links.length) {
        linksHTML = `<div class="message-links">` +
            data.links.map(l => `<a href="${l.url}" target="_blank" rel="noopener">${escapeHTML(l.label)}</a>`).join("") +
            `</div>`;
    }

    let buttonsHTML = "";
    if (buttons.length) {
        buttonsHTML = `<div class="response-buttons">` +
            buttons.map(b => `<button class="response-button" onclick="sendQuickMessage('${escapeHTML(b.title)}')">${escapeHTML(b.title)}</button>`).join("") +
            `</div>`;
    }

    appendWrapper(`
        <div class="message-avatar">🌿</div>
        <div class="message-content">
            <div class="message-name">EcoTravel AI</div>
            <div class="message-bubble">
                ${escapeHTML(message).replace(/\n/g, "<br>")}
                ${extraHTML}
                ${linksHTML}
                ${buttonsHTML}
            </div>
            <div class="message-timestamp">${nowStamp()}</div>
        </div>
    `, "message bot-message");
}

function carbonResultHTML(data) {
    const legs = data.legs || [];
    const maxKg = Math.max(...legs.map(l => l.emission_kg), 1);
    const rows = legs.map(l => `
        <div class="carbon-bar-row">
            <span class="carbon-bar-label">${escapeHTML(l.label)} (${l.distance_km} km)</span>
            <div class="carbon-bar-track">
                <div class="carbon-bar-fill" style="width:${Math.max(4, (l.emission_kg / maxKg) * 100)}%"></div>
            </div>
            <span class="carbon-bar-value">${l.emission_kg} kg</span>
        </div>
    `).join("");

    return `
        <div class="carbon-result">
            ${rows}
            <p class="carbon-total">Total: <strong>${data.total_kg} kg CO2e</strong> (${data.band}) · Best leg mode: ${escapeHTML(data.best_mode || "-")}</p>
            <p class="carbon-caveat">Figures are rounded, indicative averages - not exact measurements.</p>
        </div>
    `;
}


/* ---------- send / receive ---------- */

async function sendMessage(message) {
    if (!message || !message.trim()) return;
    message = message.trim();

    addUserMessage(message);
    messageInput.value = "";
    setTyping(true);

    try {
        const response = await fetch("/chatbot/api/chat/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCSRFToken(),
            },
            body: JSON.stringify({ message: message }),
        });

        if (!response.ok) throw new Error(`HTTP error ${response.status}`);

        const data = await response.json();
        setTyping(false);

        if (data.text !== undefined || data.action) {
            addBotMessage(data);
        } else {
            addBotMessage({ text: "Sorry, I couldn't process that request." });
        }
    } catch (error) {
        console.error(error);
        setTyping(false);
        addBotMessage({ text: "I'm having trouble connecting to the travel assistant. Please try again." });
    }
}

function sendQuickMessage(message) {
    sendMessage(message);
}

function clearChat() {
    chatMessages.innerHTML = `
        <div class="message bot-message">
            <div class="message-avatar">🌿</div>
            <div class="message-content">
                <div class="message-name">EcoTravel AI</div>
                <div class="message-bubble">
                    Chat view cleared. 🌿 (Your history is still saved — refresh to see it again.)
                    <br><br>
                    Where would you like to travel?
                </div>
            </div>
        </div>
    `;
    messageInput.focus();
}

function switchSidebarTab(tab) {
    document.querySelectorAll(".sidebar-tab").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.tab === tab);
    });
    document.querySelectorAll(".sidebar-panel").forEach(panel => {
        panel.classList.toggle("hidden", panel.dataset.panel !== tab);
    });
}

chatForm.addEventListener("submit", function (event) {
    event.preventDefault();
    sendMessage(messageInput.value);
});

messageInput.focus();
scrollToBottom();
