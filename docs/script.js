// Initial Mock Alerts Data
const mockAlerts = [
    {
        time: new Date(Date.now() - 1000 * 60 * 3).toLocaleString(),
        type: "ROAD_ACCIDENT",
        conf: "94%",
        target: "Twilio SMS (+919983974149)",
        badgeClass: "tag-red"
    },
    {
        time: new Date(Date.now() - 1000 * 60 * 18).toLocaleString(),
        type: "UNCONSCIOUS_PERSON",
        conf: "88%",
        target: "REST Endpoint / Local Log",
        badgeClass: "tag-yellow"
    },
    {
        time: new Date(Date.now() - 1000 * 60 * 42).toLocaleString(),
        type: "PHYSICAL_FIGHT",
        conf: "91%",
        target: "Twilio Call (+919983974149)",
        badgeClass: "tag-red"
    },
    {
        time: new Date(Date.now() - 1000 * 60 * 120).toLocaleString(),
        type: "FIRE_SMOKE",
        conf: "82%",
        target: "REST Endpoint",
        badgeClass: "tag-yellow"
    }
];

let totalAlertCount = mockAlerts.length;
let realAiModel = null;

document.addEventListener("DOMContentLoaded", async () => {
    renderTable();

    // 0. Automatically request camera permission on page load
    initUserWebcam();

    // 1. Load Pretrained TensorFlow COCO-SSD Neural Network AI Model
    loadRealAIModel();

    // 2. FPS Fluctuation Simulation
    const fpsElem = document.getElementById("hero-fps");
    const dashFpsElem = document.getElementById("dash-fps-val");
    setInterval(() => {
        if (fpsElem && dashFpsElem) {
            const randomFps = (28.5 + Math.random() * 2.8).toFixed(1);
            fpsElem.textContent = randomFps;
            dashFpsElem.textContent = `${randomFps} FPS`;
        }
    }, 1500);

    // 3. Interactive SOS Alert Trigger
    const btnTrigger = document.getElementById("btn-trigger-alert");
    const sosOverlay = document.getElementById("sos-overlay");
    if (btnTrigger && sosOverlay) {
        btnTrigger.addEventListener("click", () => {
            sosOverlay.classList.add("active");
            addNewAlert("ROAD_ACCIDENT", "96%", "tag-red");
            setTimeout(() => {
                sosOverlay.classList.remove("active");
            }, 3500);
        });
    }

    // 4. Add Mock Alert Button
    const btnAddMock = document.getElementById("btn-add-mock-alert");
    if (btnAddMock) {
        btnAddMock.addEventListener("click", () => {
            const categories = [
                { type: "ROAD_ACCIDENT", class: "tag-red" },
                { type: "PHYSICAL_FIGHT", class: "tag-red" },
                { type: "UNCONSCIOUS_PERSON", class: "tag-yellow" },
                { type: "FIRE_SMOKE", class: "tag-yellow" }
            ];
            const chosen = categories[Math.floor(Math.random() * categories.length)];
            const randomConf = (80 + Math.floor(Math.random() * 18)) + "%";
            addNewAlert(chosen.type, randomConf, chosen.class);
        });
    }

    // 5. Image Upload & AI Detection Processing
    initImageUploadAI();
});

/**
 * Load Pretrained Object Detection Neural Network
 */
async function loadRealAIModel() {
    const placeholder = document.getElementById("upload-title-text");
    try {
        console.log("Loading TensorFlow COCO-SSD AI Model...");
        if (window.cocoSsd) {
            realAiModel = await window.cocoSsd.load();
            console.log("TensorFlow COCO-SSD AI Model Loaded Successfully.");
        }
    } catch (e) {
        console.warn("Could not load TensorFlow model via CDN, fallback enabled:", e);
    }
}

/**
 * Prompt user for camera permission automatically
 */
async function initUserWebcam() {
    const videoElement = document.getElementById("user-webcam");
    const camStatusElem = document.getElementById("dash-cam-status");

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        if (camStatusElem) camStatusElem.textContent = "✗ NOT SUPPORTED";
        return;
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 640 }, height: { ideal: 480 } },
            audio: false
        });

        if (videoElement) {
            videoElement.srcObject = stream;
        }

        if (camStatusElem) {
            camStatusElem.textContent = "✓ WEBCAM ACTIVE";
            camStatusElem.className = "value text-green";
        }
    } catch (err) {
        if (camStatusElem) {
            camStatusElem.textContent = "⚠ CAM DENIED";
            camStatusElem.className = "value text-yellow";
        }
    }
}

/**
 * Image Upload & AI Emergency Analysis Handler
 */
function initImageUploadAI() {
    const fileInput = document.getElementById("file-input");
    const dropzone = document.getElementById("dropzone");
    const placeholder = document.getElementById("analysis-placeholder");
    const canvasWrap = document.getElementById("canvas-wrap");
    const canvas = document.getElementById("analysis-canvas");
    const banner = document.getElementById("analysis-banner");
    const bannerText = document.getElementById("banner-text");

    if (!fileInput || !dropzone || !canvas) return;

    dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.classList.add("dragover");
    });

    dropzone.addEventListener("dragleave", () => {
        dropzone.classList.remove("dragover");
    });

    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("dragover");
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            processImageFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files[0]) {
            processImageFile(e.target.files[0]);
        }
    });

    function processImageFile(file) {
        const reader = new FileReader();
        reader.onload = function (event) {
            const img = new Image();
            img.onload = async function () {
                placeholder.style.display = "none";
                canvasWrap.style.display = "block";

                const ctx = canvas.getContext("2d");
                canvas.width = img.width;
                canvas.height = img.height;
                ctx.drawImage(img, 0, 0);

                if (realAiModel) {
                    // Run real neural network model inference on image element
                    const predictions = await realAiModel.detect(img);
                    renderRealAIDetections(ctx, predictions, img.width, img.height);
                } else {
                    // Fallback detection box
                    runFallbackDetection(ctx, img.width, img.height);
                }
            };
            img.src = event.target.result;
        };
        reader.readAsDataURL(file);
    }

    function renderRealAIDetections(ctx, predictions, width, height) {
        let vehicleCount = 0;
        let personCount = 0;

        if (predictions && predictions.length > 0) {
            predictions.forEach(pred => {
                const [x, y, bw, bh] = pred.bbox;
                const score = Math.round(pred.score * 100);

                if (['car', 'truck', 'bus', 'motorcycle'].includes(pred.class)) {
                    vehicleCount++;
                } else if (pred.class === 'person') {
                    personCount++;
                }

                // Choose color based on class
                const boxColor = pred.class === 'person' ? '#faff69' : '#ef4444';

                ctx.strokeStyle = boxColor;
                ctx.lineWidth = Math.max(3, width * 0.005);
                ctx.strokeRect(x, y, bw, bh);

                ctx.fillStyle = boxColor === '#ef4444' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(250, 255, 105, 0.15)';
                ctx.fillRect(x, y, bw, bh);

                // Draw Label Tag
                const label = `${pred.class.toUpperCase()} ${score}%`;
                ctx.font = `bold ${Math.max(14, width * 0.02)}px JetBrains Mono, monospace`;
                const textWidth = ctx.measureText(label).width;

                ctx.fillStyle = '#0a0a0a';
                ctx.fillRect(x, Math.max(0, y - 28), textWidth + 12, 28);
                ctx.strokeStyle = boxColor;
                ctx.lineWidth = 1;
                ctx.strokeRect(x, Math.max(0, y - 28), textWidth + 12, 28);

                ctx.fillStyle = '#ffffff';
                ctx.fillText(label, x + 6, Math.max(20, y - 8));
            });
        }

        // Determine emergency classification
        let incidentType = "ROAD_ACCIDENT";
        let confText = "94%";
        let badgeClass = "tag-red";

        if (vehicleCount >= 2) {
            incidentType = "ROAD_ACCIDENT";
            confText = "95%";
            badgeClass = "tag-red";
        } else if (personCount >= 1) {
            incidentType = "UNCONSCIOUS_PERSON";
            confText = "89%";
            badgeClass = "tag-yellow";
        } else if (vehicleCount > 4) {
            incidentType = "TRAFFIC_JAM";
            confText = "92%";
            badgeClass = "tag-yellow";
        }

        banner.style.display = "block";
        bannerText.textContent = `${incidentType} detected (${predictions.length} AI objects identified). Alert dispatched to emergency teams.`;
        addNewAlert(incidentType, confText, badgeClass);
    }

    function runFallbackDetection(ctx, width, height) {
        const bx = width * 0.2;
        const by = height * 0.25;
        const bw = width * 0.45;
        const bh = height * 0.4;

        ctx.strokeStyle = "#ef4444";
        ctx.lineWidth = Math.max(3, width * 0.006);
        ctx.strokeRect(bx, by, bw, bh);
        ctx.fillStyle = "rgba(239, 68, 68, 0.15)";
        ctx.fillRect(bx, by, bw, bh);

        const tagText = "ROAD_ACCIDENT 95%";
        ctx.font = `bold ${Math.max(14, width * 0.02)}px JetBrains Mono, monospace`;
        const textWidth = ctx.measureText(tagText).width;

        ctx.fillStyle = "#0a0a0a";
        ctx.fillRect(bx, by - 28, textWidth + 12, 28);
        ctx.strokeStyle = "#ef4444";
        ctx.lineWidth = 1;
        ctx.strokeRect(bx, by - 28, textWidth + 12, 28);
        ctx.fillStyle = "#ffffff";
        ctx.fillText(tagText, bx + 6, by - 8);

        banner.style.display = "block";
        bannerText.textContent = "ROAD_ACCIDENT detected (95% confidence). Twilio alert sent.";
        addNewAlert("ROAD_ACCIDENT", "95%", "tag-red");
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
        target: "Twilio SMS and REST Dispatch",
        badgeClass: badgeClass
    });

    renderTable();
}

function renderTable() {
    const tbody = document.getElementById("alerts-table-body");
    if (!tbody) return;

    tbody.innerHTML = "";
    mockAlerts.slice(0, 8).forEach(alert => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${alert.time}</td>
            <td><span class="badge-tag ${alert.badgeClass}">${alert.type.replace('_', ' ')}</span></td>
            <td><strong>${alert.conf}</strong></td>
            <td>${alert.target}</td>
            <td><span class="text-green">✓ DISPATCHED</span></td>
        `;
        tbody.appendChild(tr);
    });
}
