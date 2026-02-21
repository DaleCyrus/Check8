function setupLoginForm() {
  const loginAs = document.getElementById("login_as");
  const identifier = document.getElementById("identifier");
  const label = document.querySelector('[data-label="identifierLabel"]');
  if (!loginAs || !identifier || !label) return;

  function apply() {
    const mode = loginAs.value;
    if (mode === "office") {
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

async function verifyTokenViaJson(token) {
  const url = window.CHECK8_VERIFY_JSON_URL;
  if (!url) return null;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new Error((data && data.error) || "Verify failed");
  return data;
}

function setupQrScanner() {
  const el = document.getElementById("qrReader");
  if (!el) return;

  function renderResult(ok, html) {
    const box = document.getElementById("verifyResult");
    if (!box) return;
    box.innerHTML = html;
    box.style.borderColor = ok ? "rgba(54,211,153,.55)" : "rgba(251,113,133,.55)";
    box.style.background = ok ? "rgba(54,211,153,.08)" : "rgba(251,113,133,.08)";
  }

  if (!window.Html5Qrcode) {
    renderResult(false, '<div class="muted">Scanner library not loaded. Use paste mode.</div>');
    return;
  }

  const html5QrCode = new window.Html5Qrcode("qrReader");
  const config = { fps: 10, qrbox: { width: 250, height: 250 } };
  let lastToken = null;

  window.Html5Qrcode.getCameras()
    .then((devices) => {
      const cam = devices && devices[0] && devices[0].id;
      if (!cam) throw new Error("No camera found");
      return html5QrCode.start(
        cam,
        config,
        async (decodedText) => {
          if (!decodedText || decodedText === lastToken) return;
          lastToken = decodedText;
          try {
            const data = await verifyTokenViaJson(decodedText);
            renderResult(
              true,
              `
                <div class="resultLine"><strong>Valid</strong></div>
                <div class="resultLine">Student No.: <code>${data.student.student_number}</code></div>
                <div class="resultLine">Name: ${data.student.full_name}</div>
                <div class="resultLine">This office status: <span class="badge badge--${data.clearance.state}">${data.clearance.state}</span></div>
                <div class="resultLine muted">${data.clearance.note ? data.clearance.note : "—"}</div>
              `
            );
          } catch (e) {
            renderResult(false, `<div class="resultLine"><strong>Invalid</strong></div><div class="muted small">${e.message}</div>`);
          }
        },
        () => {}
      );
    })
    .catch((err) => {
      renderResult(false, `<div class="muted">Camera scan unavailable: ${String(err)}</div>`);
    });
}

document.addEventListener("DOMContentLoaded", () => {
  setupLoginForm();
  setupCopyButtons();
  setupQrScanner();
});

