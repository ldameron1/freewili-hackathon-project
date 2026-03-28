from flask import Flask, jsonify, render_template, send_from_directory

def create_app(engine=None):
    # Specify the template and static folders relative to this file
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')

    @app.route('/')
    def index():
        return render_template('index.html')

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
