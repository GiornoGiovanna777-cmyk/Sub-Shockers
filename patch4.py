import re
import random
import math

with open('game.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update Sub.__init__
init_repl = '''    def __init__(self,x,y,controls,player_num):
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
        self.active_missile=None'''
code = re.sub(r'    def __init__\(self,x,y,controls,player_num\):.*?self\._respawn_timer=0', init_repl, code, flags=re.DOTALL)

# 2. Update Sub.respawn
resp_repl = '''    def respawn(self):
        self.x,self.y=self.sx,self.sy; self.angle=self.sa; self.speed=0.0
        self.torpedoes=[]; self.alive=True; self.shoot_cooldown=0
        self.shield_timer=self.SHIELD_DUR; self._respawn_timer=0
        self.powerup=None; self.speed_timer=0; self.slow_timer=0
        self.active_missile=None'''
code = re.sub(r'    def respawn\(self\):.*?self\._respawn_timer=0', resp_repl, code, flags=re.DOTALL)

# 3. Update Sub.update for forward/backward
update_repl = '''    def update(self,keys):
        if self.shield_timer>0: self.shield_timer-=1
        if self.reload_timer>0:
            self.reload_timer-=1
            if self.reload_timer==0: self.bullet_count=0
        
        if self.speed_timer>0: self.speed_timer-=1
        if self.slow_timer>0: self.slow_timer-=1
        
        # Guided missile control logic
        if self.active_missile and self.active_missile.alive:
            self.speed *= self.FRICTION
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
            base_max_fwd += 1.0; base_max_bwd += 1.0
        if self.slow_timer > 0:
            base_max_fwd = max(0.5, base_max_fwd - 1.0); base_max_bwd = max(0.5, base_max_bwd - 1.0)
            
        if keys.get(self.controls['up']):
            self.speed=min(self.speed+base_accel, base_max_fwd)
        elif keys.get(self.controls['down']):
            self.speed=max(self.speed-base_accel, -base_max_bwd)
        else:'''
code = re.sub(r'    def update\(self,keys\):.*?        else:', update_repl, code, flags=re.DOTALL)

# 4. Add classes Powerup, Mine, GuidedMissile
classes_code = '''
# ── Powerups & Entities ──────────────────────────────────────────────────────
class Powerup:
    TYPES = ['speed', 'slow', 'mine', 'missile']
    COLORS = {'speed': (50, 255, 50), 'slow': (255, 50, 50), 'mine': (200, 100, 0), 'missile': (200, 0, 255)}
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.ptype = random.choice(self.TYPES)
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
            font_tiny.set_bold(True)
            txt = font_tiny.render('M', True, self.color)
            surf.blit(txt, txt.get_rect(center=(cx, cy)))
            font_tiny.set_bold(False)

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
                if sub.alive and self.life >= 30: # active after 0.5s
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
        if self.life < 30:
            alpha = int((1.0 - self.life/30.0) * 255)
        elif self.detonating > 0:
            alpha = 255 if (self.detonating // 4) % 2 == 0 else 50
        else:
            alpha = 0 # Invisible!
            
        if alpha > 0:
            cx, cy = int(self.x), int(self.y)
            s = pygame.Surface((20, 20), pygame.SRCALPHA)
            pygame.draw.polygon(s, (*self.color, alpha), [(6,1),(14,1),(19,10),(14,19),(6,19),(1,10)], 2)
            pygame.draw.circle(s, (255,50,50,alpha), (10,10), 3)
            surf.blit(s, (cx-10, cy-10))

class GuidedMissile:
    def __init__(self, x, y, angle, owner, color):
        self.x, self.y = float(x), float(y)
        self.angle = angle
        self.owner = owner
        self.color = color
        self.speed = 4.0
        self.life = 15 * 60 # 15s
        self.alive = True
        self.trail = []
        
    def update_control(self, keys, controls):
        self.life -= 1
        if self.life <= 0: self.alive = False; return
        if keys.get(controls['left']): self.angle -= 0.08
        if keys.get(controls['right']): self.angle += 0.08
        
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed
        
        self.trail.append((self.x, self.y))
        if len(self.trail) > 15: self.trail.pop(0)
        
        # Check walls
        for (ax,ay,bx,by) in get_maze():
            res = ray_vs_seg(self.x, self.y, math.cos(self.angle)*self.speed, math.sin(self.angle)*self.speed, ax,ay,bx,by)
            if res and res[0] <= 1.0:
                self.alive = False
                spawn_particles(self.x, self.y, self.color, 15)
                return
        
        if self.x<PLAY_LEFT+5 or self.x>PLAY_RIGHT-5 or self.y<PLAY_TOP+5 or self.y>PLAY_BOTTOM-5:
            self.alive = False
            spawn_particles(self.x, self.y, self.color, 15)

    def draw(self, surf):
        for i,(tx,ty) in enumerate(self.trail):
            frac=i/max(len(self.trail),1); r=max(1,int(frac*4))
            s=pygame.Surface((r*2+2,r*2+2),pygame.SRCALPHA)
            pygame.draw.circle(s,(*self.color,int(frac*200)),(r+1,r+1),r)
            surf.blit(s,(int(tx)-r-1,int(ty)-r-1))
        
        cx, cy = int(self.x), int(self.y)
        pygame.draw.circle(surf, WHITE, (cx, cy), 5)
        pygame.draw.circle(surf, self.color, (cx, cy), 7, 2)
'''

code = code.replace('# ── Sub ──────────────────────────────────────────────────────────────────────', classes_code + '\n# ── Sub ──────────────────────────────────────────────────────────────────────')

# 5. Add globals to run_game
run_game_glob = '''def run_game(match_scores):
    global particles, ripples
    particles=[]; ripples=[]
    powerups=[]; mines=[]; guided_missiles=[]'''
code = code.replace('def run_game(match_scores):\n    global particles, ripples\n    particles=[]; ripples=[]', run_game_glob)

# 6. Spawn and process powerups / items
loop_physics_repl = '''        # ── Physics ──
        if not game_over:
            # Spawn powerup randomly
            if random.random() < 0.005 and len(powerups) < 3: # rare spawn
                px = random.randint(PLAY_LEFT + 20, PLAY_RIGHT - 20)
                py = random.randint(PLAY_TOP + 20, PLAY_BOTTOM - 20)
                powerups.append(Powerup(px, py))
                
            # Use powerup
            for sub, enemy in [(p1, p2), (p2, p1)]:
                # Detect keydown for USE instead of checking keys_held continuously
                keydown_use = False
                for evt in event_list:
                    if evt.type == pygame.KEYDOWN and evt.key == sub.use_key:
                        keydown_use = True
                
                if keydown_use:
                    if sub.powerup and not (sub.active_missile and sub.active_missile.alive):
                        p = sub.powerup
                        sub.powerup = None
                        if p == 'speed': sub.speed_timer = 240
                        elif p == 'slow': enemy.slow_timer = 240
                        elif p == 'mine': mines.append(Mine(sub.x, sub.y, sub.player_num, sub.color))
                        elif p == 'missile': 
                            m = GuidedMissile(sub.x, sub.y, sub.angle, sub.player_num, sub.color)
                            guided_missiles.append(m)
                            sub.active_missile = m
                            
            # Updates
            p1.update(merged_p1); p2.update(merged_p2)
            
            # Sub collision with powerups
            for sub in [p1, p2]:
                if sub.alive and not sub.powerup:
                    for pu in powerups[:]:
                        if math.hypot(sub.x - pu.x, sub.y - pu.y) < 25:
                            sub.powerup = pu.ptype
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
            
            p1_dead,p2_dead=check_hits(p1,p2, guided_missiles)'''
# Need to capture event_list from earlier
code = code.replace('        # ── Events ──\n        for event in pygame.event.get():', '        # ── Events ──\n        event_list = pygame.event.get()\n        for event in event_list:')
code = re.sub(r'        # ── Physics ──.*?p1_dead,p2_dead=check_hits\(p1,p2\)', loop_physics_repl, code, flags=re.DOTALL)

# Modify check_hits signature and logic
check_hits_repl = '''def check_hits(p1,p2, guided_missiles):
    p1_dead=False; p2_dead=False
    for sub in [p1,p2]:
        for torp in list(sub.torpedoes):
            if sub.is_shielded(): continue
            if sub.alive and math.hypot(torp.x-sub.x,torp.y-sub.y)<20:
                torp.alive=False; sub.alive=False
                spawn_particles(sub.x,sub.y,sub.color,35)
                spawn_particles(sub.x,sub.y,WHITE,12)
                ripples.append(Ripple(sub.x,sub.y,sub.color))
                if sub.player_num==1: p1_dead=True
                else: p2_dead=True
        # Check guided missiles
        if not sub.is_shielded() and sub.alive:
            for m in guided_missiles:
                if math.hypot(m.x-sub.x,m.y-sub.y)<20:
                    m.alive=False; sub.alive=False
                    spawn_particles(sub.x,sub.y,sub.color,35)
                    spawn_particles(sub.x,sub.y,WHITE,12)
                    ripples.append(Ripple(sub.x,sub.y,sub.color))
                    if sub.player_num==1: p1_dead=True
                    else: p2_dead=True'''
code = re.sub(r'def check_hits\(p1,p2\):.*?else: p2_dead=True\n', check_hits_repl + '\n', code, flags=re.DOTALL)

# Modify check_hits call inside loop if needed
# (Already replaced earlier in loop_physics_repl)

# Add clear of lists in map change
clear_repl = '''                    next_map(); map_flash=18
                    particles.clear(); ripples.clear()
                    powerups.clear(); mines.clear(); guided_missiles.clear()'''
code = code.replace('                    next_map(); map_flash=18\n                    particles.clear(); ripples.clear()', clear_repl)

clear_repl2 = '''                    next_map(); map_flash=20
                    particles.clear(); ripples.clear()
                    powerups.clear(); mines.clear(); guided_missiles.clear()'''
code = code.replace('                    next_map(); map_flash=20\n                    particles.clear(); ripples.clear()', clear_repl2)

# 7. Draw powerups
draw_repl = '''        draw_border(screen,t); draw_walls(screen,t); draw_ocean_floor(screen)
        for pu in powerups: pu.draw(screen)
        for m in mines: m.draw(screen)
        for r in ripples: r.draw(screen)
        for pt in particles: pt.draw(screen)
        p1.draw(screen); p2.draw(screen)
        for m in guided_missiles: m.draw(screen)'''
code = code.replace('        draw_border(screen,t); draw_walls(screen,t); draw_ocean_floor(screen)\n        for r in ripples: r.draw(screen)\n        for pt in particles: pt.draw(screen)\n        p1.draw(screen); p2.draw(screen)', draw_repl)

# 8. Draw HUD items
hud_items_repl = '''    surf.blit(font_big.render(str(s1),True,P1_COLOR),(55,16))
    if p1_sub.powerup: surf.blit(font_small.render(f"[{p1_sub.powerup.upper()}] (E)", True, P1_COLOR), (75, 2))
    _draw_bullet_bar(surf,p1_sub,100,22)
    surf.blit(font_small.render("VIPER",True,(*P2_COLOR,180)),(WIDTH-100,4))
    surf.blit(font_big.render(str(s2),True,P2_COLOR),(WIDTH-55,16))
    if p2_sub.powerup: surf.blit(font_small.render(f"[{p2_sub.powerup.upper()}] (SHIFT)", True, P2_COLOR), (WIDTH-180, 2))
    _draw_bullet_bar(surf,p2_sub,WIDTH-170,22)'''
code = re.sub(r'    surf\.blit\(font_big\.render\(str\(s1\),True,P1_COLOR\),\(55,16\)\).*?_draw_bullet_bar\(surf,p2_sub,WIDTH-170,22\)', hud_items_repl, code, flags=re.DOTALL)

with open('game.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Finished patching powerups")
