from flask import Flask, render_template, request, jsonify
import time

app = Flask(__name__)

instances = {}
OFFLINE_TIMEOUT = 10

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/update_stats', methods=['POST'])
def update_stats():
    data = request.json
    username = data.get('username')
    
    if not username:
        return jsonify({'status': 'error', 'message': 'Missing username'}), 400

    current_time = time.time()
    current_money = data.get('money', 0)

    # Calculate hourly delta rate if instance already exists
    hourly_rate = "$0/h"
    rate_class = "stagnant"
    
    if username in instances:
        old_data = instances[username]
        time_diff = current_time - old_data['first_seen']
        money_diff = current_money - old_data['initial_money']
        
        if time_diff > 30:  # Calculate over a stable window
            hours = time_diff / 3600
            rate = money_diff / hours
            if rate > 0:
                hourly_rate = f"+${int(rate):,}/h"
                rate_class = "rising"
            elif rate < 0:
                hourly_rate = f"-${abs(int(rate)):,}/h"
                rate_class = "falling"
    else:
        # Register baseline for new instance
        instances[username] = {
            'initial_money': current_money,
            'first_seen': current_time
        }

    instances[username].update({
        'username': username,
        'level': data.get('level', 1),
        'fishing': data.get('fishing', 1),
        'stocker': data.get('stocker', 1),
        'stamina': data.get('stamina', 1),
        'farming': data.get('farming', 1),
        'money': current_money,
        'uptime_str': data.get('uptime_str', '0h 0m'),
        'reconnects': data.get('reconnects', 0),
        'hourly_rate': hourly_rate,
        'rate_class': rate_class,
        'last_ping': current_time
    })
    
    return jsonify({'status': 'success'}), 200

@app.route('/api/get_instances', methods=['GET'])
def get_instances():
    current_time = time.time()
    formatted_instances = []

    for username, data in list(instances.items()):
        is_online = (current_time - data['last_ping']) <= OFFLINE_TIMEOUT
        instance_info = dict(data)
        instance_info['is_online'] = is_online
        formatted_instances.append(instance_info)

    return jsonify(formatted_instances)

@app.route('/api/delete_instance', methods=['POST'])
def delete_instance():
    data = request.json
    username = data.get('username')
    if username in instances:
        del instances[username]
        return jsonify({'status': 'success', 'message': f'{username} removed'}), 200
    return jsonify({'status': 'error', 'message': 'Instance not found'}), 404

@app.route('/script.lua', methods=['GET'])
def serve_lua_script():
    lua_code = """
    task.spawn(function()
        local Players = game:GetService("Players")
        local localPlayer = Players.LocalPlayer
        while not localPlayer do task.wait(1) localPlayer = Players.LocalPlayer end

        local HttpService = game:GetService("HttpService")
        local PlayerGui = localPlayer:WaitForChild("PlayerGui")

        local reconnectFile = "blockspin_reconnects_" .. localPlayer.Name .. ".txt"
        local reconnects = 0
        pcall(function()
            if isfile and readfile and isfile(reconnectFile) then
                reconnects = tonumber(readfile(reconnectFile)) or 0
            end
            reconnects = reconnects + 1
            if writefile then writefile(reconnectFile, tostring(reconnects)) end
        end)

        local function extractNum(text)
            if not text then return 0 end
            local cleaned = string.gsub(text, "[^%d]", "")
            return tonumber(cleaned) or 0
        end

        local cachedBankTable = nil

        local function getAccurateMoney()
            local handMoney = 0
            local bankMoney = 0

            pcall(function()
                for _, gui in ipairs(PlayerGui:GetDescendants()) do
                    if gui:IsA("TextLabel") and string.find(gui.Text, "%$") and not string.find(gui.Text, "Balance") then
                        local val = extractNum(gui.Text)
                        if val > 0 then handMoney = val end
                    end
                end
            end)

            pcall(function()
                for _, gui in ipairs(PlayerGui:GetDescendants()) do
                    if gui:IsA("TextLabel") and string.find(gui.Text, "Bank Balance") then
                        bankMoney = extractNum(gui.Text)
                    end
                end
            end)

            if bankMoney == 0 then
                if not cachedBankTable then
                    pcall(function()
                        for _, obj in ipairs(getgc(true)) do
                            if typeof(obj) == "table" then
                                local b = rawget(obj, "Bank") or rawget(obj, "BankBalance") or rawget(obj, "bank")
                                if b and type(b) == "number" then
                                    cachedBankTable = obj
                                    break
                                end
                            end
                        end
                    end)
                end
                
                if cachedBankTable then
                    pcall(function()
                        bankMoney = tonumber(rawget(cachedBankTable, "Bank") or rawget(cachedBankTable, "BankBalance") or rawget(cachedBankTable, "bank")) or 0
                    end)
                end
            end

            return bankMoney + handMoney
        end

        local function getLevels()
            local totalLvl, fishing, stocker, stamina, farming = 1, 1, 1, 1, 1
            pcall(function()
                local skillsGui = PlayerGui:FindFirstChild("Skills")
                if skillsGui then
                    for _, gui in ipairs(skillsGui:GetDescendants()) do
                        if gui:IsA("TextLabel") then
                            local txt = string.lower(gui.Text)
                            local num = extractNum(gui.Text)
                            if num > 0 then
                                if string.find(txt, "total level") then totalLvl = num
                                elseif string.find(txt, "fishing") then fishing = num
                                elseif string.find(txt, "stocker") then stocker = num
                                elseif string.find(txt, "stamina") then stamina = num
                                elseif string.find(txt, "farming") then farming = num
                                end
                            end
                        end
                    end
                end
            end)
            return totalLvl, fishing, stocker, stamina, farming
        end

        local sessionStartTime = os.time()

        while task.wait(2) do
            pcall(function()
                local totalMoney = getAccurateMoney()
                local lvl, fish, stock, stam, farm = getLevels()

                local activeSeconds = os.time() - sessionStartTime
                local hrs = math.floor(activeSeconds / 3600)
                local mins = math.floor((activeSeconds % 3600) / 60)

                local payload = HttpService:JSONEncode({
                    username = localPlayer.Name,
                    level = lvl,
                    fishing = fish,
                    stocker = stock,
                    stamina = stam,
                    farming = farm,
                    money = totalMoney,
                    uptime_str = string.format("%dh %dm", hrs, mins),
                    reconnects = reconnects,
                    status_state = "Farming"
                })

                request({
                    Url = "http://192.168.1.243:5000/update_stats",
                    Method = "POST",
                    Headers = { ["Content-Type"] = "application/json" },
                    Body = payload
                })
            end)
        end
    end)
    """
    return lua_code, 200, {'Content-Type': 'text/plain'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)