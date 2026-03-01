import re

with open('game.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Fix duplicated draw_grand_winner
code = re.sub(r'(def draw_grand_winner\(surf, player_num\):.*?surf\.blit\(rt,\(WIDTH//2-rt\.get_width\(\)//2,HEIGHT//2\+120\)\)\n\n)+def draw_win_screen', 
              r'\1def draw_win_screen', code, flags=re.DOTALL)

# 2. Fix duplicated powerup initialization in Sub
code = re.sub(r'(\s+self\.powerup=None; self\.speed_timer=0; self\.slow_timer=0\n\s+self\.active_missile=None)+', 
              r'\n        self.powerup=None; self.speed_timer=0; self.slow_timer=0\n        self.active_missile=None\n', code)

# 3. Fix duplicated lists clear in game loop
code = re.sub(r'(\s+powerups\.clear\(\); mines\.clear\(\); guided_missiles\.clear\(\))+', 
              r'\n                    powerups.clear(); mines.clear(); guided_missiles.clear()', code)

# 4. Fix duplicated lists init
code = re.sub(r'(\s+powerups=\[\]; mines=\[\]; guided_missiles=\[\])+', 
              r'\n    powerups=[]; mines=[]; guided_missiles=[]', code)

# 5. Fix return winner duplicate
code = re.sub(r'(\s+return winner)+', r'\n                    return winner', code)

# 6. Apply Tweaks to Speed multipliers & Durations (5 sec = 300 frames)
# Replace update logic for speed timers
update_repl = '''    def update(self,keys):
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
        else:'''
code = re.sub(r'    def update\(self,keys\):.*?        else:', update_repl, code, flags=re.DOTALL)


# 7. Tweak Mine timers
# Fades OUT after 0.5s (30 logic steps). Activated after 2s (120 logic steps).
mine_logic = '''class Mine:
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
        if self.life < 30: # Fades out over 0.5s
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
            surf.blit(s, (cx-10, cy-10))'''
code = re.sub(r'class Mine:.*?(?=class GuidedMissile:)', mine_logic + '\n', code, flags=re.DOTALL)


# 8. Tweak Powerup icons to Rocket, and ensure strict "one active at a time"
missile_icon = '''        elif self.ptype == 'missile':
            # Rocket icon
            pygame.draw.polygon(surf, self.color, [(cx,cy-8), (cx-4,cy+6), (cx,cy+4), (cx+4,cy+6)])'''
code = re.sub(r"        elif self\.ptype == 'missile':\n[\s\S]*?(?=\n\nclass Mine:)", missile_icon, code)


use_logic = '''                if keydown_use:
                    has_active = (sub.speed_timer > 0) or (sub.slow_timer > 0) or (sub.active_missile and sub.active_missile.alive)
                    if sub.powerup and not has_active:
                        p = sub.powerup
                        sub.powerup = None
                        if p == 'speed': sub.speed_timer = 300
                        elif p == 'slow': enemy.slow_timer = 300
                        elif p == 'mine': mines.append(Mine(sub.x, sub.y, sub.player_num, sub.color))
                        elif p == 'missile': 
                            m = GuidedMissile(sub.x, sub.y, sub.angle, sub.player_num, sub.color)
                            guided_missiles.append(m)
                            sub.active_missile = m'''
code = re.sub(r'                if keydown_use:\n\s+if sub\.powerup and not \(sub\.active_missile and sub\.active_missile\.alive\):\s+p = sub\.powerup\n\s+sub\.powerup = None\n\s+if p == \'speed\': sub\.speed_timer = 240\n\s+elif p == \'slow\': enemy\.slow_timer = 240\n\s+elif p == \'mine\': mines\.append\(Mine.*?sub\.active_missile = m', use_logic, code, flags=re.DOTALL)

with open('game.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Fixes applied.")
