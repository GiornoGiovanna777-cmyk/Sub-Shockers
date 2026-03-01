import re
import os

with open('game.py', 'r', encoding='utf-8') as f:
    code = f.read()

intro_code = '''
# ── Intro Animation ─────────────────────────────────────────────────────────────
def screen_intro_animation():
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
            # Skip animation on click or key
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                return
        
        # 12 seconds total animation
        if elapsed > 12.0:
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
            # Appear one-by-one
            line_appear_time = i * 1.5
            if elapsed > line_appear_time:
                alpha = min((elapsed - line_appear_time) * 255, 255)
                # Fade out older lines slightly
                if elapsed > line_appear_time + 4:
                    alpha = max(255 - (elapsed - (line_appear_time + 4)) * 120, 0)
                
                if alpha > 0:
                    text_surf = font_med.render(line, True, (0, 255, 231))
                    text_surf.set_alpha(int(alpha))
                    screen.blit(text_surf, (WIDTH//2 - text_surf.get_width()//2, HEIGHT//2 - 150 + i * 40))
        
        # Skip hint
        if elapsed > 2.0:
            skip = font_tiny.render("Press any key to skip", True, (100, 150, 180))
            screen.blit(skip, (WIDTH//2 - skip.get_width()//2, HEIGHT - 30))

        pygame.display.flip()
        clock.tick(60)

# ── 1. MAIN MENU ──'''

code = code.replace('# ── 1. MAIN MENU ──────────────────────────────────────────────────────────────', intro_code)
code = code.replace('def main():\n    while True:\n        choice=screen_main_menu()', 'def main():\n    screen_intro_animation()\n    while True:\n        choice=screen_main_menu()')
code = code.replace('"PLAY LOCAL  (same keyboard)"', '"START THE WAR"')

with open('game.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("done")
