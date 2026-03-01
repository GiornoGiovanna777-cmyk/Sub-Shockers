import re

with open('game.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update powerup pickup logic
pickup_repl = '''            # Sub collision with powerups
            for sub, enemy in [(p1, p2), (p2, p1)]:
                if sub.alive and not sub.powerup:
                    for pu in powerups[:]:
                        if math.hypot(sub.x - pu.x, sub.y - pu.y) < 25:
                            if pu.ptype == 'speed':
                                sub.speed_timer = 300
                            elif pu.ptype == 'slow':
                                enemy.slow_timer = 300
                            else:
                                sub.powerup = pu.ptype
                            powerups.remove(pu)
                            break'''

code = re.sub(r'            # Sub collision with powerups\n\s+for sub in \[p1, p2\]:\n\s+if sub\.alive and not sub\.powerup:\n\s+for pu in powerups\[:\]:\n\s+if math\.hypot\(sub\.x - pu\.x, sub\.y - pu\.y\) < 25:\n\s+sub\.powerup = pu\.ptype\n\s+powerups\.remove\(pu\)\n\s+break', pickup_repl, code, flags=re.DOTALL)


# 2. Remove speed and slow from manual usage logic
usage_repl = '''            # Use powerup
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
                        # If a powerup was just activated, consume the shoot action so they don't fire a bullet right after
                        sub.shoot_cooldown = 15'''

code = re.sub(r'            # Use powerup.*?sub\.shoot_cooldown = 15\n\s+# If a powerup was just activated, consume the shoot action so they don\'t fire a bullet right after\n\s+sub\.shoot_cooldown = 15', usage_repl, code, flags=re.DOTALL)


# 3. Add grace period for missile hitting its owner during launch
hits_repl = '''        # Check guided missiles
        if not sub.is_shielded() and sub.alive:
            for m in guided_missiles:
                if math.hypot(m.x-sub.x,m.y-sub.y)<20:
                    if sub.player_num == m.owner and m.life > 570: # Safe for first 0.5s
                        continue
                    m.alive=False; sub.alive=False
                    spawn_particles(sub.x,sub.y,sub.color,35)
                    spawn_particles(sub.x,sub.y,WHITE,12)
                    ripples.append(Ripple(sub.x,sub.y,sub.color))
                    if sub.player_num==1: p1_dead=True
                    else: p2_dead=True'''

code = re.sub(r'        # Check guided missiles\n\s+if not sub\.is_shielded\(\) and sub\.alive:\n\s+for m in guided_missiles:\n\s+if math\.hypot\(m\.x-sub\.x,m\.y-sub\.y\)<20:\n\s+m\.alive=False; sub\.alive=False\n\s+spawn_particles\(sub\.x,sub\.y,sub\.color,35\)\n\s+spawn_particles\(sub\.x,sub\.y,WHITE,12\)\n\s+ripples\.append\(Ripple\(sub\.x,sub\.y,sub\.color\)\)\n\s+if sub\.player_num==1: p1_dead=True\n\s+else: p2_dead=True', hits_repl, code, flags=re.DOTALL)


with open('game.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Auto-activation & Invulnerability applied.")
