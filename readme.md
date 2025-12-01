# 🛰️ Geofence Event Processing Challenge

## 📘 Overview
This project implements a **Geofence Event Processing Service** for a taxi company that tracks vehicles as they move across predefined geographic zones.  
The system receives **real-time GPS coordinates**, determines when vehicles **enter or exit** specific areas, and provides APIs to query the **current zone status** for each vehicle.

---

## 🧠 Problem Understanding

### Scenario
- Taxis continuously send their GPS coordinates to a backend service.
- The backend determines if a taxi has entered or exited a **geofence zone**.
- Zones are **circular** regions (defined by latitude, longitude, and radius).
- The service must expose APIs for:
  - Receiving location updates.
  - Reporting zone entry/exit events.
  - Querying the current zone of a specific vehicle.

---

## 🚀 Key Features

| Feature | Description |
|----------|--------------|
| **POST /location** | Receives GPS updates and detects geofence enter/exit transitions |
| **GET /status/{vehicleId}** | Returns the current zone and last known location for a vehicle |
| **GET /events** | Returns recent enter/exit events (optionally filtered by vehicleId) |
| **GET /zones** | Returns all configured geofence zones |
| **GET /health** | Health-check endpoint for monitoring |

---

## 🏗️ Tech Stack

| Component | Technology |
|------------|-------------|
| **Language** | Python 3.10+ |
| **Framework** | FastAPI |
| **Web Server** | Uvicorn |
| **Data Storage** | In-memory (dicts/lists) |
| **Logging** | Python `logging` module |
| **Validation** | Pydantic models |

---

## 📂 Project Structure

geofence-service/
├── main.py # Main FastAPI service code
├── requirements.txt # Python dependencies
└── README.md # Documentation (this file)

yaml
Copy code

---

## ⚙️ Setup Instructions

### 1. Clone Repository
```bash
git clone https://github.com/RamShekade/Geofence-Event-Tracker
cd geofence-service
2. Create Virtual Environment (optional)
bash
Copy code
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
3. Install Dependencies
bash
Copy code
pip install -r requirements.txt
4. Run the Application
bash
Copy code
uvicorn main:app --reload
By default, the service runs on:

cpp
Copy code
http://127.0.0.1:8000
You can access interactive docs at:

Swagger UI → http://127.0.0.1:8000/docs

ReDoc → http://127.0.0.1:8000/redoc

🌐 API Endpoints
🩺 1. Health Check
GET /health

Response

json
Copy code
{
  "status": "ok",
  "timestamp": "2025-12-01T14:23:45.123Z"
}
📍 2. Receive Location Update
POST /location

Request Body

json
Copy code
{
  "vehicleId": "TX123",
  "latitude": 12.9716,
  "longitude": 77.5946,
  "timestamp": "2025-12-01T10:30:00Z"
}
Response

json
Copy code
{
  "status": {
    "vehicleId": "TX123",
    "currentZone": "downtown",
    "lastLatitude": 12.9716,
    "lastLongitude": 77.5946,
    "lastUpdated": "2025-12-01T10:30:00Z"
  },
  "generatedEvents": [
    {
      "eventType": "enter",
      "vehicleId": "TX123",
      "zoneId": "downtown",
      "timestamp": "2025-12-01T10:30:00Z",
      "fromZone": null,
      "toZone": "downtown"
    }
  ]
}
The service automatically detects if the vehicle has entered, exited, or switched between zones.

🚗 3. Get Vehicle Status
GET /status/{vehicleId}

Example

bash
Copy code
GET /status/TX123
Response

json
Copy code
{
  "vehicleId": "TX123",
  "currentZone": "downtown",
  "lastLatitude": 12.9716,
  "lastLongitude": 77.5946,
  "lastUpdated": "2025-12-01T10:30:00Z"
}
📜 4. List Zone Events
GET /events?vehicleId=TX123&limit=10

Response

json
Copy code
[
  {
    "eventType": "enter",
    "vehicleId": "TX123",
    "zoneId": "downtown",
    "timestamp": "2025-12-01T10:30:00Z",
    "fromZone": null,
    "toZone": "downtown"
  }
]
🗺️ 5. List All Zones
GET /zones

Response

json
Copy code
[
  {
    "id": "airport",
    "center_lat": 12.9611,
    "center_lng": 77.6387,
    "radius_m": 3000.0
  },
  {
    "id": "downtown",
    "center_lat": 12.9716,
    "center_lng": 77.5946,
    "radius_m": 5000.0
  },
  {
    "id": "suburb",
    "center_lat": 12.9956,
    "center_lng": 77.7,
    "radius_m": 4000.0
  }
]

```
## 🧭 How It Works

### 🗺️ Geofence Representation
Each zone is defined as a **circle** using:
- `center_lat`, `center_lng` → coordinates  
- `radius_m` → radius in meters  

A vehicle is considered inside a zone if its distance from the center is less than or equal to the radius.

---

### 📏 Distance Calculation
Uses the **Haversine formula** to calculate distance between the vehicle and zone center.

---

### 🧮 State Tracking
The service keeps each vehicle’s **last known location and zone** in memory.

---

### 🚦 Event Detection
When a new location arrives:
- If the vehicle enters a zone → emit **enter** event  
- If it leaves a zone → emit **exit** event  
- If it moves between zones → emit **exit + enter**

All events are logged and returned in the API response.

---

## 🧰 Error Handling & Logging
- Validates all inputs using **Pydantic**
- Returns `400` for invalid data and `404` for unknown vehicles
- Logs all updates and transitions with timestamps

---

## ⚡ Performance & Scalability
| Aspect | Current | Future |
|---------|----------|---------|
| Storage | In-memory | Redis / Database |
| Events | Local list | Kafka / Queue |
| Monitoring | Logs | Prometheus / Grafana |

---

## 🧪 Example Commands

```bash
# Send location update
curl -X POST http://127.0.0.1:8000/location \
  -H "Content-Type: application/json" \
  -d '{"vehicleId":"TX001","latitude":12.9715,"longitude":77.5947}'

# Get vehicle status
curl http://127.0.0.1:8000/status/TX001

```

🔮 Future Enhancements

Polygon-based zones

Persistent storage

Real-time event streaming

Authentication and rate limiting
