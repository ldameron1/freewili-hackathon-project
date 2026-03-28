import os
from flask import Flask, jsonify, send_from_directory

def create_app(engine=None):
    app = Flask(__name__)
    
    # Simple HTML template embedded for hackathon speed avoiding extra files
    TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Mafia Moderator</title>
    <style>
        body { background: #121212; color: #fff; font-family: monospace; margin: 0; padding: 20px;}
        .grid { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }
        .panel { background: #1e1e1e; padding: 15px; border-radius: 8px; }
        h2 { border-bottom: 1px solid #333; padding-bottom: 10px;}
        .player { padding: 10px; margin: 5px 0; background: #2c2c2c; border-radius: 4px; display: flex; justify-content: space-between;}
        .dead { opacity: 0.5; text-decoration: line-through; }
        .log-entry { font-size: 0.9em; margin: 5px 0; padding: 5px; border-left: 3px solid #555;}
        .log-public { border-left-color: #4CAF50;}
        .log-private { border-left-color: #f44336; color: #ff9800;}
        #logs { max-height: 80vh; overflow-y: auto; }
    </style>
</head>
<body>
    <h1>Mafia Moderator Panel - <span id="phase">LOBBY</span></h1>
    <div class="grid">
        <div class="panel">
            <h2>Game Log</h2>
            <div id="logs"></div>
        </div>
        <div class="panel">
            <h2>Players</h2>
            <div id="players"></div>
            <hr/>
            <h3>State</h3>
            <pre id="state-raw"></pre>
        </div>
    </div>
    <script>
        async function fetchState() {
            const res = await fetch('/api/state');
            const data = await res.json();
            
            document.getElementById('phase').innerText = data.phase.toUpperCase() + (data.turn ? ' (Turn ' + data.turn + ')' : '');
            
            document.getElementById('players').innerHTML = data.players.map(p => 
                `<div class="player ${p.alive ? '' : 'dead'}">
                    <span>${p.name} ${p.is_ai ? '🤖' : '👤'}</span>
                    <span>${p.role}</span>
                </div>`
            ).join('');
            
            document.getElementById('state-raw').innerText = JSON.stringify(data.votes, null, 2);
        }

        async function fetchLogs() {
            const res = await fetch('/api/logs');
            const logs = await res.json();
            
            const html = logs.map(l => 
                `<div class="log-entry ${l.public ? 'log-public' : 'log-private'}">
                    <strong>[${l.phase}]</strong> ${l.message}
                </div>`
            ).join('');
            
            const logsDiv = document.getElementById('logs');
            logsDiv.innerHTML = html;
            // logsDiv.scrollTop = logsDiv.scrollHeight;
        }

        setInterval(fetchState, 1000);
        setInterval(fetchLogs, 1000);
        fetchState();
        fetchLogs();
    </script>
</body>
</html>
"""

    @app.route('/')
    def index():
        return TEMPLATE

    @app.route('/api/state')
    def api_state():
        if not engine: return jsonify({"error": "No engine attached"})
        return jsonify(engine.state.to_dict())

    @app.route('/api/logs')
    def api_logs():
        if not engine: return jsonify([])
        return jsonify([l.to_dict() for l in engine.state.game_log])

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(port=5000)
