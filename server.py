try:
    import socketio
    import eventlet
except ImportError:
    print("\n[!] ERROR: Missing dependencies for the server.")
    print("Please run: pip install python-socketio eventlet\n")
    exit(1)

import random
import string
import time

sio = socketio.Server(cors_allowed_origins='*')
app = socketio.WSGIApp(sio)

rooms = {} # room_id -> {p1: sid, p2: sid, state: 'waiting'|'playing'}

def generate_room_id():
    return ''.join(random.choices(string.ascii_uppercase, k=4))

@sio.event
def connect(sid, environ):
    print(f"Connect: {sid}")

@sio.event
def disconnect(sid):
    print(f"Disconnect: {sid}")
    # Cleanup rooms
    for rid, rdata in list(rooms.items()):
        if sid == rdata['p1'] or sid == rdata['p2']:
            print(f"Closing room {rid}")
            sio.emit('room_closed', room=rid)
            del rooms[rid]

@sio.event
def create_room(sid):
    rid = generate_room_id()
    while rid in rooms: rid = generate_room_id()
    rooms[rid] = {'p1': sid, 'p2': None, 'state': 'waiting'}
    sio.enter_room(sid, rid)
    print(f"Room Created: {rid}")
    return rid

@sio.event
def join_room(sid, rid):
    rid = rid.upper()
    if rid in rooms and rooms[rid]['p2'] is None:
        rooms[rid]['p2'] = sid
        rooms[rid]['state'] = 'playing'
        sio.enter_room(sid, rid)
        print(f"Room Joined: {rid}")
        sio.emit('start_game', {'p1': rooms[rid]['p1'], 'p2': sid}, room=rid)
        return True
    return False

@sio.event
def send_input(sid, data):
    # Relay input from client to room
    rid = data.get('room')
    if rid in rooms:
        sio.emit('relay_input', data, room=rid, skip_sid=sid)

@sio.event
def update_state(sid, data):
    # Authority (P1) sends the full state to P2
    rid = data.get('room')
    if rid in rooms:
        sio.emit('state_sync', data, room=rid, skip_sid=sid)

import socket

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)) # Doesn't actually connect
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

if __name__ == '__main__':
    local_ip = get_local_ip()
    print("="*40)
    print(" SUB TROUBLE - PRIVATE SERVER ")
    print("="*40)
    print(f" SERVER IP: {local_ip} ")
    print(f" Port: 5000")
    print("="*40)
    print("Players should enter the SERVER IP above into their games.")
    print("Waiting for connections...")
    eventlet.wsgi.server(eventlet.listen(('', 5000)), app)
