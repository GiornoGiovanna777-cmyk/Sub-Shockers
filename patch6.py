import re

with open('game.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update powerup usage to use the SHOOT key ('q' or 'm') instead of USE key ('e' or 'shift')
use_logic_repl = '''            # Use powerup
            for sub, enemy in [(p1, p2), (p2, p1)]:
                keydown_use = False
                for evt in event_list:
                    if evt.type == pygame.KEYDOWN and evt.key == sub.controls['shoot']:
                        keydown_use = True
                
                if keydown_use:
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
                            sub.active_missile = m
                        # If a powerup was just activated, consume the shoot action so they don't fire a bullet right after
                        sub.shoot_cooldown = 15'''

code = re.sub(r'            # Use powerup.*?sub\.active_missile = m', use_logic_repl, code, flags=re.DOTALL)


# 2. Update Mine rendering to be a Dark Blue hexagon (and fading invisible at 0.5s instead of just slowly fading based on timer)
# Also ensuring explosion creates an expanding ring
mine_logic_repl = '''class Mine:
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
            s = pygame.Surface((30, 30), pygame.SRCALPHA)
            # Draw dark blue hexagon
            pygame.draw.polygon(s, (10, 30, 100, alpha), [(15, 0), (30, 8), (30, 22), (15, 30), (0, 22), (0, 8)])
            pygame.draw.polygon(s, (20, 50, 150, alpha), [(15, 0), (30, 8), (30, 22), (15, 30), (0, 22), (0, 8)], 2)
            
            # Draw pulsing red light in middle when detonating
            if self.detonating > 0:
                pygame.draw.circle(s, (255,50,50,alpha), (15,15), 5)
            surf.blit(s, (cx-15, cy-15))'''

code = re.sub(r'class Mine:.*?(?=class GuidedMissile:)', mine_logic_repl + '\n', code, flags=re.DOTALL)

with open('game.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Mine tweaks generated.")
