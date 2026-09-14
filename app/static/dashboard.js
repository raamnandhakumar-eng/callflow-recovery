const body = document.body;
const tenantSlug = body.dataset.tenant || "northstar-hvac";

const scenarios = {
  appointment: {
    transcript: "I need to book an appointment for an AC diagnostic.",
    requestedTime: "Thursday at 2 PM",
    service: "AC diagnostic",
  },
  pricing: {
    transcript: "How much does a standard diagnostic visit cost?",
    requestedTime: "",
    service: "",
  },
  emergency: {
    transcript: "There is smoke coming from my furnace. This is an emergency.",
    requestedTime: "",
    service: "Emergency furnace inspection",
  },
  "knowledge-gap": {
    transcript: "Do you service geothermal heat pumps in landmark buildings?",
    requestedTime: "",
    service: "Geothermal heat pump service",
  },
};

function setScenario(name) {
  const preset = scenarios[name];
  if (!preset) return;
  document.querySelector("#transcriptInput").value = preset.transcript;
  document.querySelector("#requestedTimeInput").value = preset.requestedTime;
  document.querySelector("#serviceInput").value = preset.service;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderDemoResult(data) {
  const result = document.querySelector("#demoResult");
  const citations = Array.isArray(data.citations) && data.citations.length
    ? data.citations.map((item) => `<span>${escapeHtml(item.title || item.source)}</span>`).join("")
    : "<span>No citation required</span>";
  const demoAdapters = String(data.crm_contact_id || "").startsWith("demo-")
    || String(data.sms_message_id || "").startsWith("demo-");
  const integrationLabel = demoAdapters ? "Demo CRM/SMS adapters" : "Live downstream integrations";

  result.innerHTML = `
    <div class="demo-result-header">
      <div><span class="badge badge-${escapeHtml(data.status)}">${escapeHtml(data.status)}</span><strong>${escapeHtml(data.intent.replaceAll("_", " "))}</strong></div>
      <small>${escapeHtml(data.latency_ms)} ms · $${Number(data.cost_usd || 0).toFixed(5)}</small>
    </div>
    <p>${escapeHtml(data.answer || "Workflow completed without a customer-facing answer.")}</p>
    <div class="demo-result-meta">
      <span>Confidence ${Math.round(Number(data.confidence || 0) * 100)}%</span>
      <span>${data.appointment_id ? `Appointment #${escapeHtml(data.appointment_id)}` : "No appointment"}</span>
      <span>${data.escalated ? "Human escalation" : "Automated outcome"}</span>
      <span>${escapeHtml(integrationLabel)}</span>
    </div>
    <div class="citation-chips">${citations}</div>
    <p class="reload-note">Outcome persisted. Refresh the dashboard when you want to update metrics and inspect the trace table.</p>
    <button class="button button-dark button-small" type="button" id="refreshAfterDemo">Refresh and inspect trace</button>
  `;
  result.classList.remove("hidden");
  document.querySelector("#refreshAfterDemo")?.addEventListener("click", () => {
    window.location.hash = "call-review";
    window.location.reload();
  });
}

const scenarioSelect = document.querySelector("#scenarioSelect");
if (scenarioSelect) {
  scenarioSelect.addEventListener("change", (event) => setScenario(event.target.value));
}

const demoForm = document.querySelector("#demoCallForm");
if (demoForm) {
  demoForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = document.querySelector("#runCallButton");
    const result = document.querySelector("#demoResult");
    button.disabled = true;
    button.textContent = "Running workflow…";
    result.classList.add("hidden");
    result.classList.remove("demo-result-error");

    const payload = {
      tenant_slug: tenantSlug,
      external_call_id: `web-${Date.now()}`,
      caller_phone: document.querySelector("#callerPhoneInput").value,
      customer_name: document.querySelector("#customerNameInput").value,
      transcript: document.querySelector("#transcriptInput").value,
      requested_time: document.querySelector("#requestedTimeInput").value || null,
      service: document.querySelector("#serviceInput").value || null,
    };

    try {
      const response = await fetch("/v1/calls/simulate", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Call workflow failed");
      renderDemoResult(data);
    } catch (error) {
      result.textContent = error.message;
      result.classList.remove("hidden");
      result.classList.add("demo-result-error");
    } finally {
      button.disabled = false;
      button.textContent = "Run end-to-end call";
    }
  });
}

document.querySelectorAll(".approval-form").forEach((form) => {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const suggestionId = form.dataset.suggestionId;
    const textarea = form.querySelector("textarea");
    const button = form.querySelector("button");
    const status = form.querySelector(".approval-status");
    button.disabled = true;
    button.textContent = "Publishing…";
    status.textContent = "";
    try {
      const response = await fetch(`/v1/learning/${tenantSlug}/suggestions/${suggestionId}/approve`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ answer: textarea.value }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Approval failed");
      status.textContent = "Approved. Regression case created.";
      window.setTimeout(() => window.location.reload(), 1000);
    } catch (error) {
      status.textContent = error.message;
    } finally {
      button.disabled = false;
      button.textContent = "Approve and publish";
    }
  });
});

document.querySelectorAll(".trace-toggle").forEach((button) => {
  button.addEventListener("click", () => {
    const row = document.getElementById(button.dataset.target);
    const isHidden = row.classList.toggle("hidden");
    button.textContent = isHidden ? "Review" : "Close";
  });
});

const sidebar = document.querySelector("#sidebar");
const overlay = document.querySelector("#sidebarOverlay");
const menuButton = document.querySelector("#menuButton");
const closeButton = document.querySelector("#sidebarClose");

function closeSidebar() {
  sidebar?.classList.remove("open");
  overlay?.classList.remove("visible");
}

menuButton?.addEventListener("click", () => {
  sidebar?.classList.add("open");
  overlay?.classList.add("visible");
});
closeButton?.addEventListener("click", closeSidebar);
overlay?.addEventListener("click", closeSidebar);
document.querySelectorAll(".sidebar-nav a").forEach((link) => link.addEventListener("click", closeSidebar));
