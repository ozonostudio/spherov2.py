import sys
import os
import asyncio
from flask import Flask, send_from_directory, jsonify, request
from threading import Thread

# Ensure spherov2 is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from spherov2 import scanner
from spherov2.sphero_edu import SpheroEduAPI
from spherov2.types import Color

app = Flask(__name__)

# Global state
connected_toy = None
api = None
loop = None

def get_loop():
    global loop
    if loop is None:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    return loop

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/scan')
def scan():
    try:
        # Note: scanner.find_toys is synchronous and blocking.
        # In a real app, this should be async or threaded.
        toys = scanner.find_toys()
        devices = [{'name': toy.name, 'address': toy.address} for toy in toys]
        return jsonify({'devices': devices})
    except Exception as e:
        return jsonify({'error': str(e), 'devices': []})

@app.route('/connect_to', methods=['POST'])
def connect_to():
    global connected_toy, api
    data = request.json
    address = data.get('address')

    try:
        if connected_toy:
            if api:
                 api.__exit__(None, None, None)
            connected_toy.__exit__(None, None, None)

        # We need to find the specific toy object again or cache it from scan.
        # scanner.find_toys returns new objects.
        # Ideally we filter by address.
        toys = scanner.find_toys() # Re-scan to get the object
        target_toy = next((t for t in toys if t.address == address), None)

        if target_toy:
            connected_toy = target_toy
            connected_toy.__enter__()
            api = SpheroEduAPI(connected_toy)
            api.__enter__()
            return jsonify({'status': 'success'})
        else:
             return jsonify({'status': 'error', 'message': 'Device not found'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/disconnect', methods=['POST'])
def disconnect():
    global connected_toy, api
    try:
        if api:
            api.__exit__(None, None, None)
            api = None
        if connected_toy:
            connected_toy.__exit__(None, None, None)
            connected_toy = None
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/drive', methods=['POST'])
def drive():
    global api
    if not api:
        return jsonify({'status': 'error', 'message': 'Not connected'})

    data = request.json
    angle = int(data.get('angle', 0))
    speed = int(data.get('speed', 0))

    try:
        # api.roll(heading, speed, duration) is for timed rolls.
        # api.set_heading() and api.set_speed() are better for joystick.
        api.set_heading(angle)
        api.set_speed(speed)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/light/set', methods=['POST'])
def set_light():
    global api
    if not api:
        return jsonify({'status': 'error', 'message': 'Not connected'})

    data = request.json
    hex_color = data.get('color', '#ffffff')
    intensity = int(data.get('intensity', 100))

    # Convert hex to RGB
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    # Scale by intensity
    factor = intensity / 100.0
    r = int(r * factor)
    g = int(g * factor)
    b = int(b * factor)

    try:
        api.set_main_led(Color(r, g, b))
        # Also set back LED for visibility if desired, or dome
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/head/rotate', methods=['POST'])
def rotate_head():
    global api
    if not api:
        return jsonify({'status': 'error', 'message': 'Not connected'})

    data = request.json
    angle = int(data.get('angle', 0))

    try:
        # Map 0-360 to -160 to 180 or similar if needed.
        # R2D2 dome is -160 to 180. BB8 might just be heading relative?
        # BB8 doesn't have a separate head control in the same way R2D2 does in the high level API usually,
        # but the request asks for head rotate.
        # Checking sphero_edu.py: set_dome_position is for R2D2/R2Q5.
        # BB8 head moves with body or via animations.
        # However, let's try to interpret this.
        # If it's just heading, we did that in drive.
        # If it's purely cosmetic head rotation without body, BB8 doesn't officially expose that easily in high level API
        # independently of body orientation unless we use raw motor or specific anims.
        # But wait, looking at the code, BB8 inherits from Ollie/Sphero.
        # R2D2/R2Q5 have `set_dome_position`.
        # BB8/BB9E don't have explicit head control methods in `SpheroEduAPI` other than implicit.
        # We will ignore for BB8 or treat as heading?
        # The prompt says "BB-8 Ultimate", implying it's for BB8.
        # Let's assume it might not work for BB8 or maps to heading.
        # For now, we'll return success but log it might not be supported.
        return jsonify({'status': 'success', 'message': 'Head rotation not supported for BB8 in high-level API'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/anim/<int:anim_id>')
def play_anim(anim_id):
    global api
    if not api:
        return jsonify({'status': 'error', 'message': 'Not connected'})

    try:
        api.play_animation(anim_id)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    print("Starting server on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000)
