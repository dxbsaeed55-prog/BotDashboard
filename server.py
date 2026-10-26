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
        # Update bot info with a fresh timestamp
        active_bots[username] = {
            "username": username,
            "level": data.get("level", "N/A"),
            "money": data.get("money", "N/A"),
            "uptime": data.get("uptime", "N/A"),
            "last_seen": time.time()
        }
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/get_instances', methods=['GET'])
def get_instances():
    current_time = time.time()
    # Remove bots that haven't sent stats in the last 15 seconds (disconnected/crashed)
    offline_bots = [uname for uname, info in active_bots.items() if current_time - info['last_seen'] > 15]
    for uname in offline_bots:
        del active_bots[uname]
        
    return jsonify(list(active_bots.values()))

@app.route('/script.lua')
def script():
    # Automatically points bots to your live Render domain
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
                        level = "Active", 
                        money = "Tracking", 
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