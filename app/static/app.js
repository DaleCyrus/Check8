function setupLoginForm() {
  const loginAs = document.getElementById("login_as");
  const identifier = document.getElementById("identifier");
  const label = document.querySelector('[data-label="identifierLabel"]');
  if (!loginAs || !identifier || !label) return;

  function apply() {
    const mode = loginAs.value;
    if (mode === "faculty") {
      label.textContent = "Username";
      identifier.placeholder = "e.g. registrar";
    } else {
      label.textContent = "Student Number";
      identifier.placeholder = "e.g. 2022-0001";
    }
  }

  loginAs.addEventListener("change", apply);
  apply();
}

function setupCopyButtons() {
  const btn = document.querySelector("[data-copy-btn]");
  const src = document.querySelector("[data-copy-source]");
  if (!btn || !src) return;
  btn.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(src.value);
      btn.textContent = "Copied";
      setTimeout(() => (btn.textContent = "Copy token"), 1200);
    } catch {
      // fallback
      src.select();
      document.execCommand("copy");
    }
  });
}

function setupPasswordPeek() {
  document.querySelectorAll("[data-password-toggle]").forEach((button) => {
    const input = document.getElementById(button.dataset.passwordTarget);
    if (!input) return;
    let hideTimer;

    button.addEventListener("click", () => {
      clearTimeout(hideTimer);
      const showing = input.type === "text";
      input.type = showing ? "password" : "text";
      button.textContent = showing ? "👁" : "🙈";
      button.setAttribute("aria-label", showing ? "Show password" : "Hide password");
      button.setAttribute("aria-pressed", String(!showing));

      if (!showing) {
        hideTimer = setTimeout(() => {
          input.type = "password";
          button.textContent = "👁";
          button.setAttribute("aria-label", "Show password");
          button.setAttribute("aria-pressed", "false");
        }, 1500);
      }
    });
  });
}

async function verifyTokenViaJson(token) {
  const url = window.CHECK8_VERIFY_JSON_URL;
  if (!url) return null;
  
  // Get selected course from the selector
  const courseSelector = document.getElementById("courseSelector");
  const courseId = courseSelector ? courseSelector.value : null;
  
  if (!courseId) {
    const warning = document.getElementById("courseWarning");
    if (warning) warning.style.display = "inline";
    throw new Error("Please select a course first");
  }
  
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';
  const res = await fetch(url, {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken
    },
    body: JSON.stringify({ token, course_id: parseInt(courseId) }),
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error((data && data.error) || "Verification failed");
  return data;
}

function setupQrScanner() {
  const el = document.getElementById("qrReader");
  if (!el) return;

  // Prevent double initialization
  if (window.SCANNER_ALREADY_SETUP) return;
  window.SCANNER_ALREADY_SETUP = true;

  let html5QrCode = null;
  let isRunning = false;
  let lastToken = null;

  function isMobileDevice() {
    const ua = (navigator.userAgent || "").toLowerCase();
    const mobileByUa = /android|iphone|ipad|ipod|mobile/.test(ua);
    const mobileByPointer = window.matchMedia && window.matchMedia("(pointer: coarse)").matches;
    return mobileByUa || mobileByPointer;
  }

  function pickPreferredCamera(devices) {
    if (!devices || devices.length === 0) return null;

    const isMobile = isMobileDevice();
    const backKeywords = ["back", "rear", "environment", "traseira"];
    const frontKeywords = ["front", "user", "facetime", "integrated", "webcam", "camera"];

    const findByKeywords = (keywords) =>
      devices.find((d) => {
        const label = (d.label || "").toLowerCase();
        return keywords.some((kw) => label.includes(kw));
      });

    if (isMobile) {
      // Mobile default: use back camera for easier QR scanning.
      const backCamera = findByKeywords(backKeywords);
      return (backCamera || devices[devices.length - 1]).id;
    }

    // Desktop/laptop default: use front/user camera.
    const frontCamera = findByKeywords(frontKeywords);
    return (frontCamera || devices[0]).id;
  }

  function renderResult(ok, html) {
    const box = document.getElementById("verifyResult");
    if (!box) return;
    box.innerHTML = html;
    box.style.borderColor = ok ? "rgba(54,211,153,.55)" : "rgba(251,113,133,.55)";
    box.style.background = ok ? "rgba(54,211,153,.08)" : "rgba(251,113,133,.08)";
  }

  function renderStatusPopup(state, studentName, studentNo, note, studentId, courseId) {
    const box = document.getElementById("verifyResult");
    if (!box) return;
    
    // Determine status display
    let statusIcon = "❓";
    let statusColor = "#ff9800"; // orange for pending
    
    if (state === "cleared") {
      statusIcon = "✅";
      statusColor = "#22c55e"; // green
    } else if (state === "blocked") {
      statusIcon = "❌";
      statusColor = "#ef4444"; // red
    }
    
    box.innerHTML = `
      <div style="display: flex; gap: 1.5rem; align-items: flex-start; padding: 1.5rem;">
        <div style="font-size: 3.5em; line-height: 1; animation: scaleIn 0.3s ease-out; flex-shrink: 0;">${statusIcon}</div>
        <div style="flex: 1; min-width: 0;">
          <div style="font-weight: 700; font-size: 1.1em; margin-bottom: 0.5rem; word-break: break-word;">${studentName}</div>
          <div style="font-size: 0.9em; color: #bfa074; margin-bottom: 0.75rem; word-break: break-all;"><strong>ID:</strong> ${studentNo}</div>
          ${note ? `<div style="font-size: 0.85em; color: #bfa074; margin-bottom: 0.75rem; font-style: italic; border-left: 2px solid ${statusColor}; padding-left: 0.75rem;">${note}</div>` : ''}
          <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0.75rem; margin-top: 1rem;">
            <button id="btnApprove" class="btn btn--sm" style="background: #22c55e; border: none; color: white; cursor: pointer; padding: 0.6rem 0.75rem; border-radius: 8px; font-size: 0.9em; font-weight: 600; transition: all 0.2s;" data-student="${studentId}" data-course="${courseId}" data-note="${note || ''}">
              ✓ Approve
            </button>
            <button id="btnPending" class="btn btn--sm" style="background: #ff9800; border: none; color: white; cursor: pointer; padding: 0.6rem 0.75rem; border-radius: 8px; font-size: 0.9em; font-weight: 600; transition: all 0.2s;" data-student="${studentId}" data-course="${courseId}" data-note="${note || ''}">
              ◉ Pending
            </button>
            <button id="btnDecline" class="btn btn--sm" style="background: #ef4444; border: none; color: white; cursor: pointer; padding: 0.6rem 0.75rem; border-radius: 8px; font-size: 0.9em; font-weight: 600; transition: all 0.2s;" data-student="${studentId}" data-course="${courseId}" data-note="${note || ''}">
              ✕ Decline
            </button>
          </div>
        </div>
      </div>
    `;
    
    box.style.borderColor = statusColor + "88";
    box.style.background = statusColor + "11";
    
    // Attach event listeners to buttons
    const btnApprove = document.getElementById("btnApprove");
    const btnPending = document.getElementById("btnPending");
    const btnDecline = document.getElementById("btnDecline");
    
    if (btnApprove) {
      btnApprove.addEventListener("click", () => {
        updateStudentStatus(studentId, courseId, "cleared", btnApprove, note);
      });
    }
    if (btnPending) {
      btnPending.addEventListener("click", () => {
        updateStudentStatus(studentId, courseId, "pending", btnPending, note);
      });
    }
    if (btnDecline) {
      btnDecline.addEventListener("click", () => {
        updateStudentStatus(studentId, courseId, "blocked", btnDecline, note);
      });
    }
  }

  async function updateStudentStatus(studentId, courseId, newState, buttonEl, note) {
    try {
      // Disable all buttons and show loading state
      if (buttonEl) {
        buttonEl.disabled = true;
        buttonEl.style.opacity = "0.6";
      }

      const formData = new URLSearchParams({
        student_id: studentId,
        course_id: courseId,
        state: newState
      });
      
      // Include note if provided
      if (note) {
        formData.append("note", note);
      }
      
      // Add CSRF token
      const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';
      if (csrfToken) {
        formData.append("csrf_token", csrfToken);
      }

      const response = await fetch("/faculty/set-status", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: formData
      });
      
      if (response.ok) {
        // Show success message
        const box = document.getElementById("verifyResult");
        const stateIcons = { cleared: "✅", blocked: "❌", pending: "⏳" };
        const stateLabels = { cleared: "Approved", blocked: "Declined", pending: "Pending" };
        const stateColors = { cleared: "#22c55e", blocked: "#ef4444", pending: "#ff9800" };
        
        box.innerHTML = `
          <div style="display: flex; align-items: center; gap: 1rem; padding: 1rem;">
            <div style="font-size: 2.5em; animation: scaleIn 0.3s ease-out;">${stateIcons[newState]}</div>
            <div>
              <div style="font-weight: 700; color: ${stateColors[newState]};">Status Updated</div>
              <div style="font-size: 0.9em; color: #bfa074;">Cleared as: <strong>${stateLabels[newState]}</strong></div>
            </div>
          </div>
        `;
        
        box.style.borderColor = stateColors[newState] + "88";
        box.style.background = stateColors[newState] + "11";
      } else {
        console.error("Update failed with status:", response.status, response.statusText);
        const errorText = await response.text();
        console.error("Response body:", errorText);
        renderResult(false, `<div class="resultLine"><strong>Error</strong></div><div class="muted small">Failed to update status (${response.status})</div>`);
        if (buttonEl) {
          buttonEl.disabled = false;
          buttonEl.style.opacity = "1";
        }
      }
    } catch (e) {
      console.error("Status update failed:", e);
      renderResult(false, `<div class="resultLine"><strong>Error</strong></div><div class="muted small">${e.message}</div>`);
      if (buttonEl) {
        buttonEl.disabled = false;
        buttonEl.style.opacity = "1";
      }
    }
  }

  async function handlePasteTokenSubmit(event) {
    event.preventDefault();
    const input = document.getElementById("tokenInput");
    const token = input.value.trim();
    
    if (!token) {
      renderResult(false, `<div class="resultLine"><strong>Error</strong></div><div class="muted small">Please paste a token</div>`);
      return;
    }
    
    try {
      const data = await verifyTokenViaJson(token);
      renderStatusPopup(
        data.clearance.state,
        data.student.full_name,
        data.student.student_number,
        data.clearance.note,
        data.student.id,
        data.course ? data.course.id : null
      );
    } catch (e) {
      renderResult(false, `<div class="resultLine"><strong>Invalid</strong></div><div class="muted small">${e.message}</div>`);
    }
  }

  function updateCameraStatus(status, message = "") {
    const loading = document.getElementById("cameraLoading");
    const ready = document.getElementById("cameraReady");
    const error = document.getElementById("cameraError");

    if (loading) loading.style.display = status === "loading" ? "inline" : "none";
    if (ready) ready.style.display = status === "ready" ? "inline" : "none";
    if (error) {
      error.style.display = status === "error" ? "inline" : "none";
      if (message) error.textContent = message;
    }
  }

  function toggleControls(show) {
    const controls = document.getElementById("cameraControls");
    const torch = document.getElementById("toggleTorch");
    if (controls) controls.style.display = show ? "flex" : "none";
    if (torch && show) {
      // Check if torch is supported
      if (html5QrCode && typeof html5QrCode.getRunningTrackCapabilities === "function") {
        torch.style.display = "block";
      }
    }
  }

  if (!window.Html5Qrcode) {
    console.error("html5-qrcode library not loaded");
    el.innerHTML = '<div style="padding: 2rem; text-align: center; color: #2d1600;"><div style="font-size: 2.5em; margin-bottom: 1rem;">❌</div><strong style="font-size: 1.1em; display: block; margin-bottom: 0.5rem;">Camera Not Available</strong><div style="font-size: 0.9em; margin-bottom: 1rem; color: #bfa074;">The QR scanner library could not be loaded.</div><div style="font-size: 0.85em; color: #bfa074;">Please use the <strong>Paste token</strong> section below instead.</div></div>';
    updateCameraStatus("error", "Library not available");
    return;
  }

  html5QrCode = new window.Html5Qrcode("qrReader");
  const config = { fps: 10, qrbox: { width: 250, height: 250 } };

  // Initialize camera on page load
  updateCameraStatus("loading");
  window.Html5Qrcode.getCameras()
    .then((devices) => {
      const cam = pickPreferredCamera(devices);
      if (!cam) throw new Error("No camera found");

      return html5QrCode.start(
        cam,
        config,
        async (decodedText) => {
          if (!decodedText || decodedText === lastToken) return;
          lastToken = decodedText;
          try {
            const data = await verifyTokenViaJson(decodedText);
            renderStatusPopup(
              data.clearance.state,
              data.student.full_name,
              data.student.student_number,
              data.clearance.note,
              data.student.id,
              data.course ? data.course.id : null
            );
          } catch (e) {
            renderResult(false, `<div class="resultLine"><strong>Invalid</strong></div><div class="muted small">${e.message}</div>`);
          }
        },
        () => {}
      );
    })
    .then(() => {
      isRunning = true;
      updateCameraStatus("ready");
      toggleControls(true);
    })
    .catch((err) => {
      const errorMsg = String(err);
      console.error("❌ Camera initialization failed:", errorMsg);
      console.error("Full error:", err);
      updateCameraStatus("error", "Camera not accessible");
      el.innerHTML = '<div style="padding: 2rem; text-align: center; color: #2d1600;"><div style="font-size: 2.5em; margin-bottom: 1rem;">📱</div><strong style="font-size: 1.1em; display: block; margin-bottom: 0.5rem;">Camera Access Denied</strong><div style="font-size: 0.9em; margin-bottom: 1rem; color: #bfa074;">Error: ' + errorMsg + '</div><div style="font-size: 0.85em; color: #bfa074;"><strong>Solution:</strong> Use the Paste token section below</div></div>';
      toggleControls(false);
    });

  // Camera toggle button
  const toggleBtn = document.getElementById("toggleCamera");
  if (toggleBtn) {
    toggleBtn.addEventListener("click", async () => {
      try {
        if (isRunning) {
          await html5QrCode.stop();
          isRunning = false;
          toggleBtn.textContent = "Start Camera";
          updateCameraStatus("");
          toggleControls(false);
        } else {
          const devices = await window.Html5Qrcode.getCameras();
          const cam = pickPreferredCamera(devices);
          if (cam) {
            await html5QrCode.start(cam, config, () => {}, () => {});
            isRunning = true;
            toggleBtn.textContent = "Stop Camera";
            updateCameraStatus("ready");
            toggleControls(true);
          }
        }
      } catch (e) {
        updateCameraStatus("error", `Error: ${String(e)}`);
      }
    });
  }

  // Torch toggle button
  const torchBtn = document.getElementById("toggleTorch");
  if (torchBtn) {
    torchBtn.addEventListener("click", async () => {
      try {
        const caps = html5QrCode.getRunningTrackCapabilities();
        if (caps && caps.torch) {
          await html5QrCode.applyConstraints({ advanced: [{ torch: !caps.torch }] });
          torchBtn.style.opacity = caps.torch ? "0.6" : "1";
        }
      } catch (e) {
        console.error("Torch error:", e);
      }
    });
  }
}

document.addEventListener("DOMContentLoaded", () => {
  setupLoginForm();
  setupCopyButtons();
  setupPasswordPeek();
  setupFormLoadingStates();
  // Don't auto-setup QR scanner here - let verify.html handle it with proper timing
});

// ===== FORM LOADING STATES =====
function setupFormLoadingStates() {
  // Find all forms with submit buttons
  document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function(e) {
      // Only add loading state if it's a regular form submission (not AJAX)
      const submitBtn = this.querySelector('button[type="submit"]');
      if (submitBtn && !submitBtn.classList.contains('no-loading')) {
        submitBtn.classList.add('loading');
        submitBtn.disabled = true;
        
        // Original button text for restoration
        const originalText = submitBtn.textContent;
        submitBtn.setAttribute('data-original-text', originalText);
        
        // Restore after 3 seconds if it hasn't redirected
        setTimeout(() => {
          submitBtn.classList.remove('loading');
          submitBtn.disabled = false;
          submitBtn.textContent = originalText;
        }, 3000);
      }
    });
  });
}

// Smooth transition for notification dismissal
function setupNotificationDismissal() {
  document.querySelectorAll('.flash__item').forEach(item => {
    item.addEventListener('click', function() {
      this.style.animation = 'slideInUp 0.3s ease-out reverse';
      setTimeout(() => this.remove(), 300);
    });
  });
}

function setupSiteInteraction() {
  const canUseTrail = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!canUseTrail) return;

  let lastTrailTime = 0;
  const cursorGlow = document.createElement('span');
  cursorGlow.className = 'cursor-glow';
  document.body.appendChild(cursorGlow);
  document.addEventListener('mousemove', (event) => {
    cursorGlow.style.left = `${event.clientX}px`;
    cursorGlow.style.top = `${event.clientY}px`;
    const now = performance.now();
    if (now - lastTrailTime < 45) return;
    lastTrailTime = now;

    const trail = document.createElement('span');
    trail.className = 'cursor-trail';
    trail.style.left = `${event.clientX}px`;
    trail.style.top = `${event.clientY}px`;
    document.body.appendChild(trail);
    trail.addEventListener('animationend', () => trail.remove(), { once: true });
  });
}

document.addEventListener('DOMContentLoaded', setupNotificationDismissal);
document.addEventListener('DOMContentLoaded', setupSiteInteraction);

