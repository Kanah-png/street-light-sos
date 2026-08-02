// Initial Mock Alerts Data (matching dashboard.py structure)
const mockAlerts = [
    {
        time: new Date(Date.now() - 1000 * 60 * 3).toLocaleString(),
        type: "ROAD_ACCIDENT",
        conf: "94%",
        target: "Twilio SMS (+919983974149)",
        badgeClass: "accident"
    },
    {
        time: new Date(Date.now() - 1000 * 60 * 18).toLocaleString(),
        type: "UNCONSCIOUS_PERSON",
        conf: "88%",
        target: "REST Endpoint / Local Log",
        badgeClass: "person"
    },
    {
        time: new Date(Date.now() - 1000 * 60 * 42).toLocaleString(),
        type: "PHYSICAL_FIGHT",
        conf: "91%",
        target: "Twilio Call (+919983974149)",
        badgeClass: "fight"
    },
    {
        time: new Date(Date.now() - 1000 * 60 * 120).toLocaleString(),
        type: "FIRE_SMOKE",
        conf: "82%",
        target: "REST Endpoint",
        badgeClass: "fire"
    }
];

let totalAlertCount = mockAlerts.length;

document.addEventListener("DOMContentLoaded", () => {
    renderTable();

    // 0. Automatically request camera permission on page load
    initUserWebcam();

    // 1. Simulate FPS Fluctuations
    const fpsElem = document.getElementById("hero-fps");
    const dashFpsElem = document.getElementById("dash-fps-val");

    setInterval(() => {
        if (fpsElem && dashFpsElem) {
            const randomFps = (28.5 + Math.random() * 2.8).toFixed(1);
            fpsElem.textContent = randomFps;
            dashFpsElem.textContent = `${randomFps} FPS`;
        }
    }, 1500);

    // 2. Interactive SOS Alert Trigger
    const btnTrigger = document.getElementById("btn-trigger-alert");
    const sosOverlay = document.getElementById("sos-overlay");

    if (btnTrigger && sosOverlay) {
        btnTrigger.addEventListener("click", () => {
            sosOverlay.classList.add("active");
            
            // Auto add to table as well
            addNewAlert("ROAD_ACCIDENT", "96%", "accident");

            setTimeout(() => {
                sosOverlay.classList.remove("active");
            }, 3500);
        });
    }

    // 3. Add Mock Alert Button in Dashboard section
    const btnAddMock = document.getElementById("btn-add-mock-alert");
    if (btnAddMock) {
        btnAddMock.addEventListener("click", () => {
            const categories = [
                { type: "ROAD_ACCIDENT", class: "accident" },
                { type: "PHYSICAL_FIGHT", class: "fight" },
                { type: "UNCONSCIOUS_PERSON", class: "person" },
                { type: "FIRE_SMOKE", class: "fire" }
            ];
            const chosen = categories[Math.floor(Math.random() * categories.length)];
            const randomConf = (80 + Math.floor(Math.random() * 18)) + "%";

            addNewAlert(chosen.type, randomConf, chosen.class);
        });
    }
});

/**
 * Prompt user for camera permission and attach stream to HTML video tag
 */
async function initUserWebcam() {
    const videoElement = document.getElementById("user-webcam");
    const camStatusElem = document.getElementById("dash-cam-status");

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.warn("Webcam access not supported by browser");
        if (camStatusElem) camStatusElem.textContent = "✗ NOT SUPPORTED";
        return;
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 640 },
                height: { ideal: 480 },
                facingMode: "user"
            },
            audio: false
        });

        if (videoElement) {
            videoElement.srcObject = stream;
        }

        if (camStatusElem) {
            camStatusElem.textContent = "✓ LIVE WEBCAM ACTIVE";
            camStatusElem.className = "value text-green";
        }
        console.log("Webcam permission granted and streaming.");
    } catch (err) {
        console.error("Camera permission denied or unavailable:", err);
        if (camStatusElem) {
            camStatusElem.textContent = "⚠ CAM DENIED";
            camStatusElem.className = "value text-accent";
        }
    }
}

function addNewAlert(type, conf, badgeClass) {
    totalAlertCount++;
    const countElem = document.getElementById("dash-alert-count");
    if (countElem) {
        countElem.textContent = totalAlertCount;
    }

    mockAlerts.unshift({
        time: new Date().toLocaleString(),
        type: type,
        conf: conf,
        target: "Twilio SMS & REST Dispatch",
        badgeClass: badgeClass
    });

    renderTable();
}

function renderTable() {
    const tbody = document.getElementById("alerts-table-body");
    if (!tbody) return;

    tbody.innerHTML = "";
    mockAlerts.slice(0, 8).forEach(alert => {
        const tr = document.appendElement ? document.createElement("tr") : document.createElement("tr");
        tr.innerHTML = `
            <td>${alert.time}</td>
            <td><span class="badge-alert ${alert.badgeClass}">${alert.type.replace('_', ' ')}</span></td>
            <td><strong>${alert.conf}</strong></td>
            <td>${alert.target}</td>
            <td><span class="text-green">✓ DISPATCHED</span></td>
        `;
        tbody.appendChild(tr);
    });
}
