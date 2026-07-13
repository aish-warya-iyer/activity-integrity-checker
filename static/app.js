const authStatus = document.getElementById("authStatus");
const loggedOut = document.getElementById("loggedOut");
const loggedIn = document.getElementById("loggedIn");
const activityList = document.getElementById("activityList");
const emptyState = document.getElementById("emptyState");
const activityDetail = document.getElementById("activityDetail");
const detailName = document.getElementById("detailName");
const detailMeta = document.getElementById("detailMeta");
const analyzeBtn = document.getElementById("analyzeBtn");
const writebackBtn = document.getElementById("writebackBtn");
const analysisResult = document.getElementById("analysisResult");
const segmentList = document.getElementById("segmentList");
const explanationBox = document.getElementById("explanationBox");
const explanationText = document.getElementById("explanationText");
const guardrailNote = document.getElementById("guardrailNote");
const writebackResult = document.getElementById("writebackResult");

let selectedActivityId = null;

function fmtDistance(meters) {
  return (meters / 1000).toFixed(2) + " km";
}

function fmtDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

async function init() {
  try {
    const athlete = await fetchJSON("/profile");
    authStatus.textContent = `Connected as ${athlete.firstname} ${athlete.lastname}`;
    loggedOut.classList.add("hidden");
    loggedIn.classList.remove("hidden");
    await loadActivities();
  } catch (e) {
    loggedOut.classList.remove("hidden");
    loggedIn.classList.add("hidden");
  }
}

async function fetchJSON(url, options) {
  const resp = await fetch(url, options);
  if (!resp.ok) throw new Error(`Request failed: ${resp.status}`);
  return resp.json();
}

async function loadActivities() {
  const activities = await fetchJSON("/activities");
  activityList.innerHTML = "";
  activities.forEach((a) => {
    const li = document.createElement("li");
    li.className = "activity-item";
    li.dataset.id = a.id;
    li.innerHTML = `
      <div class="name">${a.name}</div>
      <div class="meta">${a.type} · ${fmtDate(a.start_date_local)} · ${fmtDistance(a.distance_m)}</div>
    `;
    li.addEventListener("click", () => selectActivity(a));
    activityList.appendChild(li);
  });
}

function selectActivity(activity) {
  selectedActivityId = activity.id;

  document.querySelectorAll(".activity-item").forEach((el) => {
    el.classList.toggle("active", Number(el.dataset.id) === activity.id);
  });

  emptyState.classList.add("hidden");
  activityDetail.classList.remove("hidden");

  detailName.textContent = activity.name;
  detailMeta.textContent = `${activity.type} · ${fmtDate(activity.start_date_local)} · ${fmtDistance(activity.distance_m)}`;

  analysisResult.classList.add("hidden");
  writebackResult.classList.add("hidden");
  writebackBtn.classList.add("hidden");
  segmentList.innerHTML = "";
  explanationBox.classList.add("hidden");
}

analyzeBtn.addEventListener("click", async () => {
  if (!selectedActivityId) return;
  analyzeBtn.disabled = true;
  analyzeBtn.textContent = "Analyzing…";

  try {
    const result = await fetchJSON(`/activity/${selectedActivityId}/explain`);
    renderAnalysis(result);
  } catch (e) {
    segmentList.innerHTML = `<p>Analysis failed: ${e.message}</p>`;
    analysisResult.classList.remove("hidden");
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = "Analyze Course Integrity";
  }
});

function renderAnalysis(result) {
  analysisResult.classList.remove("hidden");
  segmentList.innerHTML = "";

  if (!result.deviation_results || result.deviation_results.length === 0) {
    segmentList.innerHTML = `<p>${result.note || "No matched segment efforts on this activity."}</p>`;
    explanationBox.classList.add("hidden");
    writebackBtn.classList.add("hidden");
    return;
  }

  result.deviation_results.forEach((seg) => {
    const card = document.createElement("div");
    card.className = "segment-card";
    card.innerHTML = `
      <div>
        <div class="segment-name">${seg.segment_name || "Segment " + seg.segment_id}</div>
        <div class="segment-dev">Max deviation: ${seg.max_deviation_m} m (threshold ${seg.threshold_m} m)</div>
      </div>
      <span class="badge ${seg.flagged ? "badge-flagged" : "badge-clean"}">${seg.flagged ? "Flagged" : "Clean"}</span>
    `;
    segmentList.appendChild(card);
  });

  if (result.final_text) {
    explanationText.textContent = result.final_text;
    if (result.guardrail_blocked) {
      guardrailNote.textContent = `Guardrail blocked the AI-generated explanation (adherence score ${result.adherence_score}) — showing the deterministic fallback instead.`;
      guardrailNote.className = "guardrail-note blocked";
    } else {
      guardrailNote.textContent = `Passed guardrail check (adherence score ${result.adherence_score}).`;
      guardrailNote.className = "guardrail-note passed";
    }
    explanationBox.classList.remove("hidden");
  }

  writebackBtn.classList.remove("hidden");
}

writebackBtn.addEventListener("click", async () => {
  if (!selectedActivityId) return;
  writebackBtn.disabled = true;
  writebackBtn.textContent = "Writing…";

  try {
    const result = await fetchJSON(`/activity/${selectedActivityId}/writeback`, { method: "POST" });
    writebackResult.classList.remove("hidden");
    if (result.written === false) {
      writebackResult.textContent = result.note;
    } else {
      writebackResult.innerHTML = `
        <strong>Written to Strava description:</strong>
        <p>${result.written_text}</p>
      `;
    }
  } catch (e) {
    writebackResult.classList.remove("hidden");
    writebackResult.textContent = `Write-back failed: ${e.message}`;
  } finally {
    writebackBtn.disabled = false;
    writebackBtn.textContent = "Write Result to Strava";
  }
});

init();
