"""
Smart Emergency Street Light System - Web Dashboard
FastAPI server providing real-time status and alert history at http://localhost:8000
"""

import datetime
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn
import config
import alert as alert_module

app = FastAPI(title="Street Light SOS Dashboard")

# Shared state updated by main.py
system_state = {
    "running": False,
    "fps": 0.0,
    "camera_ok": False,
    "model_loaded": False,
    "total_alerts": 0,
    "started_at": None,
}


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Main dashboard HTML page."""
    alerts = alert_module.load_recent_alerts(20)
    alert_rows = ""
    for a in reversed(alerts):
        ts = a.get("timestamp", "")[:19].replace("T", " ")
        etype = a.get("type", "")
        conf = int(a.get("confidence", 0) * 100)
        desc = a.get("description", "")
        color_map = {
            "ROAD_ACCIDENT": "#ff4444",
            "TRAFFIC_JAM": "#ff8800",
            "UNCONSCIOUS_PERSON": "#cc00cc",
            "PHYSICAL_FIGHT": "#ff0066",
            "FIRE_SMOKE": "#ff2200",
            "KIDNAPPING_FORCED_MOVEMENT": "#aa0000",
        }
        color = color_map.get(etype, "#888")
        alert_rows += f"""
        <tr>
            <td>{ts}</td>
            <td><span class="badge" style="background:{color}">{etype.replace('_',' ')}</span></td>
            <td>{conf}%</td>
            <td>{desc}</td>
        </tr>"""

    uptime = ""
    if system_state["started_at"]:
        delta = datetime.datetime.now() - system_state["started_at"]
        uptime = str(delta).split(".")[0]

    status_color = "#00ff88" if system_state["camera_ok"] else "#ff4444"
    status_text = "ONLINE" if system_state["camera_ok"] else "OFFLINE"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="5">
    <title>Street Light SOS — Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', sans-serif;
            background: #0a0e1a;
            color: #e0e6f0;
            min-height: 100vh;
        }}
        header {{
            background: linear-gradient(135deg, #1a1f35, #0d1b2a);
            border-bottom: 2px solid #00aaff33;
            padding: 20px 40px;
            display: flex;
            align-items: center;
            gap: 16px;
        }}
        header h1 {{ font-size: 1.6rem; color: #00ccff; }}
        header p {{ font-size: 0.85rem; color: #8899aa; }}
        .status-dot {{
            width: 14px; height: 14px;
            border-radius: 50%;
            background: {status_color};
            box-shadow: 0 0 10px {status_color};
            animation: pulse 1.5s infinite;
        }}
        @keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:0.4}} }}
        .stats {{
            display: flex;
            gap: 20px;
            padding: 24px 40px;
            flex-wrap: wrap;
        }}
        .stat-card {{
            background: #131929;
            border: 1px solid #1e2d44;
            border-radius: 12px;
            padding: 20px 28px;
            min-width: 160px;
            flex: 1;
        }}
        .stat-card .label {{ font-size: 0.75rem; color: #6677aa; text-transform: uppercase; letter-spacing: 1px; }}
        .stat-card .value {{ font-size: 2rem; font-weight: 700; color: #00ccff; margin-top: 6px; }}
        .section {{ padding: 0 40px 40px; }}
        .section h2 {{ font-size: 1.1rem; color: #8899bb; margin-bottom: 14px; border-bottom: 1px solid #1e2d44; padding-bottom: 8px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ text-align: left; padding: 10px 14px; font-size: 0.75rem; color: #556677; text-transform: uppercase; background: #0d1422; }}
        td {{ padding: 12px 14px; border-bottom: 1px solid #131929; font-size: 0.88rem; }}
        tr:hover td {{ background: #131929; }}
        .badge {{
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            color: white;
        }}
        .no-alerts {{ text-align: center; padding: 40px; color: #445566; font-size: 0.9rem; }}
    </style>
</head>
<body>
    <header>
        <div class="status-dot"></div>
        <div>
            <h1>🚦 Street Light SOS — Live Dashboard</h1>
            <p>System Status: <strong style="color:{status_color}">{status_text}</strong>
               &nbsp;|&nbsp; Uptime: {uptime or 'N/A'}
               &nbsp;|&nbsp; Auto-refreshes every 5s
            </p>
        </div>
    </header>

    <div class="stats">
        <div class="stat-card">
            <div class="label">Camera</div>
            <div class="value" style="color:{'#00ff88' if system_state['camera_ok'] else '#ff4444'}">
                {'✓ OK' if system_state['camera_ok'] else '✗ OFF'}
            </div>
        </div>
        <div class="stat-card">
            <div class="label">FPS</div>
            <div class="value">{system_state['fps']:.1f}</div>
        </div>
        <div class="stat-card">
            <div class="label">Total Alerts</div>
            <div class="value">{system_state['total_alerts']}</div>
        </div>
        <div class="stat-card">
            <div class="label">AI Model</div>
            <div class="value" style="color:{'#00ff88' if system_state['model_loaded'] else '#ff4444'}">
                {'Loaded' if system_state['model_loaded'] else 'Loading'}
            </div>
        </div>
    </div>

    <div class="section">
        <h2>Recent Emergency Alerts</h2>
        {'<table><thead><tr><th>Time</th><th>Type</th><th>Confidence</th><th>Description</th></tr></thead><tbody>' + alert_rows + '</tbody></table>'
          if alerts else '<div class="no-alerts">No alerts recorded yet — system is watching 👁</div>'}
    </div>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.get("/alerts")
async def get_alerts():
    """Return all recent alerts as JSON."""
    return JSONResponse(content=alert_module.load_recent_alerts(100))


@app.get("/status")
async def get_status():
    """Return system health status as JSON."""
    return JSONResponse(content=system_state)


def start_server():
    """Start the dashboard server (called in a background thread from main.py)."""
    uvicorn.run(app, host=config.SERVER_HOST, port=config.SERVER_PORT, log_level="warning")
