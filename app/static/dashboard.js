const body = document.body;
const tenantSlug = body.dataset.tenant || "northstar-hvac";

const transcriptSamples = [
  {
    label: "Book service",
    text: "Hi, my AC stopped working. I need an AC diagnostic Thursday at 2 PM.",
  },
  {
    label: "Pricing",
    text: "How much does a standard diagnostic visit cost?",
  },
  {
    label: "Emergency",
    text: "There is smoke coming from my furnace. This is an emergency.",
  },
  {
    label: "Unsupported",
    text: "Do you service geothermal heat pumps in landmark buildings?",
  },
];

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function setupTranscriptOnlyDemo() {
  const content = document.querySelector(".app-content");
  const overview = document.querySelector("#overview");
  if (content && overview && !document.querySelector("#productExplainer")) {
    const explainer = document.createElement("article");
    explainer.id = "productExplainer";
    explainer.className = "panel";
    explainer.innerHTML = `
      <div class="panel-header">
        <div>
          <p class="eyebrow">WHAT CALLFLOW RECOVERY DOES</p>
          <h2>Turn a caller's words into a business action.</h2>
          <p>Enter the phone number they called from and what they said. CallFlow detects the request, uses approved business knowledge, then answers, creates an appointment, or escalates to a human. It records the full outcome so the business can review what happened.</p>
        </div>
      </div>
    `;
    content.insertBefore(explainer, overview);
  }

  const demoPanel = document.querySelector(".demo-panel");
  const panelTitle = demoPanel?.querySelector(".panel-header h3");
  const panelCopy = demoPanel?.querySelector(".panel-header p");
  if (panelTitle) panelTitle.textContent = "Process a caller transcript";
  if (panelCopy) panelCopy.textContent = "Only the caller phone number and transcript are needed. CallFlow decides what action to take.";

  const scenarioSelect = document.querySelector("#scenarioSelect");
  scenarioSelect?.closest("label")?.remove();

  document.querySelector("#customerNameInput")?.closest("label")?.remove();
  document.querySelector("#bookingFields")?.remove();

  const phoneInput = document.querySelector("#callerPhoneInput");
  if (phoneInput) {
    phoneInput.value = "+12125550123";
    const row = phoneInput.closest(".form-row");
    row?.classList.remove("form-row");
  }

  const transcriptInput = document.querySelector("#transcriptInput");
  if (transcriptInput) {
    transcriptInput.value = transcriptSamples[0].text;
    transcriptInput.rows = 6;
    transcriptInput.placeholder = "Example: Hi, my AC stopped working. I need an AC diagnostic Thursday at 2 PM.";

    const transcriptLabel = transcriptInput.closest("label");
    if (transcriptLabel && !document.querySelector("#transcriptSamples")) {
      const sampleWrap = document.createElement("div");
      sampleWrap.id = "transcriptSamples";
      sampleWrap.innerHTML = `
        <small>Try a sample or type your own:</small>
        <div class="hero-actions" style="margin-top: 10px; flex-wrap: wrap; gap: 8px;">
          ${transcriptSamples
            .map(
              (sample, index) =>
                `<button class="button button-small button-outline transcript-sample" type="button" data-sample-index="${index}">${escapeHtml(sample.label)}</button>`,
            )
            .join("")}
        </div>
      `;
      transcriptLabel.insertAdjacentElement("afterend", sampleWrap);
      sampleWrap.querySelectorAll(".transcript-sample").forEach((button) => {
        button.addEventListener("click", () => {
          const sample = transcriptSamples[Number(button.dataset.sampleIndex)];
          transcriptInput.value = sample.text;
          transcriptInput.focus();
        });
      });
    }
  }

  const runButton = document.querySelector("#runCallButton");
  if (runButton) runButton.textContent = "Process transcript";
}

function renderDemoResult(data) {
  const result = document.querySelector("#demoResult");
  const citations = Array.isArray(data.citations) && data.citations.length
    ? data.citations.map((item) => `<span>${escapeHtml(item.title || item.source)}</span>`).join("")
    : "<span>No citation required</span>";
  const demoAdapters = String(data.crm_contact_id || "").startsWith("demo-")
    || String(data.sms_message_id || "").startsWith("demo-");
  const integrationLabel = demoAdapters ? "Demo CRM/SMS adapters" : "Live downstream integrations";
  const actionLabel = data.status === "booked"
    ? "Appointment created"
    : data.status === "escalated"
      ? "Escalated to human"
      : "Question answered";

  result.innerHTML = `
    <div class="demo-result-header">
      <div><span class="badge badge-${escapeHtml(data.status)}">${escapeHtml(actionLabel)}</span><strong>Detected intent: ${escapeHtml(data.intent.replaceAll("_", " "))}</strong></div>
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
    <p class="reload-note">Outcome persisted. Use the trace review below for the full execution details.</p>
    <button class="button button-dark button-small" type="button" id="refreshAfterDemo">Refresh and inspect trace</button>
  `;
  result.classList.remove("hidden");
  document.querySelector("#refreshAfterDemo")?.addEventListener("click", () => {
    window.location.hash = "call-review";
    window.location.reload();
  });
}

function addRecentOutcome(data, transcript) {
  const feed = document.querySelector(".activity-feed");
  if (!feed) return;

  feed.querySelector(".empty-state")?.remove();

  const item = document.createElement("div");
  item.className = "activity-item";
  item.innerHTML = `
    <span class="activity-status status-${escapeHtml(data.status)}"></span>
    <div class="activity-content">
      <div>
        <strong>${escapeHtml(String(data.intent || "unknown").replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase()))}</strong>
        <span class="badge badge-${escapeHtml(data.status)}">${escapeHtml(data.status)}</span>
      </div>
      <p>${escapeHtml(transcript)}</p>
      <small>${escapeHtml(data.latency_ms)} ms · $${Number(data.cost_usd || 0).toFixed(5)} · ${Math.round(Number(data.confidence || 0) * 100)}% confidence</small>
    </div>
  `;

  feed.prepend(item);
  [...feed.querySelectorAll(".activity-item")].slice(6).forEach((row) => row.remove());
}

setupTranscriptOnlyDemo();

const demoForm = document.querySelector("#demoCallForm");
if (demoForm) {
  demoForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = document.querySelector("#runCallButton");
    const result = document.querySelector("#demoResult");
    const callerPhone = document.querySelector("#callerPhoneInput").value.trim();
    const transcript = document.querySelector("#transcriptInput").value.trim();

    if (!callerPhone || !transcript) {
      result.textContent = "Enter the caller phone number and transcript.";
      result.classList.remove("hidden");
      result.classList.add("demo-result-error");
      return;
    }

    button.disabled = true;
    button.textContent = "Understanding transcript…";
    result.classList.add("hidden");
    result.classList.remove("demo-result-error");

    const payload = {
      tenant_slug: tenantSlug,
      external_call_id: `web-${Date.now()}`,
      caller_phone: callerPhone,
      transcript,
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
      addRecentOutcome(data, transcript);
    } catch (error) {
      result.textContent = error.message;
      result.classList.remove("hidden");
      result.classList.add("demo-result-error");
    } finally {
      button.disabled = false;
      button.textContent = "Process transcript";
    }
  });
}

const environmentText = document.querySelector(".tenant-switcher small")?.textContent?.toLowerCase() || "";
const publicDemo = environmentText.includes("demo environment");

document.querySelectorAll(".approval-form").forEach((form) => {
  const textarea = form.querySelector("textarea");
  const button = form.querySelector("button");
  const status = form.querySelector(".approval-status");

  if (publicDemo) {
    textarea.disabled = true;
    textarea.placeholder = "Publishing is disabled in the shared public demo.";
    button.disabled = true;
    button.textContent = "Admin approval protected";
    status.textContent = "Run an unsupported transcript to inspect escalation; shared knowledge writes require admin authorization.";
    return;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const suggestionId = form.dataset.suggestionId;
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
