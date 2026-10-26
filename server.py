import os
from flask import Flask, render_template, request, jsonify
import time

app = Flask(__name__)

# Dictionary to store active bot telemetry data in memory
active_bots = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/update_stats', methods=['POST'])
def update_stats():
    try:
        data = request.json
        if not data or 'username' not in data:
            return jsonify({"status": "error", "message": "Invalid data"}), 400
        
        username = data['username']
        
        # Format uptime nicely into a readable string (e.g., "1h 24m" or "45s")
        raw_uptime = int(data.get("uptime", 0))
        hours = raw_uptime // 3600
        minutes = (raw_uptime % 3600) // 60
        seconds = raw_uptime % 60
        if hours > 0:
            uptime_str = f"{hours}h {minutes}m"
        elif minutes > 0:
            uptime_str = f"{minutes}m {seconds}s"
        else:
            uptime_str = f"{seconds}s"

        # Map incoming data directly to the keys your index.html expects
        active_bots[username] = {
            "username": username,
            "level": data.get("level", "1"),
            "level": data.get("level", "1"),
            "money": data.get("money", 0),
            "hourly_rate": data.get("hourly_rate", "$0/hr"),
            "rate_class": data.get("rate_class", "stagnant"),
            "fishing": data.get("fishing", "0"),
            "stocker": data.get("stocker", "0"),
            "stamina": data.get("stamina", "0"),
            "farming": data.get("farming", "0"),
            "reconnects": data.get("reconnects", 0),
            "uptime_str": uptime_str,
            "is_online": True,
            "last_seen": time.time()
        }
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/get_instances', methods=['GET'])
def get_instances():
    current_time = time.time()
    # Mark bots offline or remove them if they haven't pinged in 15 seconds
    for uname, info in list(active_bots.items()):
        if current_time - info['last_seen'] > 15:
            info['is_online'] = False
        if current_time - info['last_seen'] > 30: # Delete completely after 30s
            del active_bots[uname]
        
    return jsonify(list(active_bots.values()))

@app.route('/api/delete_instance', methods=['POST'])
def delete_instance():
    try:
        data = request.json
        username = data.get('username')
        if username in active_bots:
            del active_bots[username]
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/script.lua')
def script():
    lua_code = """
    task.spawn(function()
        while true do
            pcall(function()
                request({
                    Url = "https://botdashboard-z4we.onrender.com/update_stats",
                    Method = "POST",
                    Headers = {
                        ["Content-Type"] = "application/json"
                    },
                    Body = game:GetService("HttpService"):JSONEncode({
                        username = game.Players.LocalPlayer.Name,
                        level = "15", 
                        money = 12500, 
                        hourly_rate = "$2,400/hr",
                        rate_class = "rising",
                        fishing = "12",
                        stocker = "8",
                        stamina = "45",
                        farming = "3",
                        reconnects = 0,
                        uptime = math.floor(workspace.DistributedGameTime)
                    })
                })
            end)
            task.wait(5)
        end
    end)
    """
    return lua_code, 200, {'Content-Type': 'text/plain'}

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)