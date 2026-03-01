import re

with open('game.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Remove NetClient class
code = re.sub(r'# ── Network client wrapper ──.*?net = NetClient\(\)\n', '', code, flags=re.DOTALL)

# Remove screen_online_lobby and screen_waiting_room
code = re.sub(r'# ── 2\. ONLINE LOBBY ──.*?# ── 4\. GAME LOOP \(local or online\) ──', '# ── GAME LOOP ──', code, flags=re.DOTALL)

new_menu = '''def screen_main_menu():
    btn_local  = Button((WIDTH//2-130, HEIGHT//2-30, 260, 46), "PLAY LOCAL  (same keyboard)")
    btn_quit   = Button((WIDTH//2-80,  HEIGHT//2+40, 160, 40), "QUIT", GRAY)
    while True:
        t=pygame.time.get_ticks()/1000
        for event in pygame.event.get():
            if event.type==pygame.QUIT: pygame.quit(); sys.exit()
            if btn_local.clicked(event):  return 'local'
            if btn_quit.clicked(event):   pygame.quit(); sys.exit()
        draw_background(screen,t)
        title=font_big.render("SUB TROUBLE",True,BIOLUM)
        sub=font_small.render("DEEP SEA ARENA  ·  BIOLUMINESCENT COMBAT",True,(0,120,150))
        screen.blit(title,(WIDTH//2-title.get_width()//2, HEIGHT//2-140))
        screen.blit(sub,(WIDTH//2-sub.get_width()//2, HEIGHT//2-85))
        btn_local.draw(screen); btn_quit.draw(screen)
        pygame.display.flip(); clock.tick(60)'''

code = re.sub(r'def screen_main_menu\(\):.*?# ── GAME LOOP ──', new_menu + '\n\n# ── GAME LOOP ──', code, flags=re.DOTALL)

code = re.sub(r'def screen_error\(.*?# ── Main app', '# ── Main app', code, flags=re.DOTALL)

new_main = '''def main():
    while True:
        choice=screen_main_menu()
        if choice=='local':
            run_game()

if __name__=='__main__':
    main()'''
code = re.sub(r'def main\(\):.*', new_main, code, flags=re.DOTALL)

code = re.sub(r'def run_game\(mode\):.*?global particles, ripples', 'def run_game():\n    global particles, ripples', code, flags=re.DOTALL)
code = re.sub(r'    # For online.*?\n    btn_menu=Button', '    btn_menu=Button', code, flags=re.DOTALL)

code = re.sub(r'        if net\.opponent_left.*?# ── Network I/O ──.*?else:\n            merged_p1=keys_held; merged_p2=keys_held\n\n        # ── Physics \(host / local\) ──', '        merged_p1=keys_held; merged_p2=keys_held\n\n        # ── Physics ──', code, flags=re.DOTALL)

code = re.sub(r'        # Send state if host in online mode.*?# ── Draw ──', '        # ── Draw ──', code, flags=re.DOTALL)

code = code.replace('round_end_timer = 360  # 6 seconds delay', 'round_end_timer = 180  # 3 seconds delay')

with open('game.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Done patching game.py")
