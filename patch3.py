import re

with open('game.py', 'r', encoding='utf-8') as f:
    code = f.read()

win_screen_code = '''def draw_grand_winner(surf, player_num):
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
'''

code = code.replace('def draw_win_screen(surf,player_num):', win_screen_code + '\ndef draw_win_screen(surf,player_num):')

code = code.replace('if event.key==pygame.K_r and game_over:', 'if event.key==pygame.K_r and game_over:\n                    return winner')

main_code = '''# ── Main app flow ─────────────────────────────────────────────────────────────
def main():
    screen_intro_animation()
    while True:
        choice=screen_main_menu()
        if choice=='local':
            match_scores = [0, 0]
            war_over = False
            war_winner = 0
            while not war_over:
                round_winner = run_game(match_scores)
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

if __name__=='''

code = re.sub(r'# ── Main app flow ──.*?if __name__==', main_code, code, flags=re.DOTALL)

# Modify run_game signature and return value
code = code.replace('def run_game():', 'def run_game(match_scores):')
code = code.replace('if btn_menu.clicked(event): return', 'if btn_menu.clicked(event): return None')

# Add match score display to HUD
hud_code = '''def draw_hud(surf,s1,s2,p1_sub,p2_sub, match_scores=None):
    hud=pygame.Surface((WIDTH,44),pygame.SRCALPHA)
    pygame.draw.rect(hud,(1,8,16,220),(0,0,WIDTH,44))
    pygame.draw.line(hud,(*BIOLUM,70),(0,43),(WIDTH,43),1)
    surf.blit(hud,(0,0))
    title=font_med.render("SUB TROUBLE",True,BIOLUM)
    surf.blit(title,(WIDTH//2-title.get_width()//2,10))
    if match_scores is not None:
        m_txt = font_tiny.render(f"WAR: {match_scores[0]} - {match_scores[1]}  (First to 2)", True, (150, 150, 150))
        surf.blit(m_txt,(WIDTH//2-m_txt.get_width()//2, 30))
        
    surf.blit(font_small.render("ANGLER",True,(*P1_COLOR,180)),(55,4))
    surf.blit(font_big.render(str(s1),True,P1_COLOR),(55,16))'''

code = re.sub(r'def draw_hud\(.*?surf\.blit\(font_big\.render\(str\(s1\),True,P1_COLOR\),\(55,16\)\)', hud_code, code, flags=re.DOTALL)
code = code.replace('draw_hud(screen,scores[0],scores[1],p1,p2)', 'draw_hud(screen,scores[0],scores[1],p1,p2, match_scores)')

with open('game.py', 'w', encoding='utf-8') as f:
    f.write(code)
print('Done round logic')
