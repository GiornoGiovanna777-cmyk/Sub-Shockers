"""
SUB TROUBLE — Game Client
==========================
Requirements:
    pip install pygame python-socketio[client] websocket-client

Run:
    python game.py

HOW MULTIPLAYER WORKS
---------------------
  Host   → runs server.py, shares their LAN IP (shown in server console)
  Both   → run game.py, enter the server IP in the lobby
  Host   → Create Room (public or private)
  Guest  → Join Room (enter the 4-letter code)

  The HOST (P1) runs all physics locally and streams state to P2.
  P2 sends inputs to the server, which relays them to P1.
  This keeps gameplay perfectly in sync on one machine as authority.

LOCAL 2-PLAYER
--------------
  Just click "Play Local" — no server needed. Both players share the keyboard.
"""

import pygame
import sys
import math
import time
import random
import json
import threading
NET_AVAILABLE = False
try:
    import socketio
    import socket
    sio = socketio.Client()
    NET_AVAILABLE = True
except ImportError:
    sio = None
    NET_AVAILABLE = False
except Exception:
    sio = None
    NET_AVAILABLE = False


# ── Colors ──────────────────────────────────────────────────────────────────
ABYSS      = (1,   8,  16)
DEEP       = (4,  20,  40)
WALL_DARK  = (6,  22,  38)
WALL_MID   = (10, 37,  60)
WALL_GLOW  = (0,  90,  160)
BIOLUM     = (0,  255, 231)
P1_COLOR   = (0,  255, 231)
P2_COLOR   = (255, 60,  100)
WHITE      = (255, 255, 255)
SAND       = (140, 110, 60)
GRAY       = (80,  80,  80)
DIM        = (40,  40,  50)

WIN_SCORE     = 11
SUB_RADIUS    = 12
WALL_THICK    = 3
MAX_BULLETS   = 7
RELOAD_FRAMES = 600
SUB_SPEED     = 3.2


pygame.init()

WIDTH  = 800
HEIGHT = 800

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("SUB SHOCKERS — Deep Sea Arena")
clock = pygame.time.Clock()

#Networking State 
net_room = None
net_is_host = False
net_ready = False
net_p2_keys = {}
net_remote_state = None

# ── Settings & State ────────────────────────────────────────────────────────
settings = {
    "music_volume": 0.4,
    "muted": False
}

@sio.on('start_game')
def on_start(data):
    global net_ready
    net_ready = True

@sio.on('relay_input')
def on_input(data):
    global net_p2_keys
    net_p2_keys = data.get('keys', {})

@sio.on('state_sync')
def on_sync(data):
    global net_remote_state
    net_remote_state = data.get('state')

@sio.on('room_closed')
def on_close(data):
    global net_ready
    net_ready = False


font_big   = pygame.font.SysFont("consolas", 36, bold=True)
font_med   = pygame.font.SysFont("consolas", 22, bold=True)
font_small = pygame.font.SysFont("consolas", 14)
font_tiny  = pygame.font.SysFont("consolas", 12)

# ── Sound Effects ───────────────────────────────────────────────────────────
pygame.mixer.init()
sounds = {}
current_track = None

def load_sound(name, filename):
    try:
        sounds[name] = pygame.mixer.Sound(filename)
    except:
        sounds[name] = None

# To use your own piano sounds: 
# 1. Save your piano recording as a .wav file in the same folder as this script.
# 2. Uncomment the lines below and use your filenames.
load_sound('shoot',    'piano_shoot.wav')
load_sound('explode',  'piano_boom.wav')
load_sound('powerup',  'piano_sparkle.wav')
load_sound('music_game',  'sound.wav')
load_sound('music_intro', 'sound2.wav')
load_sound('music_menu',  'HomePage.wav')

def update_volumes():
    v = 0 if settings["muted"] else settings["music_volume"]
    if 'music_game' in sounds and sounds['music_game']:
        sounds['music_game'].set_volume(v)
    if 'music_intro' in sounds and sounds['music_intro']:
        sounds['music_intro'].set_volume(v)
    if 'music_menu' in sounds and sounds['music_menu']:
        sounds['music_menu'].set_volume(v)

update_volumes()

def play_sound(name):
    if name in sounds and sounds[name]:
        sounds[name].play()

def play_music(name, loops=-1, fade_ms=1000):
    global current_track
    if name == current_track: return # Already playing
    
    if name in sounds and sounds[name]:
        # Stop ALL possible music tracks to prevent layering
        for track in ['music_game', 'music_intro', 'music_menu']:
            if track in sounds and sounds[track]:
                sounds[track].stop()
        sounds[name].play(loops=loops, fade_ms=fade_ms)
        current_track = name

def stop_sound(name, fade_ms=1000):
    global current_track
    if name in sounds and sounds[name]:
        sounds[name].fadeout(fade_ms)
        if name == current_track:
            current_track = None


# ── Colors moved to top ──


# ── Common UI Helpers ───────────────────────────────────────────────────────
def draw_gear(surf, x, y, size, color=GRAY):
    # Simple gear icon using polygons
    points = []
    num_teeth = 8
    inner_r = size * 0.5
    outer_r = size * 0.8
    for i in range(num_teeth * 2):
        angle = i * (math.pi / num_teeth)
        r = outer_r if i % 2 == 0 else inner_r
        points.append((x + math.cos(angle) * r, y + math.sin(angle) * r))
    pygame.draw.polygon(surf, color, points)
    pygame.draw.circle(surf, ABYSS, (int(x), int(y)), int(size * 0.3))
    pygame.draw.circle(surf, color, (int(x), int(y)), int(size * 0.15))

def draw_front_sub(surf, x, y, size, color):
    # Front-facing Submarine: Black body with a single blue window
    body_color = (10, 10, 15) # Deep black
    # Main body oval
    pygame.draw.ellipse(surf, body_color, (x - size, y - size*0.7, size*2, size*1.4))
    # Conning tower
    pygame.draw.rect(surf, body_color, (x - size*0.2, y - size*1.1, size*0.4, size*0.5))
    # Periscope
    pygame.draw.line(surf, body_color, (x, y - size*1.1), (x, y - size*1.4), 3)
    # Single Glowing Blue Window (centered)
    window_color = (0, 150, 255) # Deep blue
    win_r = int(size*0.35)
    pygame.draw.circle(surf, window_color, (int(x), int(y - size*0.1)), win_r)
    # Glistening effect on window
    draw_circle_alpha(surf, (200, 255, 255), (int(x - win_r*0.3), int(y - size*0.1 - win_r*0.3)), int(win_r*0.3), 150)
    # Outer blue glow
    draw_circle_alpha(surf, (0, 100, 255), (int(x), int(y - size*0.1)), win_r + 5, 60)

PAD         = 15
PLAY_LEFT   = PAD
PLAY_RIGHT  = WIDTH  - PAD
PLAY_TOP    = PAD + 44
PLAY_BOTTOM = HEIGHT - PAD

# ── Maps ────────────────────────────────────────────────────────────────────
current_maze = []
maze_grid = None
maze_cols, maze_rows = 10, 10

def generate_maze(cols, rows):
    width = PLAY_RIGHT - PLAY_LEFT
    height = PLAY_BOTTOM - PLAY_TOP
    cw = width / cols
    ch = height / rows

    grid = [[{'N':True, 'S':True, 'E':True, 'W':True, 'visited':False} for _ in range(cols)] for _ in range(rows)]
    stack = [(0,0)]
    grid[0][0]['visited'] = True

    while stack:
        cy, cx = stack[-1]
        neighbors = []
        if cy > 0 and not grid[cy-1][cx]['visited']: neighbors.append(('N', cy-1, cx, 'S'))
        if cy < rows-1 and not grid[cy+1][cx]['visited']: neighbors.append(('S', cy+1, cx, 'N'))
        if cx > 0 and not grid[cy][cx-1]['visited']: neighbors.append(('W', cy, cx-1, 'E'))
        if cx < cols-1 and not grid[cy][cx+1]['visited']: neighbors.append(('E', cy, cx+1, 'W'))

        if neighbors:
            dir, ny, nx, opp = random.choice(neighbors)
            grid[cy][cx][dir] = False
            grid[ny][nx][opp] = False
            grid[ny][nx]['visited'] = True
            stack.append((ny, nx))
        else:
            stack.pop()
    
    # Knock down a few extra walls for loops
    for _ in range(int(cols * rows * 0.15)):
        ry = random.randint(1, rows-2)
        rx = random.randint(1, cols-2)
        d = random.choice(['N','S','E','W'])
        grid[ry][rx][d] = False
        if d == 'N': grid[ry-1][rx]['S'] = False
        if d == 'S': grid[ry+1][rx]['N'] = False
        if d == 'E': grid[ry][rx+1]['W'] = False
        if d == 'W': grid[ry][rx-1]['E'] = False

    global maze_grid
    maze_grid = grid
    
    segs = []
    for y in range(1, rows):
        for x in range(cols):
            if grid[y][x]['N']:
                px1 = PLAY_LEFT + x * cw
                px2 = px1 + cw
                py = PLAY_TOP + y * ch
                segs.append((px1, py, px2, py))
    for y in range(rows):
        for x in range(1, cols):
            if grid[y][x]['W']:
                px = PLAY_LEFT + x * cw
                py1 = PLAY_TOP + y * ch
                py2 = py1 + ch
                segs.append((px, py1, px, py2))
    return segs

def get_maze():
    if not current_maze:
        next_map()
    return current_maze

def next_map():
    global current_maze, maze_grid
    current_maze = generate_maze(10, 10)
    try:
        reset_walls_cache()
    except NameError:
        pass

def get_cell_from_pos(x, y):
    cols, rows = maze_cols, maze_rows
    width = PLAY_RIGHT - PLAY_LEFT
    height = PLAY_BOTTOM - PLAY_TOP
    cw, ch = width / cols, height / rows
    cx = int((x - PLAY_LEFT) / cw)
    cy = int((y - PLAY_TOP) / ch)
    return clamp(cx, 0, cols-1), clamp(cy, 0, rows-1)

def get_pos_from_cell(cx, cy):
    cols, rows = maze_cols, maze_rows
    width = PLAY_RIGHT - PLAY_LEFT
    height = PLAY_BOTTOM - PLAY_TOP
    cw, ch = width / cols, height / rows
    return PLAY_LEFT + cx * cw + cw/2, PLAY_TOP + cy * ch + ch/2

def a_star(start_cell, goal_cell):
    if not maze_grid or start_cell == goal_cell: return []
    import heapq
    q = [(0, start_cell)]
    came_from = {start_cell: None}
    cost_so_far = {start_cell: 0}
    
    while q:
        _, current = heapq.heappop(q)
        if current == goal_cell: break
        
        cx, cy = current
        neighbors = []
        c = maze_grid[cy][cx]
        if not c['N'] and cy > 0: neighbors.append((cx, cy-1))
        if not c['S'] and cy < maze_rows-1: neighbors.append((cx, cy+1))
        if not c['E'] and cx < maze_cols-1: neighbors.append((cx+1, cy))
        if not c['W'] and cx > 0: neighbors.append((cx-1, cy))
        
        for n in neighbors:
            new_cost = cost_so_far[current] + 1
            if n not in cost_so_far or new_cost < cost_so_far[n]:
                cost_so_far[n] = new_cost
                priority = new_cost + abs(n[0]-goal_cell[0]) + abs(n[1]-goal_cell[1])
                heapq.heappush(q, (priority, n))
                came_from[n] = current
                
    if goal_cell not in came_from: return []
    path = []
    curr = goal_cell
    while curr != start_cell:
        path.append(curr)
        curr = came_from[curr]
    path.reverse()
    return path

def can_see(x1, y1, x2, y2):
    # Raycast check against all wall segments
    dx, dy = x2 - x1, y2 - y1
    dist = math.hypot(dx, dy)
    if dist < 5: return True
    ux, uy = dx/dist, dy/dist
    
    for ax, ay, bx, by in current_maze:
        # Check if the line (x1,y1) -> (x2,y2) intersects wall (ax,ay) -> (bx,by)
        # Using a simplified intersection
        hit = ray_vs_seg(x1, y1, ux, uy, ax, ay, bx, by)
        if hit and hit[0] < dist:
            return False
    return True


# ── Geometry ────────────────────────────────────────────────────────────────
def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def lerp_color(c1, c2, t):
    return tuple(int(c1[i]+(c2[i]-c1[i])*t) for i in range(3))

def closest_point_on_seg(px,py,ax,ay,bx,by):
    dx,dy=bx-ax,by-ay
    l2=dx*dx+dy*dy
    if l2==0: return ax,ay
    t=clamp(((px-ax)*dx+(py-ay)*dy)/l2,0,1)
    return ax+t*dx,ay+t*dy

def push_out_of_wall(cx,cy,radius,ax,ay,bx,by,thick):
    px,py=closest_point_on_seg(cx,cy,ax,ay,bx,by)
    dx,dy=cx-px,cy-py
    dist=math.hypot(dx,dy)
    needed=radius+thick
    if 0.001<dist<needed:
        nx,ny=dx/dist,dy/dist
        return cx+nx*(needed-dist),cy+ny*(needed-dist)
    elif dist<=0.001:
        return cx,cy-needed
    return None

def ray_vs_seg(ox,oy,dx,dy,ax,ay,bx,by):
    sdx,sdy=bx-ax,by-ay
    denom=dx*sdy-dy*sdx
    if abs(denom)<1e-9: return None
    t=((ax-ox)*sdy-(ay-oy)*sdx)/denom
    u=((ax-ox)*dy-(ay-oy)*dx)/denom
    if 0.0001<=t<=1 and 0<=u<=1:
        wl=math.hypot(sdx,sdy)
        if wl<1e-9: return None
        wnx,wny=-sdy/wl,sdx/wl
        if wnx*dx+wny*dy>0: wnx,wny=-wnx,-wny
        return t,wnx,wny
    return None

def draw_circle_alpha(surf,color,pos,radius,alpha):
    s=pygame.Surface((radius*2,radius*2),pygame.SRCALPHA)
    pygame.draw.circle(s,(*color,alpha),(radius,radius),radius)
    surf.blit(s,(pos[0]-radius,pos[1]-radius))


# ── Particles / Ripples ──────────────────────────────────────────────────────
class Particle:
    def __init__(self,x,y,color,ptype='spark'):
        self.x,self.y=x,y
        a=random.uniform(0,math.pi*2); sp=random.uniform(1,5)
        self.vx,self.vy=math.cos(a)*sp,math.sin(a)*sp
        self.color=color; self.life=1.0
        self.decay=random.uniform(0.02,0.045)
        self.size=random.uniform(2,6); self.ptype=ptype
    def update(self):
        self.x+=self.vx; self.y+=self.vy
        self.vy-=0.04;   self.vx*=0.97
        self.life-=self.decay
    def draw(self,surf):
        if self.life<=0: return
        r=int(self.size*self.life)
        if r<1: return
        alpha=int(self.life*220)
        s=pygame.Surface((r*2+2,r*2+2),pygame.SRCALPHA)
        if self.ptype=='bubble':
            pygame.draw.circle(s,(*self.color,alpha),(r+1,r+1),r,1)
        else:
            pygame.draw.circle(s,(*self.color,alpha),(r+1,r+1),r)
        surf.blit(s,(int(self.x)-r-1,int(self.y)-r-1))

class Ripple:
    def __init__(self,x,y,color):
        self.x,self.y=x,y; self.r,self.maxr=4,50
        self.life=1.0; self.color=color
    def update(self):
        self.r+=(self.maxr-self.r)*0.1; self.life-=0.03
    def draw(self,surf):
        if self.life<=0: return
        s=pygame.Surface((self.maxr*2+4,self.maxr*2+4),pygame.SRCALPHA)
        pygame.draw.circle(s,(*self.color,int(self.life*130)),
                           (self.maxr+2,self.maxr+2),int(self.r),2)
        surf.blit(s,(int(self.x)-self.maxr-2,int(self.y)-self.maxr-2))

particles=[]
ripples=[]

def spawn_particles(x,y,color,count=10):
    for _ in range(count):
        particles.append(Particle(x,y,color,'bubble' if random.random()>.5 else 'spark'))


# ── Torpedo ──────────────────────────────────────────────────────────────────
class Torpedo:
    SPEED=6; MAX_BOUNCES=5; MAX_AGE=680
    def __init__(self,x,y,vx,vy,owner):
        self.x,self.y=float(x),float(y)
        self.vx,self.vy=float(vx),float(vy)
        self.owner=owner; self.color=P1_COLOR if owner==1 else P2_COLOR
        self.alive=True; self.bounces=self.MAX_BOUNCES
        self.age=0; self.trail=[]
    @classmethod
    def from_angle(cls,x,y,angle,owner):
        s=cls.SPEED
        return cls(x,y,math.cos(angle)*s,math.sin(angle)*s,owner)
    def _reflect(self,wnx,wny):
        dot=self.vx*wnx+self.vy*wny
        self.vx-=2*dot*wnx; self.vy-=2*dot*wny
    def update(self):
        self.age+=1
        if self.age>self.MAX_AGE: self.alive=False; return
        self.trail.append((self.x,self.y))
        if len(self.trail)>12: self.trail.pop(0)
        for _ in range(4):
            sx,sy=self.vx/4,self.vy/4
            nx,ny=self.x+sx,self.y+sy
            hb=False
            if nx<PLAY_LEFT+3:    nx=PLAY_LEFT+3;    self.vx=abs(self.vx);  hb=True
            elif nx>PLAY_RIGHT-3: nx=PLAY_RIGHT-3;   self.vx=-abs(self.vx); hb=True
            if ny<PLAY_TOP+3:     ny=PLAY_TOP+3;     self.vy=abs(self.vy);  hb=True
            elif ny>PLAY_BOTTOM-3:ny=PLAY_BOTTOM-3;  self.vy=-abs(self.vy); hb=True
            if hb:
                self.bounces-=1
                spawn_particles(nx,ny,self.color,4)
                ripples.append(Ripple(nx,ny,self.color))
                if self.bounces<0: self.alive=False; return
                self.x,self.y=nx,ny; continue
            bt,bn=1.0,None
            for (ax,ay,bx,by) in get_maze():
                res=ray_vs_seg(self.x,self.y,sx,sy,ax,ay,bx,by)
                if res and res[0]<bt: bt,bn=res[0],(res[1],res[2])
            if bn:
                self.x+=sx*bt; self.y+=sy*bt
                self._reflect(*bn)
                self.bounces-=1
                spawn_particles(self.x,self.y,self.color,4)
                ripples.append(Ripple(self.x,self.y,self.color))
                if self.bounces<0: self.alive=False; return
                rem=1.0-bt
                self.x+=(self.vx/4)*rem; self.y+=(self.vy/4)*rem
            else:
                self.x,self.y=nx,ny
    def draw(self,surf):
        for i,(tx,ty) in enumerate(self.trail):
            frac=i/max(len(self.trail),1); r=max(1,int(frac*3))
            s=pygame.Surface((r*2+2,r*2+2),pygame.SRCALPHA)
            pygame.draw.circle(s,(*self.color,int(frac*160)),(r+1,r+1),r)
            surf.blit(s,(int(tx)-r-1,int(ty)-r-1))
        glow=pygame.Surface((28,28),pygame.SRCALPHA)
        pygame.draw.circle(glow,(*self.color,50),(14,14),12)
        surf.blit(glow,(int(self.x)-14,int(self.y)-14))
        angle=math.atan2(self.vy,self.vx); perp=angle+math.pi/2
        pts=[(self.x+math.cos(angle)*11,self.y+math.sin(angle)*11),
             (self.x+math.cos(perp)*3,  self.y+math.sin(perp)*3),
             (self.x-math.cos(angle)*7, self.y-math.sin(angle)*7),
             (self.x-math.cos(perp)*3,  self.y-math.sin(perp)*3)]
        pygame.draw.polygon(surf,self.color,pts)
        pygame.draw.circle(surf,WHITE,(int(self.x+math.cos(angle)*11),int(self.y+math.sin(angle)*11)),2)
    def to_dict(self):
        return {'x':self.x,'y':self.y,'vx':self.vx,'vy':self.vy,
                'owner':self.owner,'bounces':self.bounces,'age':self.age}
    @classmethod
    def from_dict(cls,d):
        t=cls(d['x'],d['y'],d['vx'],d['vy'],d['owner'])
        t.bounces=d['bounces']; t.age=d['age']; t.alive=True
        return t



# ── Powerups & Entities ──────────────────────────────────────────────────────
class Powerup:
    TYPES = ['speed', 'slow', 'mine', 'missile']
    COLORS = {'speed': (50, 255, 50), 'slow': (255, 50, 50), 'mine': (200, 100, 0), 'missile': (200, 0, 255)}
    def __init__(self, x, y):
        self.x, self.y = x, y
        # Favor 'mine' by including it more in the selection list
        choices = self.TYPES + ['mine', 'mine']
        self.ptype = random.choice(choices)
        self.color = self.COLORS[self.ptype]
        self.rect = pygame.Rect(x-12, y-12, 24, 24)
        self.life = 600
        
    def update(self):
        self.life -= 1
        
    def draw(self, surf):
        pygame.draw.rect(surf, self.color, self.rect, 2)
        cx, cy = int(self.x), int(self.y)
        if self.ptype == 'speed':
            pygame.draw.polygon(surf, self.color, [(cx, cy-6), (cx-6, cy+4), (cx+6, cy+4)])
        elif self.ptype == 'slow':
            pygame.draw.polygon(surf, self.color, [(cx-6, cy-4), (cx+6, cy-4), (cx, cy+6)])
        elif self.ptype == 'mine':
            pygame.draw.polygon(surf, self.color, [(cx-4,cy-7),(cx+4,cy-7),(cx+7,cy),(cx+4,cy+7),(cx-4,cy+7),(cx-7,cy)])
        elif self.ptype == 'missile':
            # Rocket icon
            pygame.draw.polygon(surf, self.color, [(cx,cy-8), (cx-4,cy+6), (cx,cy+4), (cx+4,cy+6)])

class Mine:
    def __init__(self, x, y, owner, color):
        self.x, self.y = x, y
        self.owner = owner
        self.color = color
        self.life = 0
        self.detonating = 0
        self.alive = True
        
    def update(self, p1, p2):
        if self.detonating > 0:
            self.detonating -= 1
            if self.detonating == 0:
                self.alive = False
        else:
            self.life += 1
            # Check proximity
            trigger = False
            for sub in [p1, p2]:
                if sub.alive and self.life >= 120: # ACTIVATE AFTER 2 SECONDS (120 frames)
                    if math.hypot(sub.x - self.x, sub.y - self.y) < 35:
                        trigger = True
            if trigger:
                self.detonating = 120 # 2 seconds
                
    def fire_bullets(self):
        # Fire bullets if detonating
        bullets = []
        if self.detonating > 0 and self.detonating % 10 == 0:
            for a in range(6):
                angle = (a/6) * math.pi * 2 + (self.detonating * 0.1)
                t = Torpedo.from_angle(self.x, self.y, angle, self.owner)
                t.MAX_AGE = 45 # Short lived spray
                t.bounces = 0
                bullets.append(t)
        return bullets
        
    def draw(self, surf):
        alpha = 255
        if self.life < 60: # Fades out over 1.0s
            alpha = int((1.0 - self.life/60.0) * 255)
        elif self.detonating > 0:
            alpha = 255 if (self.detonating // 4) % 2 == 0 else 50
        else:
            alpha = 0 # Invisible!
            
        if alpha > 0:
            cx, cy = int(self.x), int(self.y)
            s = pygame.Surface((30, 30), pygame.SRCALPHA)
            # Draw dark blue hexagon
            pygame.draw.polygon(s, (10, 30, 100, alpha), [(15, 0), (30, 8), (30, 22), (15, 30), (0, 22), (0, 8)])
            pygame.draw.polygon(s, (20, 50, 150, alpha), [(15, 0), (30, 8), (30, 22), (15, 30), (0, 22), (0, 8)], 2)
            
            # Draw pulsing red light in middle when detonating
            if self.detonating > 0:
                pygame.draw.circle(s, (255,50,50,alpha), (15,15), 5)
            surf.blit(s, (cx-15, cy-15))
class GuidedMissile:
    def __init__(self, x, y, angle, owner, color):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = math.cos(angle)*4.0, math.sin(angle)*4.0
        self.angle = angle
        self.owner = owner
        self.color = color
        self.speed = 4.0
        self.life = 10 * 60 # 10 seconds life
        self.alive = True
        self.trail = []
        
    def _reflect(self, wnx, wny):
        dot = self.vx * wnx + self.vy * wny
        self.vx -= 2 * dot * wnx
        self.vy -= 2 * dot * wny
        self.angle = math.atan2(self.vy, self.vx)
        
    def update_control(self, keys, controls):
        self.life -= 1
        if self.life <= 0: self.alive = False; return
        if keys.get(controls['left']): self.angle -= 0.08; self.vx=math.cos(self.angle)*self.speed; self.vy=math.sin(self.angle)*self.speed
        if keys.get(controls['right']): self.angle += 0.08; self.vx=math.cos(self.angle)*self.speed; self.vy=math.sin(self.angle)*self.speed
        
        self.trail.append((self.x, self.y))
        if len(self.trail) > 15: self.trail.pop(0)
        
        # Move step processing for bounce logic
        for _ in range(4):
            sx, sy = self.vx/4, self.vy/4
            nx, ny = self.x+sx, self.y+sy
            hb = False
            if nx<PLAY_LEFT+5:    nx=PLAY_LEFT+5;    self.vx=abs(self.vx); hb=True
            elif nx>PLAY_RIGHT-5: nx=PLAY_RIGHT-5;   self.vx=-abs(self.vx);hb=True
            if ny<PLAY_TOP+5:     ny=PLAY_TOP+5;     self.vy=abs(self.vy); hb=True
            elif ny>PLAY_BOTTOM-5:ny=PLAY_BOTTOM-5;  self.vy=-abs(self.vy);hb=True
            if hb:
                self.angle = math.atan2(self.vy, self.vx)
                spawn_particles(nx, ny, self.color, 4)
                self.x, self.y = nx, ny; continue
                
            bt, bn = 1.0, None
            for (ax,ay,bx,by) in get_maze():
                res = ray_vs_seg(self.x, self.y, sx, sy, ax,ay,bx,by)
                if res and res[0] < bt: bt, bn = res[0], (res[1], res[2])
            if bn:
                self.x += sx*bt; self.y += sy*bt
                self._reflect(*bn)
                spawn_particles(self.x, self.y, self.color, 4)
                rem = 1.0 - bt
                self.x += (self.vx/4)*rem; self.y += (self.vy/4)*rem
            else:
                self.x, self.y = nx, ny

    def draw(self, surf):
        for i,(tx,ty) in enumerate(self.trail):
            frac=i/max(len(self.trail),1); r=max(1,int(frac*4))
            s=pygame.Surface((r*2+2,r*2+2),pygame.SRCALPHA)
            pygame.draw.circle(s,(*self.color,int(frac*200)),(r+1,r+1),r)
            surf.blit(s,(int(tx)-r-1,int(ty)-r-1))
        
        # Big Rocket Graphic
        cx, cy = int(self.x), int(self.y)
        angle = self.angle
        perp = angle + math.pi/2
        
        # Rocket body
        pts = [
            (cx + math.cos(angle)*16, cy + math.sin(angle)*16), # nose
            (cx + math.cos(perp)*6,   cy + math.sin(perp)*6),
            (cx - math.cos(angle)*12, cy - math.sin(angle)*12), # tail
            (cx - math.cos(perp)*6,   cy - math.sin(perp)*6)
        ]
        pygame.draw.polygon(surf, self.color, pts)
        
        # Fins / Thruster
        pygame.draw.circle(surf, WHITE, (int(cx + math.cos(angle)*16), int(cy + math.sin(angle)*16)), 3)
        pygame.draw.polygon(surf, WHITE, [
            (cx - math.cos(angle)*8, cy - math.sin(angle)*8),
            (cx - math.cos(angle)*16 + math.cos(perp)*10, cy - math.sin(angle)*16 + math.sin(perp)*10),
            (cx - math.cos(angle)*12, cy - math.sin(angle)*12),
            (cx - math.cos(angle)*16 - math.cos(perp)*10, cy - math.sin(angle)*16 - math.sin(perp)*10)
        ])

# ── Sub ──────────────────────────────────────────────────────────────────────
class Sub:
    TURN_SPEED=0.09; MAX_SPEED=SUB_SPEED; ACCEL=0.28; FRICTION=0.9; SHIELD_DUR=150
    def __init__(self,x,y,controls,player_num):
        self.x,self.y=float(x),float(y)
        self.sx,self.sy=float(x),float(y)
        self.angle=0.0 if player_num==1 else math.pi
        self.sa=self.angle; self.speed=0.0
        self.controls=controls; self.player_num=player_num
        self.use_key=pygame.K_e if player_num==1 else pygame.K_RSHIFT
        self.color=P1_COLOR if player_num==1 else P2_COLOR
        self.torpedoes=[]; self.alive=True
        self.shoot_cooldown=0; self.reload_timer=0; self.bullet_count=0
        self.prop_bubbles=[]; self.shield_timer=0; self.prop_angle=0.0
        self._respawn_timer=0
        self.powerup=None; self.speed_timer=0; self.slow_timer=0
        self.active_missile=None
        self.is_ai = False


    def respawn(self):
        self.x,self.y=self.sx,self.sy; self.angle=self.sa; self.speed=0.0
        self.torpedoes=[]; self.alive=True; self.shoot_cooldown=0
        self.shield_timer=self.SHIELD_DUR; self._respawn_timer=0
        self.powerup=None; self.speed_timer=0; self.slow_timer=0
        self.active_missile=None


    def is_shielded(self): return self.shield_timer>0
    def _resolve_walls(self):
        for _ in range(4):
            for (ax,ay,bx,by) in get_maze():
                res=push_out_of_wall(self.x,self.y,SUB_RADIUS,ax,ay,bx,by,WALL_THICK)
                if res: self.x,self.y=res; self.speed*=0.6
        self.x=clamp(self.x,PLAY_LEFT+SUB_RADIUS+2,PLAY_RIGHT-SUB_RADIUS-2)
        self.y=clamp(self.y,PLAY_TOP+SUB_RADIUS+2,PLAY_BOTTOM-SUB_RADIUS-2)
    def update(self,keys):
        if self.shield_timer>0: self.shield_timer-=1
        if self.reload_timer>0:
            self.reload_timer-=1
            if self.reload_timer==0: self.bullet_count=0
        
        if self.speed_timer>0: self.speed_timer-=1
        if self.slow_timer>0: self.slow_timer-=1
        
        # Guided missile control logic
        if self.active_missile and self.active_missile.alive:
            self.speed = 0 # Fully immobilize
            self.x+=math.cos(self.angle)*self.speed; self.y+=math.sin(self.angle)*self.speed
            self._resolve_walls()
            self.active_missile.update_control(keys, self.controls)
            self.torpedoes=[t for t in self.torpedoes if t.alive]
            for t in self.torpedoes: t.update()
            return
            
        self.torpedoes=[t for t in self.torpedoes if t.alive]
        for t in self.torpedoes: t.update()
        if not self.alive: return
        if self.shoot_cooldown>0: self.shoot_cooldown-=1
        if keys.get(self.controls['left']):  self.angle-=self.TURN_SPEED
        if keys.get(self.controls['right']): self.angle+=self.TURN_SPEED
        
        base_accel = self.ACCEL
        base_max_fwd = 2.4
        base_max_bwd = 2.1
        if self.speed_timer > 0:
            base_max_fwd += 1.5; base_max_bwd += 1.5
        if self.slow_timer > 0:
            base_max_fwd = max(0.5, base_max_fwd - 1.5); base_max_bwd = max(0.5, base_max_bwd - 1.5)
            
        if keys.get(self.controls['up']):
            self.speed=min(self.speed+base_accel, base_max_fwd)
        elif keys.get(self.controls['down']):
            self.speed=max(self.speed-base_accel, -base_max_bwd)
        else:
            self.speed*=self.FRICTION
        self.x+=math.cos(self.angle)*self.speed
        self.y+=math.sin(self.angle)*self.speed
        self._resolve_walls()
        self.prop_angle+=self.speed*0.3
        if abs(self.speed)>0.4 and random.random()>0.5:
            bx=self.x-math.cos(self.angle)*16; by=self.y-math.sin(self.angle)*16
            self.prop_bubbles.append({'x':bx,'y':by,'r':random.uniform(1,2.5),'life':1.0,
                'vx':-math.cos(self.angle)*1.2+random.uniform(-0.4,0.4),
                'vy':-math.sin(self.angle)*1.2+random.uniform(-0.4,0.4)-0.2})
        for b in self.prop_bubbles:
            b['x']+=b['vx']; b['y']+=b['vy']; b['vy']-=0.04; b['life']-=0.045
        self.prop_bubbles=[b for b in self.prop_bubbles if b['life']>0]
        can_shoot=(self.shoot_cooldown==0 and self.reload_timer==0 and self.bullet_count<MAX_BULLETS)
        if keys.get(self.controls['shoot']) and can_shoot:
            tx=self.x+math.cos(self.angle)*24; ty=self.y+math.sin(self.angle)*24
            self.torpedoes.append(Torpedo.from_angle(tx,ty,self.angle,self.player_num))
            self.shoot_cooldown=10; self.bullet_count+=1; self.speed-=0.3
            play_sound('shoot')
            spawn_particles(self.x-math.cos(self.angle)*14,
                            self.y-math.sin(self.angle)*14,self.color,5)
            if self.bullet_count>=MAX_BULLETS: self.reload_timer=RELOAD_FRAMES

    def get_ai_keys(self, target):
        keys = {k: False for k in self.controls.values()}
        if not target or not target.alive: return keys
        
        # 0. Guided Missile Steering
        if self.active_missile and self.active_missile.alive:
            msl = self.active_missile
            dx = target.x - msl.x
            dy = target.y - msl.y
            target_angle = math.atan2(dy, dx)
            diff = (target_angle - msl.angle + math.pi) % (2 * math.pi) - math.pi
            if diff > 0.1: keys[self.controls['right']] = True
            elif diff < -0.1: keys[self.controls['left']] = True
            return keys

        my_cell = get_cell_from_pos(self.x, self.y)
        target_cell = get_cell_from_pos(target.x, target.y)
        path = a_star(my_cell, target_cell)
        
        # Target Leading Logic
        dist_to_target = math.hypot(target.x - self.x, target.y - self.y)
        bullet_speed = 5.0 # Speed of torpedo
        lead_time = dist_to_target / bullet_speed
        
        # Predict target position (very simple linear prediction)
        # We need target's velocity. Let's assume Sub has vx, vy or calculate it.
        # Looking at Sub.update, it moves by cos(angle)*speed.
        t_vx = math.cos(target.angle) * target.speed
        t_vy = math.sin(target.angle) * target.speed
        
        aim_x = target.x + t_vx * lead_time
        aim_y = target.y + t_vy * lead_time
        
        target_x, target_y = aim_x, aim_y
        
        if path:
            # Navigate toward the next cell center
            wp_x, wp_y = get_pos_from_cell(path[0][0], path[0][1])
            dist_to_wp = math.hypot(wp_x - self.x, wp_y - self.y)
            if dist_to_wp < 20 and len(path) > 1:
                wp_x, wp_y = get_pos_from_cell(path[1][0], path[1][1])
            
            # If we are navigating, we use the waypoint for movement
            nav_dx = wp_x - self.x
            nav_dy = wp_y - self.y
            nav_angle = math.atan2(nav_dy, nav_dx)
        else:
            nav_angle = math.atan2(target.y - self.y, target.x - self.x)

        # Smooth turning toward navigation angle
        diff = (nav_angle - self.angle + math.pi) % (2 * math.pi) - math.pi
        if diff > 0.05: keys[self.controls['right']] = True
        elif diff < -0.05: keys[self.controls['left']] = True
        
        # Movement
        dist = math.hypot(target.x - self.x, target.y - self.y)
        if abs(diff) < 0.6:
            if dist > 40: keys[self.controls['up']] = True
        elif abs(diff) > 2.5: # Back up if facing away
            keys[self.controls['down']] = True

        # Shooting logic
        # 1. Point-blank aggression: widen aim diff if very close
        aim_dx = aim_x - self.x
        aim_dy = aim_y - self.y
        real_target_angle = math.atan2(aim_dy, aim_dx)
        aim_diff = (real_target_angle - self.angle + math.pi) % (2 * math.pi) - math.pi
        
        shoot_tolerance = 0.2
        if dist < 80: shoot_tolerance = 0.8 # Point blank spray
        
        if abs(aim_diff) < shoot_tolerance and dist < 600:
            # 2. Self-preservation: don't shoot if wall is very close (reduced margin)
            ux, uy = math.cos(self.angle), math.sin(self.angle)
            wall_ahead = False
            for ax, ay, bx, by in current_maze:
                hit = ray_vs_seg(self.x, self.y, ux, uy, ax, ay, bx, by)
                if hit and hit[0] < 25: # 25px safety margin (less perfect)
                    wall_ahead = True
                    break
            
            if not wall_ahead:
                if can_see(self.x, self.y, target.x, target.y) or dist < 100:
                    if random.random() < 0.12: # increased fire rate
                        keys[self.controls['shoot']] = True
        
        if self.powerup and random.random() < 0.05:
            keys[self.controls['shoot']] = True
            
        return keys

    def draw(self,surf):
        for b in self.prop_bubbles:
            alpha=int(b['life']*130); r=max(1,int(b['r']))
            s=pygame.Surface((r*2+2,r*2+2),pygame.SRCALPHA)
            pygame.draw.circle(s,(180,230,255,alpha),(r+1,r+1),r,1)
            surf.blit(s,(int(b['x'])-r-1,int(b['y'])-r-1))
        if self.shield_timer>0:
            pulse=0.6+0.4*math.sin(self.shield_timer*0.15); r=24
            draw_circle_alpha(surf,self.color,(int(self.x),int(self.y)),r,int(pulse*70))
            s2=pygame.Surface((r*2+4,r*2+4),pygame.SRCALPHA)
            pygame.draw.circle(s2,(*self.color,int(pulse*150)),(r+2,r+2),r,2)
            surf.blit(s2,(int(self.x)-r-2,int(self.y)-r-2))
        if self.reload_timer>0:
            r=20; s3=pygame.Surface((r*2+4,r*2+4),pygame.SRCALPHA)
            pygame.draw.circle(s3,(255,80,80,110),(r+2,r+2),r,2)
            surf.blit(s3,(int(self.x)-r-2,int(self.y)-r-2))
        for t in self.torpedoes: t.draw(surf)
        if not self.alive: return
        cx,cy=int(self.x),int(self.y); W2,H2=18,8
        glow=pygame.Surface((60,60),pygame.SRCALPHA)
        pygame.draw.ellipse(glow,(*self.color,30),(0,0,60,60))
        surf.blit(glow,(cx-30,cy-30))
        def rot(px,py):
            c,s=math.cos(self.angle),math.sin(self.angle)
            return(cx+px*c-py*s,cy+px*s+py*c)
        hull=[rot(W2,0),rot(W2-4,H2),rot(-W2,H2),rot(-W2,-H2),rot(W2-4,-H2)]
        base=(3,40,60) if self.player_num==1 else (50,5,15)
        mid=(5,70,80) if self.player_num==1 else (80,10,25)
        pygame.draw.polygon(surf,mid,hull); pygame.draw.polygon(surf,self.color,hull,2)
        hl=[rot(W2-5,-H2+1),rot(-W2+3,-H2+1),rot(-W2+3,-H2+3),rot(W2-5,-H2+3)]
        hs=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        pygame.draw.polygon(hs,(*self.color,45),hl); surf.blit(hs,(0,0))
        tower=[rot(-1,-H2),rot(2,-H2),rot(2,-H2-8),rot(-1,-H2-8)]
        pygame.draw.polygon(surf,base,tower); pygame.draw.polygon(surf,self.color,tower,1)
        pb=rot(0,-H2-8); pt=rot(0,-H2-14); pe=rot(5,-H2-14)
        pygame.draw.line(surf,self.color,(int(pb[0]),int(pb[1])),(int(pt[0]),int(pt[1])),2)
        pygame.draw.line(surf,self.color,(int(pt[0]),int(pt[1])),(int(pe[0]),int(pe[1])),2)
        pygame.draw.circle(surf,self.color,(int(pe[0]),int(pe[1])),2)
        po=rot(6,0)
        pygame.draw.circle(surf,self.color,(int(po[0]),int(po[1])),3,1)
        pygame.draw.circle(surf,self.color,(int(po[0]),int(po[1])),1)
        prop_cx,prop_cy=rot(-W2-2,0)
        ps=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        for i in range(3):
            ba=self.prop_angle+(i/3)*math.pi*2
            bx1=prop_cx+math.cos(self.angle+math.pi/2+ba)*5
            by1=prop_cy+math.sin(self.angle+math.pi/2+ba)*5
            pygame.draw.line(ps,(*self.color,150),(int(bx1),int(by1)),(int(prop_cx),int(prop_cy)),2)
        surf.blit(ps,(0,0))
        num=font_tiny.render(str(self.player_num),True,WHITE)
        surf.blit(num,num.get_rect(center=(cx,cy)))
    def to_dict(self):
        return {'x':self.x,'y':self.y,'angle':self.angle,'speed':self.speed,
                'alive':self.alive,'shield':self.shield_timer,
                'reload':self.reload_timer,'bullets':self.bullet_count,
                'torpedoes':[t.to_dict() for t in self.torpedoes]}
    def apply_state(self,d):
        self.x=d['x']; self.y=d['y']; self.angle=d['angle']; self.speed=d['speed']
        self.alive=d['alive']; self.shield_timer=d['shield']
        self.reload_timer=d['reload']; self.bullet_count=d['bullets']
        tds=d.get('torpedoes',[])
        # Sync torpedoes by index
        while len(self.torpedoes)<len(tds):
            td=tds[len(self.torpedoes)]
            self.torpedoes.append(Torpedo.from_dict(td))
        while len(self.torpedoes)>len(tds):
            self.torpedoes.pop()
        for i,td in enumerate(tds):
            self.torpedoes[i].x=td['x']; self.torpedoes[i].y=td['y']
            self.torpedoes[i].vx=td['vx']; self.torpedoes[i].vy=td['vy']
            self.torpedoes[i].bounces=td['bounces']; self.torpedoes[i].age=td['age']


# ── Draw helpers ─────────────────────────────────────────────────────────────
_bg_surface = None
def draw_background(surf,t):
    global _bg_surface
    if _bg_surface is None:
        _bg_surface = pygame.Surface((WIDTH,HEIGHT))
        _bg_surface.fill(ABYSS)
        grad=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        for y in range(0,HEIGHT,4):
            c=lerp_color(DEEP,ABYSS,y/HEIGHT)
            pygame.draw.rect(grad,(*c,180),(0,y,WIDTH,4))
        _bg_surface.blit(grad,(0,0))
    surf.blit(_bg_surface,(0,0))
    
    caus=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
    for i in range(5):
        cx=int((math.sin(t*0.4+i*1.3)*0.5+0.5)*WIDTH)
        cy=int((math.cos(t*0.3+i*0.9)*0.5+0.5)*HEIGHT)
        r=int(50+math.sin(t*0.7+i)*22)
        pygame.draw.circle(caus,(0,255,231,7),(cx,cy),r)
    surf.blit(caus,(0,0))

_border_surface = None
def draw_border(surf,t):
    global _border_surface
    if _border_surface is None:
        _border_surface = pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        rect=pygame.Rect(PLAY_LEFT,PLAY_TOP,PLAY_RIGHT-PLAY_LEFT,PLAY_BOTTOM-PLAY_TOP)
        pygame.draw.rect(_border_surface,WALL_DARK,rect,PAD)
        pygame.draw.rect(_border_surface,WALL_MID,rect,PAD-4)
        pygame.draw.rect(_border_surface,(0,45,80),rect,6)
    surf.blit(_border_surface,(0,0))
    pulse=int((math.sin(t*1.1)*0.3+0.7)*80)
    gs=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
    rect=pygame.Rect(PLAY_LEFT,PLAY_TOP,PLAY_RIGHT-PLAY_LEFT,PLAY_BOTTOM-PLAY_TOP)
    pygame.draw.rect(gs,(*WALL_GLOW,pulse),rect,3)
    surf.blit(gs,(0,0))

_walls_surface = None
def reset_walls_cache():
    global _walls_surface
    _walls_surface = None

def draw_walls(surf,t):
    global _walls_surface
    if _walls_surface is None:
        _walls_surface = pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        for(x1,y1,x2,y2) in get_maze():
            pygame.draw.line(_walls_surface,WALL_DARK,(x1,y1),(x2,y2),16)
            pygame.draw.line(_walls_surface,WALL_MID,(x1,y1),(x2,y2),12)
            pygame.draw.line(_walls_surface,(0,45,80),(x1,y1),(x2,y2),7)
            
    surf.blit(_walls_surface,(0,0))
    gs=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
    pulse=int((math.sin(t*1.2)*0.3+0.7)*65)
    for(x1,y1,x2,y2) in get_maze():
        pygame.draw.line(gs,(*WALL_GLOW,pulse),(x1,y1),(x2,y2),2)
    surf.blit(gs,(0,0))

_ocean_surface = None
def draw_ocean_floor(surf):
    global _ocean_surface
    if _ocean_surface is None:
        _ocean_surface = pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        r=pygame.Rect(PLAY_LEFT+3,PLAY_BOTTOM-22,PLAY_RIGHT-PLAY_LEFT-6,20)
        pygame.draw.rect(_ocean_surface,(8,25,40),r)
        rng2=random.Random(999)
        s=pygame.Surface((r.width,r.height),pygame.SRCALPHA)
        for _ in range(40):
            sx=rng2.randint(0,r.width); sy=rng2.randint(0,r.height); sr=rng2.randint(1,3)
            pygame.draw.circle(s,(*SAND,45),(sx,sy),sr)
        _ocean_surface.blit(s,(r.x,r.y))
    surf.blit(_ocean_surface,(0,0))

def draw_hud(surf,s1,s2,p1_sub,p2_sub, match_scores=None):
    hud=pygame.Surface((WIDTH,44),pygame.SRCALPHA)
    pygame.draw.rect(hud,(1,8,16,220),(0,0,WIDTH,44))
    pygame.draw.line(hud,(*BIOLUM,70),(0,43),(WIDTH,43),1)
    surf.blit(hud,(0,0))
    title=font_med.render("SUB SHOCKERS",True,BIOLUM)
    surf.blit(title,(WIDTH//2-title.get_width()//2,10))
    if match_scores is not None:
        m_txt = font_tiny.render(f"WAR: {match_scores[0]} - {match_scores[1]}  (First to 2)", True, (150, 150, 150))
        surf.blit(m_txt,(WIDTH//2-m_txt.get_width()//2, 30))
        
    surf.blit(font_small.render("ANGLER",True,(*P1_COLOR,180)),(55,4))
    surf.blit(font_big.render(str(s1),True,P1_COLOR),(55,16))
    _draw_bullet_bar(surf,p1_sub,100,22)
    surf.blit(font_small.render("VIPER",True,(*P2_COLOR,180)),(WIDTH-100,4))
    surf.blit(font_big.render(str(s2),True,P2_COLOR),(WIDTH-55,16))
    _draw_bullet_bar(surf,p2_sub,WIDTH-170,22)
    
    # Legend at bottom
    p1_ctrl = font_tiny.render("ANGLER (P1): WASD Move, Q Shoot/Use", True, (0,150,200))
    p2_ctrl = font_tiny.render("VIPER (P2): ARROWS Move, M Shoot/Use", True, (200,50,50))
    surf.blit(p1_ctrl, (10, HEIGHT - 20))
    surf.blit(p2_ctrl, (WIDTH - p2_ctrl.get_width() - 10, HEIGHT - 20))

def _draw_bullet_bar(surf,sub,x,y):
    if sub.reload_timer>0:
        frac=1.0-sub.reload_timer/RELOAD_FRAMES; bw=64
        pygame.draw.rect(surf,(40,0,0),(x,y,bw,6))
        col=(255,80,80) if frac<0.5 else (255,160,0)
        pygame.draw.rect(surf,col,(x,y,int(bw*frac),6))
    else:
        rem=MAX_BULLETS-sub.bullet_count
        for i in range(MAX_BULLETS):
            col=sub.color if i<rem else (30,30,40)
            pygame.draw.circle(surf,col,(x+i*8,y+3),3)

_vignette_surface = None
def draw_vignette(surf):
    global _vignette_surface
    if _vignette_surface is None:
        _vignette_surface = pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        for step in range(8):
            rw=WIDTH-step*24; rh=HEIGHT-step*18
            if rw<0 or rh<0: break
            alpha=int((step/8)**1.5*100)
            rect=pygame.Rect((WIDTH-rw)//2,(HEIGHT-rh)//2,rw,rh)
            pygame.draw.rect(_vignette_surface,(1,8,16,alpha//8),rect,10,border_radius=6)
    surf.blit(_vignette_surface,(0,0))

def draw_map_flash(surf,alpha):
    if alpha<=0: return
    fl=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
    fl.fill((0,200,255,alpha)); surf.blit(fl,(0,0))

def draw_grand_winner(surf, player_num):
    ov=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
    ov.fill((1,8,16,230)); surf.blit(ov,(0,0))
    color=P1_COLOR if player_num==1 else P2_COLOR
    label="ANGLER" if player_num==1 else "VIPER"
    wt=font_big.render(f"{label} HAS WON THE WAR!",True,color)
    surf.blit(wt,(WIDTH//2-wt.get_width()//2,HEIGHT//2-100))
    
    lines = [
        f"{label} has unlocked the Secret Chamber.",
        "With the ultimate weapons secured,",
        f"{label} is the New Ruler of the Ocean!"
    ]
    for i, line in enumerate(lines):
        st=font_med.render(line,True,(0,200,255))
        surf.blit(st,(WIDTH//2-st.get_width()//2,HEIGHT//2-20 + i*35))
        
    rt=font_small.render("Press R to Return to Menu",True,(150,150,150))
    surf.blit(rt,(WIDTH//2-rt.get_width()//2,HEIGHT//2+120))






def draw_win_screen(surf,player_num):
    ov=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
    ov.fill((1,8,16,200)); surf.blit(ov,(0,0))
    color=P1_COLOR if player_num==1 else P2_COLOR
    label="ANGLER" if player_num==1 else "VIPER"
    wt=font_big.render(f"{label} WINS!",True,color)
    st=font_med.render("Press R to restart",True,(0,180,255))
    surf.blit(wt,(WIDTH//2-wt.get_width()//2,HEIGHT//2-40))
    surf.blit(st,(WIDTH//2-st.get_width()//2,HEIGHT//2+20))




# ── Input text box ────────────────────────────────────────────────────────────
class TextBox:
    def __init__(self,rect,placeholder='',max_len=40):
        self.rect=pygame.Rect(rect); self.text=''; self.active=False
        self.placeholder=placeholder; self.max_len=max_len
    def handle(self,event):
        if event.type==pygame.MOUSEBUTTONDOWN:
            self.active=self.rect.collidepoint(event.pos)
        if event.type==pygame.KEYDOWN and self.active:
            if event.key==pygame.K_BACKSPACE: self.text=self.text[:-1]
            elif event.key not in (pygame.K_RETURN,pygame.K_TAB):
                if len(self.text)<self.max_len: self.text+=event.unicode
    def draw(self,surf):
        col=BIOLUM if self.active else GRAY
        pygame.draw.rect(surf,(10,25,40),self.rect,border_radius=4)
        pygame.draw.rect(surf,col,self.rect,2,border_radius=4)
        txt=self.text if self.text else self.placeholder
        color=WHITE if self.text else (60,60,70)
        t=font_small.render(txt,True,color)
        surf.blit(t,(self.rect.x+8,self.rect.y+self.rect.height//2-t.get_height()//2))

def screen_multiplayer_lobby():
    btn_create = Button((WIDTH//2-130, HEIGHT//2-110, 260, 42), "CREATE ROOM")
    btn_join   = Button((WIDTH//2-130, HEIGHT//2-60, 260, 42), "JOIN ROOM")
    txt_ip     = TextBox((WIDTH//2-130, HEIGHT//2-10, 260, 36), "SERVER IP (e.g. localhost)")
    txt_room   = TextBox((WIDTH//2-70, HEIGHT//2+40, 140, 36), "ROOM CODE", max_len=4)
    btn_back   = Button((WIDTH//2-60, HEIGHT//2+110, 120, 32), "BACK", GRAY)
    
    txt_ip.text = "localhost" # Default
    # You might want to allow entering the server IP too
    
    status_msg = ""
    status_color = (150, 150, 150)
    
    room_code = ""
    is_host = False
    connected = False
    
    while True:
        t=pygame.time.get_ticks()/1000
        events = pygame.event.get()
        for event in events:
            if event.type==pygame.QUIT: pygame.quit(); sys.exit()
            txt_ip.handle(event)
            txt_room.handle(event)
            
            if btn_create.clicked(event):
                server_ip = txt_ip.text.strip() or "localhost"
                try:
                    status_msg = "CONNECTING..."
                    status_color = (150, 150, 150)
                    draw_background(screen, t)
                    st = font_med.render(status_msg, True, status_color)
                    screen.blit(st, (WIDTH//2-st.get_width()//2, HEIGHT//2 + 70))
                    pygame.display.flip()
                    
                    sio.connect(f"http://{server_ip}:5000", wait_timeout=3)
                    room_code = sio.call('create_room')
                    is_host = True
                    connected = True
                    status_msg = f"ROOM CREATED: {room_code}"
                    status_color = BIOLUM
                except Exception as e:
                    status_msg = "CONNECTION FAILED (Check Server & IP)"
                    status_color = (255, 50, 50)
            
            if btn_join.clicked(event):
                server_ip = txt_ip.text.strip() or "localhost"
                code = txt_room.text.strip().upper()
                if len(code) == 4:
                    try:
                        status_msg = "CONNECTING..."
                        draw_background(screen, t)
                        st = font_med.render(status_msg, True, status_color)
                        screen.blit(st, (WIDTH//2-st.get_width()//2, HEIGHT//2 + 70))
                        pygame.display.flip()
                        
                        sio.connect(f"http://{server_ip}:5000", wait_timeout=3)
                        success = sio.call('join_room', code)
                        if success:
                            room_code = code
                            is_host = False
                            connected = True
                            status_msg = "JOINED! STARTING..."
                            status_color = BIOLUM
                        else:
                            status_msg = "ROOM NOT FOUND / FULL"
                            status_color = (255, 50, 50)
                            sio.disconnect()
                    except Exception as e:
                        status_msg = "CONNECTION FAILED (Check Server & IP)"
                        status_color = (255, 50, 50)

            if btn_back.clicked(event):
                if connected: sio.disconnect()
                return None
            
        if connected and not is_host:
            # P2 just waits for start_game
            pass
            
        draw_background(screen,t)
        title=font_big.render("MULTIPLAYER LOBBY",True,BIOLUM)
        screen.blit(title,(WIDTH//2-title.get_width()//2, HEIGHT//2-180))
        
        if not connected:
            btn_create.draw(screen)
            btn_join.draw(screen)
            txt_ip.draw(screen)
            txt_room.draw(screen)
        
        if status_msg:
            st = font_med.render(status_msg, True, status_color)
            screen.blit(st, (WIDTH//2-st.get_width()//2, HEIGHT//2 + 70))
            if status_msg.startswith("ROOM CREATED"):
                info = font_tiny.render("Share the Room Code above with your friend!", True, (150, 150, 150))
                screen.blit(info, (WIDTH//2-info.get_width()//2, HEIGHT//2 + 100))
        else:
            note = font_tiny.render("Host: Run server.py and enter Server IP", True, (0, 120, 150))
            screen.blit(note, (WIDTH//2-note.get_width()//2, HEIGHT//2 + 70))
            
        btn_back.draw(screen)
        pygame.display.flip(); clock.tick(60)
        
        if connected and net_ready:
            return {'host': is_host, 'room': room_code}


# ── Button ────────────────────────────────────────────────────────────────────
class Button:
    def __init__(self,rect,label,color=BIOLUM):
        self.rect=pygame.Rect(rect); self.label=label; self.color=color; self.hovered=False
    def draw(self,surf):
        self.hovered=self.rect.collidepoint(pygame.mouse.get_pos())
        bg=(10,35,50) if self.hovered else (5,18,30)
        border=self.color if self.hovered else tuple(int(c*0.5) for c in self.color)
        pygame.draw.rect(surf,bg,self.rect,border_radius=4)
        pygame.draw.rect(surf,border,self.rect,2,border_radius=4)
        t=font_small.render(self.label,True,self.color)
        surf.blit(t,(self.rect.centerx-t.get_width()//2,self.rect.centery-t.get_height()//2))
    def clicked(self,event):
        return (event.type==pygame.MOUSEBUTTONDOWN and
                event.button==1 and self.rect.collidepoint(event.pos))


# ── Game logic helpers ────────────────────────────────────────────────────────
def make_players():
    p1=Sub(PLAY_LEFT+60,(PLAY_TOP+PLAY_BOTTOM)//2,
           {'left':pygame.K_a,'right':pygame.K_d,
            'up':pygame.K_w,'down':pygame.K_s,'shoot':pygame.K_q},1)
    p2=Sub(PLAY_RIGHT-60,(PLAY_TOP+PLAY_BOTTOM)//2,
           {'left':pygame.K_LEFT,'right':pygame.K_RIGHT,
            'up':pygame.K_UP,'down':pygame.K_DOWN,'shoot':pygame.K_m},2)
    return p1,p2

def check_hits(p1,p2, guided_missiles):
    p1_dead=False; p2_dead=False
    for sub in [p1,p2]:
        for torp in list(sub.torpedoes):
            if sub.is_shielded(): continue
            if sub.alive and math.hypot(torp.x-sub.x,torp.y-sub.y)<22:
                torp.alive=False; sub.alive=False
                play_sound('explode')
                spawn_particles(sub.x,sub.y,sub.color,35)
                spawn_particles(sub.x,sub.y,WHITE,12)
                ripples.append(Ripple(sub.x,sub.y,sub.color))
                if sub.player_num==1: p1_dead=True
                else: p2_dead=True
        # Check guided missiles
        if not sub.is_shielded() and sub.alive:
            for m in guided_missiles:
                if math.hypot(m.x-sub.x,m.y-sub.y)<22:
                    if sub.player_num == m.owner and m.life > 570: # Safe for first 0.5s
                        continue
                    m.alive=False; sub.alive=False
                    play_sound('explode')
                    spawn_particles(sub.x,sub.y,sub.color,35)
                    spawn_particles(sub.x,sub.y,WHITE,12)
                    ripples.append(Ripple(sub.x,sub.y,sub.color))
                    if sub.player_num==1: p1_dead=True
                    else: p2_dead=True
    for shooter,target in [(p1,p2),(p2,p1)]:
        for torp in list(shooter.torpedoes):
            if not torp.alive: continue
            if not target.alive or target.is_shielded(): continue
            if math.hypot(torp.x-target.x,torp.y-target.y)<22:
                torp.alive=False; target.alive=False
                play_sound('explode')
                spawn_particles(target.x,target.y,target.color,40)
                spawn_particles(target.x,target.y,WHITE,14)
                ripples.append(Ripple(target.x,target.y,target.color))
                if target.player_num==1: p1_dead=True
                else: p2_dead=True
    return p1_dead,p2_dead


# ══════════════════════════════════════════════════════════════════════════════
# SCREENS
# ══════════════════════════════════════════════════════════════════════════════


# ── Splash Screen ─────────────────────────────────────────────────────────────
def screen_splash():
    # Music stays silent here
    bubbles = []
    start_t = time.time()
    while True:
        t = time.time() - start_t
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN:
                return
        
        screen.fill(ABYSS)
        
        # Rising Bubbles
        if random.random() < 0.2:
            bubbles.append({
                'x': random.randint(0, WIDTH),
                'y': HEIGHT + 20,
                'r': random.uniform(2, 6),
                'speed': random.uniform(2, 4)
            })
            
        for b in bubbles:
            b['y'] -= b['speed']
            b['x'] += math.sin(t * 2 + b['r']) * 1.2
            # Use pygame.SRCALPHA for translucent bubbles if needed, or simple circles
            pygame.draw.circle(screen, (255, 255, 255, 100), (int(b['x']), int(b['y'])), int(b['r']), 1)
        bubbles = [b for b in bubbles if b['y'] > -20]
        
        # Bobbing Submarine
        bob_offset = math.sin(t * 1.2) * 25
        draw_front_sub(screen, WIDTH//2, HEIGHT//2 + bob_offset, 110, P1_COLOR)
        
        # Pulsing Text
        pulse = 127 + 127 * math.sin(t * 3.5)
        text = font_med.render("CLICK ANYWHERE TO START", True, WHITE)
        text.set_alpha(int(pulse))
        screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT - 120))
        
        pygame.display.flip()
        clock.tick(60)


# ── Intro Animation ─────────────────────────────────────────────────────────────
def intro_animation():
    play_music('music_intro', loops=-1)
    start_t = time.time()
    intro_bubbles = []
    story_lines = [
        "For centuries, the ocean depths were ruled in peace.",
        "But advanced factions built vessels of war...",
        "Now, the Biome is a battlefield.",
        "Only one Commander will claim the Secret Chamber",
        "and become the New Ruler of the Ocean.",
        "",
        "Descending to the abyss..."
    ]
    
    start_time = pygame.time.get_ticks()
    
    # Fish objects
    fishes = []
    for _ in range(15):
        fy = random.randint(100, HEIGHT*2)
        fx = random.randint(0, WIDTH)
        fs = random.uniform(1.5, 3.5)
        fd = 1 if random.random() > 0.5 else -1
        fc = (random.randint(50, 200), random.randint(100, 255), random.randint(150, 255))
        fishes.append([fx, fy, fs, fd, fc])
        
    intro_bubbles = []

    while True:
        t = pygame.time.get_ticks()
        elapsed = (t - start_time) / 1000.0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                return
        
        if elapsed > 15.0:
            return
            
        # The camera "descends", so objects go up
        descend_speed = 60
        y_offset = int(elapsed * descend_speed)
        
        # Color transitioning from light blue surface to abyss
        progress = min(elapsed / 10.0, 1.0)
        bg_col = lerp_color((12, 100, 180), ABYSS, progress)
        screen.fill(bg_col)
        
        # Generate bubbles
        if random.random() < 0.3:
            intro_bubbles.append([random.randint(0, WIDTH), HEIGHT + 20, random.uniform(2, 6)])
            
        for b in intro_bubbles:
            b[1] -= (4 + b[2]) # Rise up fast (descending effect)
            b[0] += math.sin(t/300.0 + b[2]) * 2
            pygame.draw.circle(screen, (255, 255, 255, 120), (int(b[0]), int(b[1])), int(b[2]), 1)
        intro_bubbles = [b for b in intro_bubbles if b[1] > -20]
        
        # Draw and move fish
        for fish in fishes:
            fish[0] += fish[2] * fish[3]
            screen_y = fish[1] - y_offset
            if fish[0] < -50 and fish[3] < 0: fish[0] = WIDTH + 50
            elif fish[0] > WIDTH + 50 and fish[3] > 0: fish[0] = -50
            
            if -50 < screen_y < HEIGHT + 50:
                # Simple fish shape
                length = fish[2] * 8
                pts = [
                    (fish[0], screen_y),
                    (fish[0] - length * fish[3], screen_y - length/2),
                    (fish[0] - length * fish[3], screen_y + length/2)
                ]
                pygame.draw.polygon(screen, fish[4], pts)
                tail = [
                    (fish[0] - length * fish[3], screen_y),
                    (fish[0] - length * fish[3] - length/2 * fish[3], screen_y - length/3),
                    (fish[0] - length * fish[3] - length/2 * fish[3], screen_y + length/3)
                ]
                pygame.draw.polygon(screen, fish[4], tail)

        # Draw Story Text
        for i, line in enumerate(story_lines):
            # Appear one-by-one, spaced out more
            line_appear_time = i * 2.0
            if elapsed > line_appear_time:
                # Fade in effect
                alpha = min(int((elapsed - line_appear_time) * 255), 255)
                # Fade out effect
                if elapsed > line_appear_time + 4.5:
                    alpha = max(0, 255 - int((elapsed - (line_appear_time + 4.5)) * 255))
                
                if alpha > 0:
                    text_surf = font_med.render(line, True, BIOLUM)
                    text_surf.set_alpha(alpha)
                    screen.blit(text_surf, (WIDTH//2 - text_surf.get_width()//2, 180 + i * 40))

        # Overlay Fade out transition at the end
        if elapsed > 13.5:
            fade_alpha = min((elapsed - 13.5) / 1.5 * 255, 255)
            fade_surf = pygame.Surface((WIDTH, HEIGHT))
            fade_surf.fill((1, 8, 16))
            fade_surf.set_alpha(int(fade_alpha))
            screen.blit(fade_surf, (0,0))

        # Skip hint
        # Skip hint
        if elapsed < 2.0:
            hint = font_tiny.render("PRESS ANY KEY TO SKIP", True, (255, 255, 255, 80))
            screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT - 30))
        elif elapsed > 2.0:
            skip = font_tiny.render("Press any key to skip", True, (100, 150, 180, 60))
            screen.blit(skip, (WIDTH//2 - skip.get_width()//2, HEIGHT - 30))

        pygame.display.flip()
        clock.tick(60)

# ── 1. MAIN MENU ──
def screen_main_menu():
    btn_start  = Button((WIDTH//2-130, HEIGHT//2-30, 260, 46), "START THE WAR")
    btn_quit   = Button((WIDTH//2-80,  HEIGHT//2+40, 160, 40), "QUIT", GRAY)
    btn_settings = Button((WIDTH-50, 20, 32, 32), "", (0,0,0,0)) # Transparent but clickable
    
    while True:
        t=pygame.time.get_ticks()/1000
        for event in pygame.event.get():
            if event.type==pygame.QUIT: pygame.quit(); sys.exit()
            if btn_start.clicked(event):  return 'start'
            if btn_quit.clicked(event):   pygame.quit(); sys.exit()
            if btn_settings.clicked(event): screen_settings()
            
        draw_background(screen,t)
        title=font_big.render("SUB SHOCKERS",True,BIOLUM)
        sub=font_small.render("DEEP SEA ARENA  ·  BIOLUMINESCENT COMBAT",True,(0,120,150))
        screen.blit(title,(WIDTH//2-title.get_width()//2, HEIGHT//2-140))
        screen.blit(sub,(WIDTH//2-sub.get_width()//2, HEIGHT//2-85))
        btn_start.draw(screen); btn_quit.draw(screen)
        
        # Gear icon
        draw_gear(screen, WIDTH-34, 36, 12, BIOLUM if btn_settings.hovered else GRAY)
        
        pygame.display.flip(); clock.tick(60)

def screen_settings():
    vol_levels = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    btn_back = Button((WIDTH//2-60, HEIGHT//2+120, 120, 32), "BACK", GRAY)
    
    while True:
        t=pygame.time.get_ticks()/1000
        for event in pygame.event.get():
            if event.type==pygame.QUIT: pygame.quit(); sys.exit()
            if btn_back.clicked(event): return
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                # Volume selector
                for i, v in enumerate(vol_levels):
                    bx = WIDTH//2 - 150 + i * 60
                    by = HEIGHT//2
                    if math.hypot(event.pos[0]-bx, event.pos[1]-by) < 20:
                        settings["music_volume"] = v
                        settings["muted"] = (v == 0)
                        update_volumes()

        draw_background(screen,t)
        title=font_med.render("SETTINGS",True,BIOLUM)
        screen.blit(title,(WIDTH//2-title.get_width()//2, HEIGHT//2-100))
        
        v_text = font_small.render(f"MUSIC VOLUME: {int(settings['music_volume']*100)}%", True, WHITE)
        screen.blit(v_text, (WIDTH//2 - v_text.get_width()//2, HEIGHT//2 - 50))
        
        for i, v in enumerate(vol_levels):
            bx = WIDTH//2 - 150 + i * 60
            by = HEIGHT//2
            color = BIOLUM if settings["music_volume"] == v else GRAY
            pygame.draw.circle(screen, color, (bx, by), 15)
            if settings["music_volume"] == v:
                pygame.draw.circle(screen, WHITE, (bx, by), 18, 2)
            
            val_txt = font_tiny.render(str(int(v*100)), True, WHITE)
            screen.blit(val_txt, (bx - val_txt.get_width()//2, by + 20))

        btn_back.draw(screen)
        pygame.display.flip(); clock.tick(60)

def screen_mode_selection():
    btn_1p = Button((WIDTH//2-130, HEIGHT//2-60, 260, 46), "1 PLAYER (vs AI)")
    btn_2p = Button((WIDTH//2-130, HEIGHT//2+10, 260, 46), "2 PLAYERS (Local)")
    btn_mp = Button((WIDTH//2-130, HEIGHT//2+80, 260, 46), "MULTIPLAYER (Online)")
    btn_back = Button((WIDTH//2-60, HEIGHT//2+150, 120, 32), "BACK", GRAY)
    
    while True:
        t=pygame.time.get_ticks()/1000
        for event in pygame.event.get():
            if event.type==pygame.QUIT: pygame.quit(); sys.exit()
            if btn_1p.clicked(event): return '1p'
            if btn_2p.clicked(event): return '2p'
            if btn_mp.clicked(event): return 'mp'
            if btn_back.clicked(event): return 'back'
            
        draw_background(screen,t)
        title=font_big.render("SELECT MODE",True,BIOLUM)
        screen.blit(title,(WIDTH//2-title.get_width()//2, HEIGHT//2-140))
        btn_1p.draw(screen); btn_2p.draw(screen); btn_mp.draw(screen); btn_back.draw(screen)
        pygame.display.flip(); clock.tick(60)

# ── GAME LOOP ────────────────────────────────────────────
def run_game(match_scores, mode='2p', net_data=None):
    global particles, ripples, net_ready, net_p2_keys, net_remote_state
    particles=[]; ripples=[]
    powerups=[]; mines=[]; guided_missiles=[]
    p1,p2=make_players()
    
    if mode == '1p': p2.is_ai = True
    
    is_mp = (net_data is not None)
    is_host = net_data.get('host', False) if is_mp else False
    room_code = net_data.get('room') if is_mp else None
    
    scores=[0,0]; game_over=False; winner=0
    next_map() # Ensure map and maze_grid are initialized

    keys_held={}; map_flash=0
    round_end_timer=0

    btn_menu=Button((WIDTH-100,HEIGHT-36,90,28),"MENU",GRAY)

    running=True
    while running:
        clock.tick(60)
        t=pygame.time.get_ticks()/1000

        # ── Events ──
        event_list = pygame.event.get()
        for event in event_list:
            if event.type==pygame.QUIT: pygame.quit(); sys.exit()
            elif event.type==pygame.KEYDOWN:
                keys_held[event.key]=True
                if (event.key==pygame.K_r or event.key==pygame.K_SPACE) and game_over:
                    return winner
                    scores=[0,0]; game_over=False; winner=0
                    round_end_timer=0
                    next_map(); map_flash=20
                    particles.clear(); ripples.clear()
                    powerups.clear(); mines.clear(); guided_missiles.clear()
                    p1,p2=make_players()
            elif event.type==pygame.KEYUP:
                keys_held[event.key]=False
            if btn_menu.clicked(event): 
                stop_sound('music_game', fade_ms=1000)
                return None

        merged_p1=keys_held; merged_p2=keys_held

        # ── Physics ──
        if not game_over:
            # Spawn powerup randomly
            if random.random() < 0.008 and len(powerups) < 4: # increased spawn
                px = random.randint(PLAY_LEFT + 20, PLAY_RIGHT - 20)
                py = random.randint(PLAY_TOP + 20, PLAY_BOTTOM - 20)
                powerups.append(Powerup(px, py))
                
            # Use powerup
            for sub, enemy in [(p1, p2), (p2, p1)]:
                keydown_use = False
                for evt in event_list:
                    if evt.type == pygame.KEYDOWN and evt.key == sub.controls['shoot']:
                        keydown_use = True
                
                if keydown_use:
                    has_active = (sub.active_missile and sub.active_missile.alive)
                    if sub.powerup and not has_active:
                        p = sub.powerup
                        sub.powerup = None
                        if p == 'mine': mines.append(Mine(sub.x, sub.y, sub.player_num, sub.color))
                        elif p == 'missile': 
                            m = GuidedMissile(sub.x, sub.y, sub.angle, sub.player_num, sub.color)
                            guided_missiles.append(m)
                            sub.active_missile = m
                        # If a powerup was just activated, consume the shoot action so they don't fire a bullet right after
                        sub.shoot_cooldown = 15
                            
            # Updates
            m1 = merged_p1
            m2 = merged_p2
            
            if mode == '1p':
                m2 = p2.get_ai_keys(p1)
            elif is_mp:
                if is_host:
                    # Host uses net_p2_keys (relayed from Guest)
                    m2 = net_p2_keys
                    # Send state to Guest
                    state = {
                        'p1': p1.to_dict(), 'p2': p2.to_dict(),
                        'powerups': [p.__dict__ for p in powerups],
                        'mines': [m.__dict__ for m in mines],
                        'scores': scores, 'winner': winner, 'game_over': game_over
                    }
                    sio.emit('update_state', {'room': room_code, 'state': state})
                else:
                    # Guest sends its local keys to Host
                    # Actually P2 controls are defined locally, so Guest sends his keys
                    my_keys = {k: merged_p1.get(k, False) for k in p2.controls.values()}
                    sio.emit('send_input', {'room': room_code, 'keys': my_keys})
                    
                    # Guest applies remote state from Host
                    if net_remote_state:
                        p1.apply_state(net_remote_state['p1'])
                        p2.apply_state(net_remote_state['p2'])
                        scores = net_remote_state['scores']
                        winner = net_remote_state['winner']
                        game_over = net_remote_state['game_over']
                        # Simplified: logic for powerups/mines could be synced too
            
            p1.update(m1); p2.update(m2)
            
            # Sub collision with powerups
            for sub, enemy in [(p1, p2), (p2, p1)]:
                if sub.alive and not sub.powerup:
                    for pu in powerups[:]:
                        if math.hypot(sub.x - pu.x, sub.y - pu.y) < 25:
                            if pu.ptype == 'speed':
                                sub.speed_timer = 300
                            elif pu.ptype == 'slow':
                                sub.slow_timer = 300
                            else:
                                sub.powerup = pu.ptype
                            play_sound('powerup')
                            powerups.remove(pu)
                            break
                            
            for pu in powerups: pu.update()
            powerups[:] = [p for p in powerups if p.life > 0]
            
            for m in mines: 
                m.update(p1, p2)
                new_bullets = m.fire_bullets()
                for b in new_bullets:
                    if m.owner == 1: p1.torpedoes.append(b)
                    else: p2.torpedoes.append(b)
            mines[:] = [m for m in mines if m.alive]
            
            guided_missiles[:] = [m for m in guided_missiles if m.alive]
            
            p1_dead,p2_dead=check_hits(p1,p2, guided_missiles)
            if (p1_dead or p2_dead) and round_end_timer == 0:
                round_end_timer = 180  # 3 seconds delay

            if round_end_timer > 0:
                round_end_timer -= 1
                if round_end_timer == 0:
                    if not p2.alive and p1.alive: scores[0]+=1
                    elif not p1.alive and p2.alive: scores[1]+=1
                    next_map(); map_flash=18
                    particles.clear(); ripples.clear()
                    powerups.clear(); mines.clear(); guided_missiles.clear()
                    p1.respawn()
                    p2.respawn()
                    if scores[0]>=WIN_SCORE: game_over=True; winner=1
                    elif scores[1]>=WIN_SCORE: game_over=True; winner=2

            for r in ripples: r.update()
            for pt in particles: pt.update()
            ripples[:]=[r for r in ripples if r.life>0]
            particles[:]=[pt for pt in particles if pt.life>0]

        if map_flash>0: map_flash-=1

        # ── Draw ──
        draw_background(screen,t)
        draw_border(screen,t); draw_walls(screen,t); draw_ocean_floor(screen)
        for pu in powerups: pu.draw(screen)
        for m in mines: m.draw(screen)
        for r in ripples: r.draw(screen)
        for pt in particles: pt.draw(screen)
        p1.draw(screen); p2.draw(screen)
        for m in guided_missiles: m.draw(screen)
        draw_vignette(screen)
        draw_hud(screen,scores[0],scores[1],p1,p2, match_scores)
        draw_map_flash(screen,map_flash*12)
        if round_end_timer > 0 and not game_over:
            secs_left = math.ceil(round_end_timer / 60.0)
            txt = font_big.render(f"NEXT ROUND IN {secs_left}", True, (255, 200, 50))
            screen.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2 - 20))
        if game_over: draw_win_screen(screen,winner)
        btn_menu.draw(screen)
        pygame.display.flip()

# Music helper (deleted duplication)

# ── Main app flow ─────────────────────────────────────────────────────────────
def main():
    screen_splash()
    intro_animation()
    
    while True:
        play_music('music_menu', loops=-1) # Menu music loops on homepage
        choice = screen_main_menu()
        if choice == 'start':
            mode = screen_mode_selection()
            if mode == 'back': continue
            
            net_data = None
            if mode == 'mp':
                net_data = screen_multiplayer_lobby()
                if net_data is None: continue
            
            match_scores = [0, 0]
            war_over = False
            war_winner = 0
            play_music('music_game', loops=-1) # Start match music
            while not war_over:
                round_winner = run_game(match_scores, mode=mode, net_data=net_data)
                if round_winner == 1: match_scores[0] += 1
                elif round_winner == 2: match_scores[1] += 1
                else: break
                
                if match_scores[0] >= 2:
                    war_over = True; war_winner = 1
                elif match_scores[1] >= 2:
                    war_over = True; war_winner = 2
                    
            if war_over:
                showing_grand = True
                while showing_grand:
                    clock.tick(60)
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT: pygame.quit(); sys.exit()
                        if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                            showing_grand = False
                    draw_grand_winner(screen, war_winner)
                    pygame.display.flip()

if __name__=='__main__':
    main()