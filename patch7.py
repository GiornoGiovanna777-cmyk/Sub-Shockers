import re
import math

with open('game.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update Mine logic to fade over 1.0 seconds (60 frames instead of 30)
mine_repl = '''    def draw(self, surf):
        alpha = 255
        if self.life < 60: # Fades out over 1.0s
            alpha = int((1.0 - self.life/60.0) * 255)
        elif self.detonating > 0:
            alpha = 255 if (self.detonating // 4) % 2 == 0 else 50
        else:
            alpha = 0 # Invisible!'''
code = re.sub(r'    def draw\(self, surf\):\n\s+alpha = 255\n\s+if self\.life < 30:.*?\n\s+alpha = 0 # Invisible!', mine_repl, code, flags=re.DOTALL)


# 2. Rewrite Guided Missile to last 10 seconds, bounce off walls, and use Rocket graphic
missile_repl = '''class GuidedMissile:
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
'''
code = re.sub(r'class GuidedMissile:.*?(?=\n# ── Sub ──────────────────────────────────────────────────────────────────────)', missile_repl, code, flags=re.DOTALL)

with open('game.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Missile and Mine tweaked successfully!")
