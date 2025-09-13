
import os
import json
import math
import time
import random
from collections import deque
import atexit
import pygame

# ------------------------------
# Global layout (updated per-frame)
# ------------------------------
DEFAULT_WINDOWED_SIZE = (1920, 1080)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREY = (160, 160, 160)
DARK_GREY = (80, 80, 80)
GREEN = (76, 209, 55)
RED = (235, 77, 75)
YELLOW = (250, 211, 144)
CYAN = (100, 220, 220)
PURPLE = (155, 89, 182)
ORANGE = (255, 165, 2)

SAVE_FILE = "idle_blackjack_save.json"
FPS_DEFAULT = 60

def clamp(v, lo, hi): return max(lo, min(hi, v))

def fmt_num(n):
    sign = "-" if n < 0 else ""
    n = abs(float(n))
    for unit in ["", "K", "M", "B", "T", "Qa", "Qi"]:
        if n < 1000.0:
            if n >= 100:
                return f"{sign}{int(n)}{unit}"
            return f"{sign}{n:.1f}{unit}".rstrip("0").rstrip(".")
        n /= 1000.0
    return f"{sign}{n:.1f}Sx"

def now_ts(): return int(time.time())

def draw_text(surface, text, font, color, pos, center=False):
    img = font.render(text, True, color)
    rect = img.get_rect()
    rect.center = pos if center else rect.move(pos).topleft
    if not center: rect.topleft = pos
    surface.blit(img, rect)
    return rect

def draw_text_shadow(surface, text, font, color, shadow, pos, center=False):
    off = (1, 1)
    img_s = font.render(text, True, shadow)
    rect = img_s.get_rect()
    if center: rect.center = (pos[0] + off[0], pos[1] + off[1])
    else: rect.topleft = (pos[0] + off[0], pos[1] + off[1])
    surface.blit(img_s, rect)
    return draw_text(surface, text, font, color, pos, center=center)

def draw_close(surface, rect, hover=False):
    r = pygame.Rect(rect.right - 28, rect.top + 8, 20, 20)
    bg = (28, 28, 28) if not hover else (48, 48, 48)
    pygame.draw.rect(surface, bg, r, border_radius=6)
    pygame.draw.rect(surface, WHITE, r, 1, border_radius=6)
    pygame.draw.line(surface, WHITE, (r.x+5, r.y+5), (r.right-5, r.bottom-5), 2)
    pygame.draw.line(surface, WHITE, (r.right-5, r.y+5), (r.x+5, r.bottom-5), 2)
    return r

# ------------------------------
# UI
# ------------------------------
class Button:
    def __init__(self, rect, text, font, onclick=None, key=None, tooltip=None, accent=None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.onclick = onclick
        self.key = key
        self.tooltip = tooltip
        self.enabled = True
        self.visible = True
        self.hover = False
        self.accent = accent

    def handle_event(self, event):
        if not self.visible or not self.enabled: return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos) and self.onclick: self.onclick()

    def update(self, mouse_pos, pressed_keys=None):
        self.hover = self.visible and self.rect.collidepoint(mouse_pos)
        if self.visible and self.enabled and self.key and pressed_keys:
            if pressed_keys[self.key] and self.onclick: self.onclick()

    def draw(self, surface):
        if not self.visible: return
        border = 2
        bg = (20, 20, 20) if not self.hover else (34, 34, 34)
        pygame.draw.rect(surface, bg, self.rect, border_radius=12)
        edge = self.accent if self.accent else WHITE
        if not self.enabled: edge = DARK_GREY
        pygame.draw.rect(surface, edge, self.rect, width=border, border_radius=12)
        col = WHITE if self.enabled else GREY
        tw = self.font.render(self.text, True, col)
        tr = tw.get_rect(center=self.rect.center)
        surface.blit(tw, tr)

    def draw_tooltip(self, surface, font, mouse_pos):
        if self.tooltip and self.hover:
            txt = font.render(self.tooltip, True, WHITE)
            pad = 8
            r = txt.get_rect()
            box = pygame.Rect(mouse_pos[0]+16, mouse_pos[1]+16, r.w + pad*2, r.h + pad*2)
            pygame.draw.rect(surface, (26, 26, 26), box, border_radius=8)
            pygame.draw.rect(surface, WHITE, box, width=1, border_radius=8)
            surface.blit(txt, (box.x+pad, box.y+pad))

class Particle:
    def __init__(self, x, y, color=YELLOW, speed=(60, 140), life=(0.4, 0.8), size=(2, 4)):
        self.x = x; self.y = y
        ang = random.uniform(0, 2*math.pi)
        spd = random.uniform(*speed)
        self.vx = math.cos(ang) * spd; self.vy = math.sin(ang) * spd
        self.life = random.uniform(*life); self.age = 0.0
        self.size = random.randint(size[0], size[1]); self.color = color

    def update(self, dt):
        self.age += dt; self.x += self.vx * dt; self.y += self.vy * dt
        return self.age < self.life

    def draw(self, surface):
        alpha = clamp(int(255 * (1 - self.age / self.life)), 0, 255)
        col = (*self.color, alpha)
        s = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA)
        pygame.draw.circle(s, col, (self.size, self.size), self.size)
        surface.blit(s, (int(self.x)-self.size, int(self.y)-self.size))

class Star:
    def __init__(self, w, h): self.reset(w, h)
    def reset(self, w, h):
        self.x = random.randint(0, max(1, w-1)); self.y = random.randint(0, max(1, h-1))
        self.base = random.randint(100, 200); self.phase = random.uniform(0, 2*math.pi); self.speed = random.uniform(0.2, 0.8)
    def update(self, dt): self.phase += dt * self.speed
    def draw(self, surface):
        b = clamp(self.base + int(55 * math.sin(self.phase)), 60, 255)
        s = pygame.Surface((2,2), pygame.SRCALPHA); s.fill((b, b, b, b)); surface.blit(s, (self.x, self.y))

# ------------------------------
# Game State
# ------------------------------
class GameState:
    def __init__(self, w, h):
        self.gold = 0.0; self.lifetime_gold_earned = 0.0
        self.cars = 1; self.speed_level = 1; self.payout_level = 1
        self.gold_mult_level = 0; self.autoclicker_level = 0; self.offline_level = 0
        self.sponsor_level = 0; self.blackjack_unlocked = False

        self.base_car_cost = 10; self.base_speed_cost = 20; self.base_payout_cost = 200
        self.base_auto_cost = 500; self.base_mult_cost = 2000; self.base_offline_cost = 2000
        self.cost_mul = 1.35

        self.base_ang_speed = 2.2; self.speed_scale_per_level = 0.18
        self._gps_last_gold = 0.0; self._gps_last_time = time.time(); self.gps_smoothed = 0.0

        self.autosave = True; self.enable_particles = True; self.fps_cap = FPS_DEFAULT
        self.last_save_ts = now_ts()

        self.cars_list = []; self.init_cars()
        self.achievements = {}; self.prestige_points = 0; self.laps_total = 0
        self.bj_stats = {"games": 0, "wins": 0}; self.track_type = 0
        self.notifications = deque(); self.stars = [Star(w, h) for _ in range(160)]
        self._autosave_accum = 0.0

    def gold_per_all_cars_rev(self):
        return self.gold_per_lap() * self.cars

    def re_seed_stars(self, w, h): self.stars = [Star(w, h) for _ in range(160)]
    def init_cars(self):
        self.cars_list.clear()
        for _ in range(self.cars):
            t = random.uniform(0, 2*math.pi)
            col = (random.randint(170,255), random.randint(170,255), random.randint(170,255))
            size = random.randint(8, 13); var = random.uniform(0.9, 1.15)
            self.cars_list.append({"t": t, "col": col, "size": size, "var": var, "boost":0.0, "cooldown":random.uniform(0.5,2.5), "trail": deque(maxlen=24)})

    def get_car_cost(self): return int(self.base_car_cost * (self.cost_mul ** (self.cars - 1)))
    def get_speed_cost(self): return int(self.base_speed_cost * (self.cost_mul ** (self.speed_level - 1)))
    def get_payout_cost(self): return int(self.base_payout_cost * (self.cost_mul ** (self.payout_level - 1)))
    def get_auto_cost(self): return int(self.base_auto_cost * (self.cost_mul ** (self.autoclicker_level)))
    def get_mult_cost(self): return int(self.base_mult_cost * (self.cost_mul ** (self.gold_mult_level)))
    def get_offline_cost(self): return int(self.base_offline_cost * (self.cost_mul ** (self.offline_level)))

    def gold_multiplier_total(self):
        payout_bonus = (1 + 0.25*(self.payout_level - 1))
        sponsor_bonus = (1 + 0.5*self.sponsor_level)
        prestige_point_bonus = (1 + 0.05*self.prestige_points)
        gold_mult_bonus = (2 ** self.gold_mult_level)
        return payout_bonus * sponsor_bonus * prestige_point_bonus * gold_mult_bonus

    def gold_per_lap(self): return 1.0 * self.gold_multiplier_total()
    def ang_speed(self): return self.base_ang_speed * (1 + self.speed_scale_per_level*(self.speed_level - 1))
    def laps_per_sec_per_car(self): return self.ang_speed() / (2*math.pi)
    def auto_gold_per_sec(self): return self.autoclicker_level * 1.0 * self.gold_multiplier_total()

    def add_car(self):
        cost = self.get_car_cost()
        if self.gold >= cost:
            self.gold -= cost; self.cars += 1
            t = random.uniform(0, 2*math.pi)
            col = (random.randint(170,255), random.randint(170,255), random.randint(170,255))
            size = random.randint(8, 13); var = random.uniform(0.9, 1.15)
            self.cars_list.append({"t": t, "col": col, "size": size, "var": var, "boost":0.0, "cooldown":1.5, "trail": deque(maxlen=24)})
            self.notify("Purchased a car 🚗")

    def upgrade_speed(self):
        cost = self.get_speed_cost()
        if self.gold >= cost: self.gold -= cost; self.speed_level += 1; self.notify("Speed upgraded ⚡")
    def upgrade_payout(self):
        cost = self.get_payout_cost()
        if self.gold >= cost: self.gold -= cost; self.payout_level += 1; self.notify("Track Ads improved 💰")
    def upgrade_auto(self):
        cost = self.get_auto_cost()
        if self.gold >= cost: self.gold -= cost; self.autoclicker_level += 1; self.notify("Auto-Clicker upgraded 🤖")
    def upgrade_multiplier(self):
        cost = self.get_mult_cost()
        if self.gold >= cost: self.gold -= cost; self.gold_mult_level += 1; self.notify("Gold Multiplier +1 (x2) ✨")
    def upgrade_offline(self):
        cost = self.get_offline_cost()
        if self.gold >= cost: self.gold -= cost; self.offline_level += 1; self.notify("Offline Earnings boosted ⏱️")

    def award_lap(self, amount=None):
        g = amount if amount is not None else self.gold_per_lap()
        self.gold += g; self.lifetime_gold_earned += g; self.laps_total += 1
        if not self.blackjack_unlocked and self.gold >= 1000: self.blackjack_unlocked = True

    def prestige_available(self): return self.gold >= 1_000_000
    def do_prestige(self):
        if self.prestige_available():
            self.sponsor_level += 1
            self.gold = 0.0; self.cars = 1; self.speed_level = 1; self.payout_level = 1
            self.gold_mult_level = 0; self.autoclicker_level = 0
            self.init_cars(); self.notify(f"Prestiged! Sponsor level {self.sponsor_level} 🏆")

    def unlock_achievement(self, name, pp=1):
        if name not in self.achievements or not self.achievements[name]["unlocked"]:
            self.achievements[name] = {"unlocked": True, "pp_awarded": True}
            self.prestige_points += pp; self.notify(f"Achievement: {name} (+{pp} PP) 🥇")

    def check_achievements(self):
        checks = [
            ("First Steps", self.gold >= 10, 1),
            ("Lap 10", self.laps_total >= 10, 1),
            ("Fleet of 5", self.cars >= 5, 1),
            ("Speedster", self.speed_level >= 5, 1),
            ("Ad Mogul", self.payout_level >= 5, 1),
            ("Auto Tactician", self.autoclicker_level >= 5, 1),
            ("Multiplier Maniac", self.gold_mult_level >= 3, 1),
            ("Trailblazer", self.laps_total >= 500, 2),
            ("Tycoon", self.gold >= 100_000, 1),
            ("Millionaire", self.gold >= 1_000_000, 2),
            ("Card Shark", self.bj_stats.get("wins",0) >= 10, 2),
            ("Collector", self.cars >= 10, 1),
        ]
        for name, cond, pp in checks:
            if cond: self.unlock_achievement(name, pp=pp)

    def to_dict(self):
        return {
            "gold": self.gold, "lifetime_gold_earned": self.lifetime_gold_earned, "cars": self.cars,
            "speed_level": self.speed_level, "payout_level": self.payout_level, "gold_mult_level": self.gold_mult_level,
            "autoclicker_level": self.autoclicker_level, "offline_level": self.offline_level, "sponsor_level": self.sponsor_level,
            "blackjack_unlocked": self.blackjack_unlocked, "last_save_ts": now_ts(), "achievements": self.achievements,
            "prestige_points": self.prestige_points, "laps_total": self.laps_total, "bj_stats": self.bj_stats,
            "autosave": self.autosave, "enable_particles": self.enable_particles, "fps_cap": self.fps_cap, "track_type": self.track_type,
        }
    def from_dict(self, d):
        self.gold = float(d.get("gold", 0.0)); self.lifetime_gold_earned = float(d.get("lifetime_gold_earned", 0.0))
        self.cars = int(d.get("cars", 1)); self.speed_level = int(d.get("speed_level", 1)); self.payout_level = int(d.get("payout_level", 1))
        self.gold_mult_level = int(d.get("gold_mult_level", 0)); self.autoclicker_level = int(d.get("autoclicker_level", 0))
        self.offline_level = int(d.get("offline_level", 0)); self.sponsor_level = int(d.get("sponsor_level", 0))
        self.blackjack_unlocked = bool(d.get("blackjack_unlocked", False)); self.laps_total = int(d.get("laps_total", 0))
        self.achievements = d.get("achievements", {}); self.prestige_points = int(d.get("prestige_points", 0))
        self.bj_stats = d.get("bj_stats", {"games":0,"wins":0})
        self.autosave = bool(d.get("autosave", True)); self.enable_particles = bool(d.get("enable_particles", True))
        self.fps_cap = int(d.get("fps_cap", FPS_DEFAULT)); self.track_type = int(d.get("track_type", 0))
        self.init_cars()
    def save(self, path=SAVE_FILE):
        with open(path, "w", encoding="utf-8") as f: json.dump(self.to_dict(), f, indent=2)
    def load(self, path=SAVE_FILE):
        if not os.path.exists(path): return False, 0
        try:
            with open(path, "r", encoding="utf-8") as f: data = json.load(f)
            self.from_dict(data); prev_ts = int(data.get("last_save_ts", now_ts()))
            elapsed = max(0, now_ts() - prev_ts); cap_hours = min(24, 6 + 2*self.offline_level)
            elapsed = min(elapsed, cap_hours * 3600)
            laps_offline = elapsed * self.laps_per_sec_per_car() * self.cars
            earned = (laps_offline * self.gold_per_lap() + elapsed * self.auto_gold_per_sec()) * (1 + 0.5*self.offline_level)
            self.gold += earned
            self.lifetime_gold_earned += earned

            # NEW: show a toast-style notification with offline earnings
            try:
                self.notify(f"Welcome back! Offline earnings: +{fmt_num(int(earned))} gold", dur=4.0)
            except Exception:
                # if anything odd happens with notifications, fail silently
                pass

            return True, earned
        except Exception as e:
            print("Load failed:", e); return False, 0
    def tick_autosave(self, dt):
        if not self.autosave: return False
        self._autosave_accum += dt
        if self._autosave_accum >= 30.0:
            self._autosave_accum = 0.0
            try: self.save(); self.notify("Autosaved 💾"); return True
            except Exception as e: print("Autosave failed:", e)
        return False
    def notify(self, text, dur=2.8): self.notifications.append({"text": text, "t": 0.0, "dur": dur})
    def update_notifications(self, dt):
        if not self.notifications: return
        kept = deque()
        for n in list(self.notifications):
            n["t"] += dt
            if n["t"] < n["dur"]: kept.append(n)
        self.notifications = kept
    def update_gps(self):
        t = time.time(); dt = max(1e-6, t - self._gps_last_time)
        delta = self.gold - self._gps_last_gold; inst = clamp(delta / dt, -1e12, 1e12)
        alpha = 0.2; self.gps_smoothed = (1-alpha)*self.gps_smoothed + alpha*inst
        self._gps_last_gold = self.gold; self._gps_last_time = t

# ------------------------------
# Blackjack
# ------------------------------
SUITS = ["♠", "♥", "♦", "♣"]; RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
def card_value(rank): return 11 if rank=="A" else (10 if rank in ["K","Q","J"] else int(rank))
def hand_value(cards):
    total = 0; aces = 0
    for r, s in cards:
        v = card_value(r); total += v; aces += (1 if r=="A" else 0)
    while total > 21 and aces > 0: total -= 10; aces -= 1
    return total

class Blackjack:
    def __init__(self, game_state):
        self.gs = game_state; self.deck = []; self.player = []; self.dealer = []
        self.in_round = False; self.message = "Place your bet and DEAL."; self.bet = 50; self.bet_locked = 0
        self.shuffle_deck()
    def shuffle_deck(self): self.deck = [(r, s) for s in SUITS for r in RANKS] * 4; random.shuffle(self.deck)
    def draw_card(self):
        if not self.deck: self.shuffle_deck()
        return self.deck.pop()
    def can_deal(self): return (not self.in_round) and self.bet > 0 and self.gs.gold >= self.bet
    def deal(self):
        if not self.can_deal(): self.message = "Not enough gold or invalid bet."; return
        self.in_round = True; self.player = [self.draw_card(), self.draw_card()]; self.dealer = [self.draw_card(), self.draw_card()]
        self.bet_locked = int(self.bet); self.gs.gold -= self.bet_locked; self.message = "Hit or Stand."
        if hand_value(self.player)==21 or hand_value(self.dealer)==21: self.resolve_naturals()
    def resolve_naturals(self):
        pv = hand_value(self.player); dv = hand_value(self.dealer)
        if pv==21 and dv!=21: self.payout(2*self.bet_locked, "Blackjack! You win."); self.gs.bj_stats["games"]+=1; self.gs.bj_stats["wins"]+=1
        elif pv==21 and dv==21: self.payout(1*self.bet_locked, "Push. Bet returned."); self.gs.bj_stats["games"]+=1
        elif dv==21 and pv!=21: self.message = "Dealer blackjack. You lose."; self.in_round=False; self.gs.bj_stats["games"]+=1
    def hit(self):
        if not self.in_round: return
        self.player.append(self.draw_card())
        if hand_value(self.player) > 21: self.message = "Bust! You lose."; self.in_round = False; self.gs.bj_stats["games"]+=1
    def stand(self):
        if not self.in_round: return
        while hand_value(self.dealer) < 17: self.dealer.append(self.draw_card())
        dv = hand_value(self.dealer); pv = hand_value(self.player); self.gs.bj_stats["games"]+=1
        if dv > 21 or pv > dv: self.payout(2*self.bet_locked, "You win."); self.gs.bj_stats["wins"]+=1
        elif pv == dv: self.payout(1*self.bet_locked, "Push. Bet returned.")
        else: self.message = "You lose."
        self.in_round = False
    def payout(self, amount, msg): self.gs.gold += amount; self.gs.lifetime_gold_earned += amount; self.message = msg; self.in_round = False
    def change_bet(self, d):
        if self.in_round: return
        self.bet = clamp(self.bet + d, 10, min(100000, int(self.gs.gold) + 10000))

# ------------------------------
# Track & layout helpers
# ------------------------------
def panel_w_for(w): return clamp(int(w * 0.22), 380, 560)
def center_for(w, h, panel_w): return ((w - panel_w)//2, h//2)
def radius_for(w, h, panel_w): return int(min(max(200, w - panel_w), h) * 0.35)

def track_pos(track_type, t, radius, center):
    cx, cy = center
    if track_type == 0:
        x = cx + radius * math.cos(t); y = cy + radius * math.sin(t)
    elif track_type == 1:
        a = radius * 0.8; x = cx + a * math.sin(t); y = cy + (a * math.sin(t) * math.cos(t))
    elif track_type == 2:
        a = radius * 1.05; b = radius * 0.6; x = cx + a * math.cos(t); y = cy + b * math.sin(t)
    else:
        a = radius * 0.9; r = a * math.cos(3*t); x = cx + r * math.cos(t); y = cy + r * math.sin(t)
    return x, y

# ------------------------------
# Scenes
# ------------------------------
class SceneBase:
    def __init__(self, app): self.app = app; self.fade = 0.0; self.fade_dir = 0
    def start_fade_in(self): self.fade = 1.0; self.fade_dir = -1
    def update_fade(self, dt):
        speed = 2.5
        if self.fade_dir != 0:
            self.fade += self.fade_dir * dt * speed
            if self.fade <= 0.0: self.fade = 0.0; self.fade_dir = 0
            elif self.fade >= 1.0: self.fade = 1.0; self.fade_dir = 0
    def draw_fade(self, surface):
        if self.fade > 0.0:
            s = pygame.Surface(surface.get_size()); s.set_alpha(int(255*self.fade)); s.fill(BLACK); surface.blit(s, (0, 0))

class MainMenu(SceneBase):
    def __init__(self, app):
        super().__init__(app)
        self.title_font = app.font_huge; self.btn_font = app.font_med; self.small_font = app.font_small
        self.buttons = []; self.hue = 0.0; self.relayout()
    def relayout(self):
        w, h = self.app.screen.get_size(); bw, bh = 260, 64; cx = w//2; y = h//2 - 120; gap = 80
        self.buttons = [
            Button((cx - bw//2, y, bw, bh), "Start Game", self.btn_font, onclick=self.start_game, key=pygame.K_RETURN, accent=CYAN),
            Button((cx - bw//2, y + gap, bw, bh), "Load Game", self.btn_font, onclick=self.load_game, accent=WHITE),
            Button((cx - bw//2, y + 2*gap, bw, bh), "Options", self.btn_font, onclick=self.go_options, accent=PURPLE),
            Button((cx - bw//2, y + 3*gap, bw, bh), "Exit", self.btn_font, onclick=self.exit_game, accent=RED),
        ]
    def start_game(self):
        w, h = self.app.screen.get_size(); self.app.state = GameState(w, h); self.app.change_scene(IdleScene(self.app))
    def load_game(self):
        w, h = self.app.screen.get_size(); gs = GameState(w, h); ok, earned = gs.load(SAVE_FILE)
        self.app.state = gs if ok else GameState(w, h)
        self.app.last_load_message = f"Loaded. Offline earned: {int(earned)}." if ok else "No save found. Starting new."
        self.app.change_scene(IdleScene(self.app))
    def go_options(self): self.app.change_scene(OptionsScene(self.app))
    def exit_game(self): pygame.event.post(pygame.event.Event(pygame.QUIT))
    def update(self, dt, events):
        keys = pygame.key.get_pressed(); mouse = pygame.mouse.get_pos()
        for e in events:
            if e.type == pygame.VIDEORESIZE: self.relayout()
        for b in self.buttons:
            b.update(mouse, pressed_keys=keys)
            for e in events: b.handle_event(e)
        self.update_fade(dt); self.hue += dt * 0.2
    def draw(self, surface):
        w, h = surface.get_size()
        surface.fill(BLACK)
        for s in self.app.state.stars: s.update(1/60); s.draw(surface)
        hue = (math.sin(self.hue) * 0.5 + 0.5); col = (int(150 + 100*hue), int(150 + 100*(1-hue)), 255)
        draw_text_shadow(surface, "IDLE RACER + BLACKJACK", self.title_font, col, DARK_GREY, (w//2, 160), center=True)
        if self.app.last_load_message: draw_text(surface, self.app.last_load_message, self.small_font, GREY, (w//2, 200), center=True)
        for b in self.buttons: b.draw(surface)
        self.draw_fade(surface)

class OptionsScene(SceneBase):
    def __init__(self, app):
        super().__init__(app)
        self.title_font = app.font_big; self.btn_font = app.font_med; self.small_font = app.font_small
        self.buttons = []; self.relayout()
    def apply_size(self, size):
        # Set preferred windowed size; apply only if not fullscreen
        self.app.windowed_size = size
        if not self.app.fullscreen: self.app.apply_window_settings(size=size, fullscreen=False)
    def toggle_fullscreen(self): self.app.apply_window_settings(fullscreen=not self.app.fullscreen)
    def relayout(self):
        w, h = self.app.screen.get_size(); bw, bh = 360, 60; cx = w//2; y0 = h//2 - 180; gap = 76
        def toggle_autosave(): self.app.state.autosave = not self.app.state.autosave
        def toggle_particles(): self.app.state.enable_particles = not self.app.state.enable_particles
        def toggle_fps(): self.app.state.fps_cap = 120 if self.app.state.fps_cap == FPS_DEFAULT else FPS_DEFAULT
        # Dynamic labels will be set in update()
        self.btn_full = Button((cx - bw//2, y0, bw, bh), "", self.btn_font, onclick=self.toggle_fullscreen, accent=CYAN)
        self.btn_res_1920 = Button((cx - bw//2, y0 + gap, bw, bh), "", self.btn_font, onclick=lambda: self.apply_size((1920,1080)), accent=WHITE)
        self.btn_res_1280 = Button((cx - bw//2, y0 + 2*gap, bw, bh), "", self.btn_font, onclick=lambda: self.apply_size((1280,720)), accent=WHITE)
        self.btn_autosave = Button((cx - bw//2, y0 + 3*gap, bw, bh), "", self.btn_font, onclick=toggle_autosave, accent=CYAN)
        self.btn_particles = Button((cx - bw//2, y0 + 4*gap, bw, bh), "", self.btn_font, onclick=toggle_particles, accent=PURPLE)
        self.btn_fps = Button((cx - bw//2, y0 + 5*gap, bw, bh), "", self.btn_font, onclick=toggle_fps, accent=WHITE)
        self.btn_back = Button((cx - 180, y0 + 6*gap, 360, 64), "Back", self.btn_font, onclick=self.go_back, key=pygame.K_ESCAPE, accent=RED)
        self.buttons = [self.btn_full, self.btn_res_1920, self.btn_res_1280, self.btn_autosave, self.btn_particles, self.btn_fps, self.btn_back]
    def go_back(self): self.app.change_scene(MainMenu(self.app))
    def update(self, dt, events):
        keys = pygame.key.get_pressed(); mouse = pygame.mouse.get_pos()
        for e in events:
            if e.type == pygame.VIDEORESIZE: self.relayout()
        # Dynamic labels
        chk = "✓"; box = lambda b: f"[{chk}]" if b else "[ ]"
        self.btn_full.text = f"{box(self.app.fullscreen)} Fullscreen (F11)"
        wsize = self.app.windowed_size
        self.btn_res_1920.text = f"{box(wsize==(1920,1080))} 1920×1080 (Windowed)"
        self.btn_res_1280.text = f"{box(wsize==(1280,720))} 1280×720 (Windowed)"
        self.btn_autosave.text = f"Autosave: {'ON' if self.app.state.autosave else 'OFF'}"
        self.btn_particles.text = f"Particles: {'ON' if self.app.state.enable_particles else 'OFF'}"
        self.btn_fps.text = f"FPS Cap: {self.app.state.fps_cap} (toggle)"
        for b in self.buttons:
            b.update(mouse, pressed_keys=keys)
            for e in events: b.handle_event(e)
        self.update_fade(dt)
    def draw(self, surface):
        w, h = surface.get_size()
        surface.fill(BLACK)
        for s in self.app.state.stars: s.update(1/60); s.draw(surface)
        draw_text(surface, "OPTIONS", self.title_font, WHITE, (w//2, 150), center=True)
        for b in self.buttons: b.draw(surface)
        self.draw_fade(surface)

class IdleScene(SceneBase):
    def __init__(self, app):
        super().__init__(app)
        self.font = app.font_med; self.small_font = app.font_small; self.big_font = app.font_big
        self.particles = []; self.scroll_offset = 0.0; self.buttons = []; self.button_bases = {}
        self.click_fx = [] 
        self.show_stats = False; self.show_achievements = True
        self._ach_rect = pygame.Rect(24, 24, 340, 180); self._stats_rect = pygame.Rect(24, 860, 360, 196)
        self.offline_note = self.app.last_load_message or ""; self.app.last_load_message = ""
        self.last_canvas_size = self.app.screen.get_size(); self.relayout()
    def relayout(self):
        w, h = self.app.screen.get_size(); panel_w = panel_w_for(w)
        self.center = center_for(w, h, panel_w); self.radius = radius_for(w, h, panel_w)
        panel_x = w - panel_w; header_h = 150; footer_pad = 20
        self.buttons_view = pygame.Rect(panel_x + 20, header_h, panel_w - 40, h - header_h - footer_pad)
        px = panel_x + 20; py = header_h + 20; gap = 66; bw, bh = panel_w - 40, 52
        # Build named buttons for easier state handling
        self.btn_buy_car = Button((px, py, bw, bh), "", self.font, onclick=self.buy_car, key=pygame.K_1, tooltip="1: Buy another car.", accent=CYAN)
        self.btn_speed   = Button((px, py + gap, bw, bh), "", self.font, onclick=self.up_speed, key=pygame.K_2, tooltip="2: Increase speed.", accent=WHITE)
        self.btn_payout  = Button((px, py + 2*gap, bw, bh), "", self.font, onclick=self.up_payout, key=pygame.K_3, tooltip="3: Gold per lap.", accent=YELLOW)
        self.btn_auto    = Button((px, py + 3*gap, bw, bh), "", self.font, onclick=self.up_auto, key=pygame.K_4, tooltip="4: Auto-Clicker.", accent=GREEN)
        self.btn_mult    = Button((px, py + 4*gap, bw, bh), "", self.font, onclick=self.up_mult, key=pygame.K_5, tooltip="5: x2 per level.", accent=PURPLE)
        self.btn_offline = Button((px, py + 5*gap, bw, bh), "", self.font, onclick=self.up_offline, key=pygame.K_6, tooltip="6: Offline earnings.", accent=ORANGE)
        self.btn_track   = Button((px, py + 6*gap, bw, bh), "Change Track (T)", self.font, onclick=self.change_track, key=pygame.K_t, tooltip="Cycle tracks.", accent=CYAN)
        self.btn_bj      = Button((px, py + 7*gap, bw, bh), "BLACKJACK (B)", self.font, onclick=self.go_blackjack, key=pygame.K_b, tooltip="Unlocks at 1000 gold.", accent=WHITE)
        self.btn_stats   = Button((px, py + 8*gap, bw, bh), "Stats Overlay (V)", self.font, onclick=self.toggle_stats, key=pygame.K_v, tooltip="Show/hide statistics overlay.", accent=WHITE)
        self.btn_prest   = Button((px, py + 9*gap, bw, bh), "PRESTIGE (P)", self.font, onclick=self.do_prestige, key=pygame.K_p, tooltip="1M+ gold.", accent=RED)
        self.btn_save    = Button((px, py + 10*gap, bw, bh), "SAVE (S)", self.font, onclick=self.manual_save, key=pygame.K_s, tooltip="Force save.", accent=WHITE)
        self.btn_menu    = Button((px, py + 11*gap, bw, bh), "MAIN MENU (Esc)", self.font, onclick=self.go_main_menu, key=pygame.K_ESCAPE, tooltip="Go back to the main menu", accent=RED)
        self.buttons = [self.btn_buy_car, self.btn_speed, self.btn_payout, self.btn_auto, self.btn_mult, self.btn_offline, self.btn_track, self.btn_bj, self.btn_stats, self.btn_prest, self.btn_save, self.btn_menu]
        self.button_bases = {b: b.rect.copy() for b in self.buttons}
    # Callbacks
    def buy_car(self): self.app.state.add_car()
    def up_speed(self): self.app.state.upgrade_speed()
    def up_payout(self): self.app.state.upgrade_payout()
    def up_auto(self): self.app.state.upgrade_auto()
    def up_mult(self): self.app.state.upgrade_multiplier()
    def up_offline(self): self.app.state.upgrade_offline()
    def toggle_stats(self): self.show_stats = not self.show_stats
    def change_track(self):
        self.app.state.track_type = (self.app.state.track_type + 1) % 4
        self.app.state.notify(["Circle", "Figure-8", "Oval", "Complex"][self.app.state.track_type] + " track selected 🛣️")
    def go_blackjack(self):
        if self.app.state.blackjack_unlocked: self.app.change_scene(BlackjackScene(self.app))
        else: self.app.state.notify("Need 1000+ gold to unlock Blackjack.")
    def do_prestige(self):
        if self.app.state.prestige_available(): self.app.state.do_prestige()
        else: self.app.state.notify("Reach 1M+ gold to Prestige.")
    def manual_save(self):
        try: self.app.state.save(); self.app.state.notify("Saved 💾")
        except Exception as e: print("Save failed:", e)
    def go_main_menu(self): self.app.change_scene(MainMenu(self.app))
    def handle_close_clicks(self, events):
        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if self.show_achievements and pygame.Rect(self._ach_rect.right - 28, self._ach_rect.top + 8, 20, 20).collidepoint(e.pos): self.show_achievements = False
                if self.show_stats and pygame.Rect(self._stats_rect.right - 28, self._stats_rect.top + 8, 20, 20).collidepoint(e.pos): self.show_stats = False
    def click_to_boost(self, pos):
        w, h = self.app.screen.get_size(); panel_w = panel_w_for(w)
        if pos[0] >= w - panel_w: return
        if not self.app.state.cars_list: return
        nearest = None; best_d2 = 1e18
        for car in self.app.state.cars_list:
            car["boost"] = min(car.get("boost", 0.0) + 0.5, 2.5)
        for _ in range(12):
            self.particles.append(Particle(pos[0], pos[1], color=CYAN, speed=(150,260), life=(0.25,0.5), size=(2,4)))
        if nearest:
            nearest["boost"] = min(nearest.get("boost", 0.0) + 1.8, 3.2)
            for _ in range(8): self.particles.append(Particle(pos[0], pos[1], color=CYAN, speed=(150,260), life=(0.25,0.5), size=(2,4)))
        self.click_fx.append({"t": 0.0, "dur": 0.65})

    def update(self, dt, events):
        w, h = self.app.screen.get_size(); panel_w = panel_w_for(w)
        self.center = center_for(w, h, panel_w); self.radius = radius_for(w, h, panel_w)
        if self.last_canvas_size != (w, h):
            self.relayout(); self.app.state.re_seed_stars(w, h); self.last_canvas_size = (w, h)
        keys = pygame.key.get_pressed(); mouse = pygame.mouse.get_pos()
        for e in events:
            if e.type == pygame.VIDEORESIZE: self.relayout()
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1: self.click_to_boost(e.pos)
        # Passive income
        gsec = self.app.state.auto_gold_per_sec(); self.app.state.gold += gsec * dt; self.app.state.lifetime_gold_earned += gsec * dt
        # Cars
        ang_speed = self.app.state.ang_speed()
        for car in self.app.state.cars_list:
            if car["cooldown"] > 0: car["cooldown"] -= dt
            if car["boost"] > 0: car["boost"] -= dt
            elif car["cooldown"] <= 0 and random.random() < 0.4*dt: car["boost"] = random.uniform(0.8, 1.4); car["cooldown"] = random.uniform(2.5, 5.5)
            boost_factor = 1.0 + (0.8 if car["boost"] > 0 else 0.0)
            prev_t = car["t"]; car["t"] = (car["t"] + ang_speed * car["var"] * boost_factor * dt) % (2*math.pi)
            x, y = track_pos(self.app.state.track_type, car["t"], self.radius, self.center)
            if not car["trail"] or (abs(x - (car["trail"][-1][0])) + abs(y - (car["trail"][-1][1])) > 2): car["trail"].append((x, y))
            if prev_t > math.pi*1.5 and car["t"] < math.pi*0.5:
                self.app.state.award_lap()
                if self.app.state.enable_particles:
                    for _ in range(10): self.particles.append(Particle(x, y, color=YELLOW, speed=(100,200), life=(0.3,0.6), size=(2,4)))
        if self.app.state.enable_particles: self.particles = [p for p in self.particles if p.update(dt)]
        # Labels & enablement
        gs = self.app.state
        self.btn_buy_car.text = f"Buy Car ({fmt_num(gs.get_car_cost())})"; self.btn_speed.text = f"Upgrade Speed ({fmt_num(gs.get_speed_cost())})"
        self.btn_payout.text = f"Track Ads ({fmt_num(gs.get_payout_cost())})"; self.btn_auto.text = f"Auto-Clicker Lv{gs.autoclicker_level} ({fmt_num(gs.get_auto_cost())})"
        self.btn_mult.text = f"Gold Mult x2^{gs.gold_mult_level} ({fmt_num(gs.get_mult_cost())})"; self.btn_offline.text = f"Offline Boost Lv{gs.offline_level} ({fmt_num(gs.get_offline_cost())})"
        self.btn_buy_car.enabled = gs.gold >= gs.get_car_cost(); self.btn_speed.enabled = gs.gold >= gs.get_speed_cost(); self.btn_payout.enabled = gs.gold >= gs.get_payout_cost()
        self.btn_auto.enabled = gs.gold >= gs.get_auto_cost(); self.btn_mult.enabled = gs.gold >= gs.get_mult_cost(); self.btn_offline.enabled = gs.gold >= gs.get_offline_cost()
        self.btn_bj.enabled = gs.blackjack_unlocked; self.btn_prest.enabled = gs.prestige_available()
        # Scroll
        base_tops = [r.top for r in self.button_bases.values()] if self.button_bases else [0]
        base_bottoms = [r.bottom for r in self.button_bases.values()] if self.button_bases else [0]
        content_h = (max(base_bottoms) - min(base_tops)) if base_bottoms and base_tops else 0; max_scroll = max(0, content_h - self.buttons_view.h + 20)
        for e in events:
            if e.type == pygame.MOUSEWHEEL: self.scroll_offset = clamp(self.scroll_offset - e.y * 40, 0, max_scroll)
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_PAGEUP, pygame.K_UP): self.scroll_offset = clamp(self.scroll_offset - 60, 0, max_scroll)
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_PAGEDOWN, pygame.K_DOWN): self.scroll_offset = clamp(self.scroll_offset + 60, 0, max_scroll)
        # Apply scroll
        for b in self.buttons:
            base = self.button_bases[b]; b.rect.topleft = (base.x, base.y - int(self.scroll_offset))
            b.visible = b.rect.colliderect(self.buttons_view); b.update(mouse, pressed_keys=keys)
        for e in events:
            for b in self.buttons:
                if b.visible: b.handle_event(e)
        # Update '+' click popups
        for fx in list(self.click_fx):
            fx["t"] += dt
            if fx["t"] >= fx["dur"]:
                self.click_fx.remove(fx)       
                 # Meta

        self.app.state.update_gps(); self.app.state.check_achievements(); self.app.state.tick_autosave(dt); self.app.state.update_notifications(dt); self.update_fade(dt)
        self._stats_rect = pygame.Rect(24, h - 220, 360, 196); self.handle_close_clicks(events)
    def draw(self, surface):
        w, h = surface.get_size(); panel_w = panel_w_for(w); self.center = center_for(w, h, panel_w); self.radius = radius_for(w, h, panel_w)
        surface.fill(BLACK)
        for s in self.app.state.stars: s.draw(surface)
        # Track
        col = (40, 40, 40); pts = []
        for i in range(200):
            t = (i / 200) * 2*math.pi; x, y = track_pos(self.app.state.track_type, t, self.radius, self.center); pts.append((int(x), int(y)))
        if len(pts) > 1: pygame.draw.aalines(surface, col, True, pts)
        # Cars & trails
        for car in self.app.state.cars_list:
            if car["trail"]:
                for i, (tx, ty) in enumerate(car["trail"]):
                    a = int(20 + 235 * (i / len(car["trail"]))**1.2); surf = pygame.Surface((8,8), pygame.SRCALPHA)
                    surf.fill((car["col"][0], car["col"][1], car["col"][2], a//5)); surface.blit(surf, (int(tx)-4, int(ty)-4))
            x, y = track_pos(self.app.state.track_type, car["t"], self.radius, self.center)
            if car["boost"] > 0:
                glow = pygame.Surface((50,50), pygame.SRCALPHA); alpha = clamp(int(120 * (car["boost"])), 40, 160)
                pygame.draw.circle(glow, (255,255,255,alpha), (25,25), 20); surface.blit(glow, (int(x)-25, int(y)-25))
            pygame.draw.circle(surface, car["col"], (int(x), int(y)), car["size"])
        if self.app.state.enable_particles:
            for p in self.particles: p.draw(surface)
        # Right panel
        panel_x = w - panel_w; panel = pygame.Rect(panel_x, 0, panel_w, h)
        pygame.draw.rect(surface, (12,12,12), panel); pygame.draw.line(surface, WHITE, (panel_x, 0), (panel_x, h), 2)
        # Header stats
        gold_rect = draw_text_shadow(surface,f"Gold: {fmt_num(self.app.state.gold)}",self.big_font,WHITE,DARK_GREY,(panel_x + 20, 20))
        # Draw '+' popups near the gold label
        for fx in self.click_fx:
            p = fx["t"] / fx["dur"]         # 0 → 1 over its lifetime
            alpha = max(0, min(255, int(255 * (1 - p))))
            yoff  = int(-20 * p)            # float upward a bit

            plus_surf = self.big_font.render("+", True, CYAN).convert_alpha()
            plus_surf.set_alpha(alpha)
            surface.blit(plus_surf, (gold_rect.right + 14, gold_rect.top + 6 + yoff))
        
        gpar = self.app.state.gold_per_all_cars_rev()  # total gold when all cars complete one lap
        draw_text(surface, f"{fmt_num(gpar)} / gold per revolution", self.font, GREY, (panel_x + 20, 64))
        draw_text(surface, f"Cars: {self.app.state.cars}", self.font, GREY, (panel_x + 20, 98))
        draw_text(surface, f"Speed Lv: {self.app.state.speed_level}", self.font, GREY, (panel_x + 200, 98))
        draw_text(surface, f"Payout Lv: {self.app.state.payout_level}", self.font, GREY, (panel_x + 20, 126))
        draw_text(surface, f"Mult: x{fmt_num(self.app.state.gold_multiplier_total())}", self.font, GREY, (panel_x + 200, 126))
        # Buttons viewport
        self.buttons_view = pygame.Rect(panel_x + 20, 150, panel_w - 40, h - 170)
        surface.set_clip(self.buttons_view)
        for b in self.buttons:
            if b.visible: b.draw(surface); b.draw_tooltip(surface, self.small_font, pygame.mouse.get_pos())
        surface.set_clip(None)
        # Achievements overlay
        if self.show_achievements:
            ach_panel = self._ach_rect; pygame.draw.rect(surface, (16,16,16), ach_panel, border_radius=12); pygame.draw.rect(surface, WHITE, ach_panel, 1, border_radius=12)
            draw_text(surface, "Achievements", self.font, WHITE, (ach_panel.x + 12, ach_panel.y + 8))
            names = [name for name, st in self.app.state.achievements.items() if st.get("unlocked")]; yy = ach_panel.y + 44
            for name in sorted(names)[:6]: draw_text(surface, f"• {name}", self.small_font, GREY, (ach_panel.x + 16, yy)); yy += 22
            if len(names) > 6: draw_text(surface, f"+{len(names)-6} more...", self.small_font, GREY, (ach_panel.x + 16, yy))
            hover = pygame.Rect(ach_panel.right - 28, ach_panel.top + 8, 20, 20).collidepoint(pygame.mouse.get_pos()); draw_close(surface, ach_panel, hover=hover)
        # Stats overlay
        if self.show_stats:
            stats_panel = self._stats_rect; pygame.draw.rect(surface, (16,16,16), stats_panel, border_radius=12); pygame.draw.rect(surface, WHITE, stats_panel, 1, border_radius=12)
            draw_text(surface, "Statistics", self.font, WHITE, (stats_panel.x + 12, stats_panel.y + 8))
            lines = [
                f"Gold/Revolution: {fmt_num(self.app.state.gold_per_all_cars_rev())}"
                f"Laps: {fmt_num(self.app.state.laps_total)}",
                f"Auto/sec: {fmt_num(self.app.state.auto_gold_per_sec())}",
                f"Lifetime: {fmt_num(self.app.state.lifetime_gold_earned)}",
                f"Sponsors: {self.app.state.sponsor_level}  PP: {self.app.state.prestige_points}",
                f"Track: {['Circle','Figure-8','Oval','Complex'][self.app.state.track_type]}",
            ]
            yy = stats_panel.y + 44
            for ln in lines: draw_text(surface, ln, self.small_font, GREY, (stats_panel.x + 16, yy)); yy += 22
            hover = pygame.Rect(stats_panel.right - 28, stats_panel.top + 8, 20, 20).collidepoint(pygame.mouse.get_pos()); draw_close(surface, stats_panel, hover=hover)
        # Notifications
        base_y = 90
        for i, n in enumerate(self.app.state.notifications):
            alpha = 1.0
            if n["t"] > n["dur"] - 0.5: alpha = clamp((n["dur"] - n["t"]) / 0.5, 0.0, 1.0)
            surf = pygame.Surface((520, 40), pygame.SRCALPHA); a = int(180 * alpha)
            pygame.draw.rect(surf, (30,30,30,a), pygame.Rect(0,0,520,40), border_radius=10)
            pygame.draw.rect(surf, (255,255,255,int(220*alpha)), pygame.Rect(0,0,520,40), 1, border_radius=10)
            txt = self.small_font.render(n["text"], True, (255,255,255,int(255*alpha))); surf.blit(txt, (14, 10))
            rect = surf.get_rect(center=(w//2 - panel_w//2, base_y + i*46)); surface.blit(surf, rect.topleft)
        draw_text(surface, "Scroll: Mouse Wheel / PgUp/PgDn", self.small_font, DARK_GREY, (panel_x + 20, h - 22)); self.draw_fade(surface)

class BlackjackScene(SceneBase):
    def __init__(self, app):
        super().__init__(app)
        self.font = app.font_med; self.small_font = app.font_small; self.big_font = app.font_big
        self.bj = Blackjack(app.state); self.buttons = []; self.relayout(); self.show_stats = True
        self._bjstats_rect = pygame.Rect(24, self.app.screen.get_height() - 200, 300, 160)
    def relayout(self):
        w, h = self.app.screen.get_size(); bw, bh = 220, 60; y = h - 120; gap = 240
        self.btn_deal  = Button((w//2 - gap - bw//2, y, bw, bh), "DEAL", self.font, onclick=self.do_deal, key=pygame.K_RETURN, tooltip="Enter: Deal", accent=CYAN)
        self.btn_hit   = Button((w//2 - bw//2, y, bw, bh), "HIT", self.font, onclick=self.do_hit, key=pygame.K_h, tooltip="H: Hit", accent=WHITE)
        self.btn_stand = Button((w//2 + gap - bw//2, y, bw, bh), "STAND", self.font, onclick=self.do_stand, key=pygame.K_j, tooltip="J: Stand", accent=WHITE)
        self.btn_back  = Button((20, 20, 160, 56), "BACK (Esc)", self.font, onclick=self.go_back, key=pygame.K_ESCAPE, tooltip="Return to Idle", accent=RED)
        self.btn_bet_m1000 = Button((w//2 - 520, y - 80, 80, 52), "-1K", self.font, onclick=lambda: self.bj.change_bet(-1000), accent=RED)
        self.btn_bet_m100  = Button((w//2 - 430, y - 80, 80, 52), "-100", self.font, onclick=lambda: self.bj.change_bet(-100), accent=RED)
        self.btn_bet_m10   = Button((w//2 - 340, y - 80, 80, 52), "-10", self.font, onclick=lambda: self.bj.change_bet(-10), accent=RED)
        self.btn_bet_p10   = Button((w//2 + 260, y - 80, 80, 52), "+10", self.font, onclick=lambda: self.bj.change_bet(+10), accent=GREEN)
        self.btn_bet_p100  = Button((w//2 + 350, y - 80, 80, 52), "+100", self.font, onclick=lambda: self.bj.change_bet(+100), accent=GREEN)
        self.btn_bet_p1000 = Button((w//2 + 440, y - 80, 80, 52), "+1K", self.font, onclick=lambda: self.bj.change_bet(+1000), accent=GREEN)
        self.buttons = [self.btn_deal, self.btn_hit, self.btn_stand, self.btn_back,
                        self.btn_bet_m1000, self.btn_bet_m100, self.btn_bet_m10, self.btn_bet_p10, self.btn_bet_p100, self.btn_bet_p1000]
    def do_deal(self): self.bj.deal()
    def do_hit(self): self.bj.hit()
    def do_stand(self): self.bj.stand()
    def go_back(self): self.app.change_scene(IdleScene(self.app))
    def update(self, dt, events):
        keys = pygame.key.get_pressed(); mouse = pygame.mouse.get_pos()
        for e in events:
            if e.type == pygame.VIDEORESIZE: self.relayout(); self._bjstats_rect = pygame.Rect(24, self.app.screen.get_height() - 200, 300, 160)
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.show_stats:
                if pygame.Rect(self._bjstats_rect.right - 28, self._bjstats_rect.top + 8, 20, 20).collidepoint(e.pos): self.show_stats = False
        self.btn_deal.enabled = (not self.bj.in_round) and self.app.state.gold >= self.bj.bet; self.btn_hit.enabled = self.bj.in_round; self.btn_stand.enabled = self.bj.in_round
        for b in self.buttons:
            b.update(mouse, pressed_keys=keys)
            for e in events: b.handle_event(e)
        self.update_fade(dt)
    def draw_card(self, surface, card, x, y):
        rect = pygame.Rect(x, y, 64, 92); pygame.draw.rect(surface, WHITE, rect, width=2, border_radius=10)
        if card[0] != "?":
            r, s = card; suit_col = RED if s in ["♥", "♦"] else WHITE; draw_text(surface, r, self.font, suit_col, (rect.x + 8, rect.y + 6)); draw_text(surface, s, self.font, suit_col, (rect.x + 8, rect.y + 46))
        else: draw_text(surface, "?", self.big_font, GREY, (rect.centerx, rect.centery-12), center=True)
    def draw_hand(self, surface, cards, center_x, y, hide=False):
        spacing = 72; start_x = center_x - (len(cards) * spacing)//2
        for i, c in enumerate(cards): self.draw_card(surface, ("?","?") if (hide and i==1) else c, start_x + i*spacing, y)
    def draw(self, surface):
        w, h = surface.get_size(); surface.fill(BLACK)
        for s in self.app.state.stars: s.draw(surface)
        top = pygame.Rect(0, 0, w, 100); pygame.draw.rect(surface, (12,12,12), top); pygame.draw.line(surface, WHITE, (0, 100), (w, 100), 2)
        draw_text_shadow(surface, "BLACKJACK", self.big_font, WHITE, DARK_GREY, (w//2, 56), center=True)
        draw_text(surface, f"Gold: {fmt_num(self.app.state.gold)}", self.font, GREY, (w - 260, 20))
        draw_text(surface, "Dealer", self.font, GREY, (w//2, 130), center=True); self.draw_hand(surface, self.bj.dealer, w//2, 160, hide=self.bj.in_round)
        if not self.bj.in_round: draw_text(surface, f"({hand_value(self.bj.dealer)})", self.small_font, GREY, (w//2, 260), center=True)
        draw_text(surface, "Player", self.font, GREY, (w//2, 300), center=True); self.draw_hand(surface, self.bj.player, w//2, 330, hide=False)
        if self.bj.player: draw_text(surface, f"({hand_value(self.bj.player)})", self.small_font, GREY, (w//2, 430), center=True)
        draw_text(surface, self.bj.message, self.font, WHITE, (w//2, 468), center=True); draw_text(surface, f"Bet: {fmt_num(self.bj.bet)}", self.font, WHITE, (w//2, h - 200), center=True)
        mouse = pygame.mouse.get_pos()
        for b in self.buttons: b.draw(surface); b.draw_tooltip(surface, self.small_font, mouse)
        if self.show_stats:
            stats = self.app.state.bj_stats; games = max(1, int(stats.get("games", 0))); wins = int(stats.get("wins", 0)); winrate = 100.0 * wins / games if games > 0 else 0.0
            box = self._bjstats_rect; pygame.draw.rect(surface, (16,16,16), box, border_radius=12); pygame.draw.rect(surface, WHITE, box, 1, border_radius=12)
            draw_text(surface, "BJ Stats", self.font, WHITE, (box.x + 12, box.y + 8))
            draw_text(surface, f"Games: {games}", self.small_font, GREY, (box.x + 16, box.y + 50)); draw_text(surface, f"Wins: {wins}", self.small_font, GREY, (box.x + 16, box.y + 74)); draw_text(surface, f"Win rate: {winrate:.1f}%", self.small_font, GREY, (box.x + 16, box.y + 98))
            hover = pygame.Rect(box.right - 28, box.top + 8, 20, 20).collidepoint(pygame.mouse.get_pos()); draw_close(surface, box, hover=hover)
        self.draw_fade(surface)

# ------------------------------
# App
# ------------------------------
class App:
    def __init__(self):
        pygame.init()
        # Window state
        self.fullscreen = False
        self.windowed_size = DEFAULT_WINDOWED_SIZE
        self.flags_windowed = pygame.RESIZABLE | pygame.DOUBLEBUF
        self.flags_full     = pygame.FULLSCREEN | pygame.DOUBLEBUF
        # Create windowed, resizable
        self.screen = pygame.display.set_mode(self.windowed_size, self.flags_windowed)
        pygame.display.set_caption("Idle Racer + Blackjack")
        self.clock = pygame.time.Clock()
        # Fonts
        self.font_small = pygame.font.SysFont("Consolas,DejaVu Sans Mono,Arial", 18)
        self.font_med   = pygame.font.SysFont("Consolas,DejaVu Sans Mono,Arial", 24, bold=True)
        self.font_big   = pygame.font.SysFont("Consolas,DejaVu Sans Mono,Arial", 36, bold=True)
        self.font_huge  = pygame.font.SysFont("Consolas,DejaVu Sans Mono,Arial", 48, bold=True)
        # Game state & scene
        self.state = GameState(*self.screen.get_size())
                # Save on interpreter exit as a safety net
        def _save_at_exit():
            try:
                if self.state:
                    self.state.save()
            except Exception:
                pass

        atexit.register(_save_at_exit)

        self.scene = MainMenu(self); self.scene.start_fade_in()
        self.last_load_message = ""
    def apply_window_settings(self, size=None, fullscreen=None):
        if size is not None: self.windowed_size = size
        if fullscreen is not None: self.fullscreen = fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), self.flags_full)
        else:
            self.screen = pygame.display.set_mode(self.windowed_size, self.flags_windowed)
        # Inform scenes to relayout next frame
        if isinstance(self.scene, IdleScene): self.scene.last_canvas_size = (0,0)
        elif isinstance(self.scene, MainMenu): self.scene.relayout()
        elif isinstance(self.scene, OptionsScene): self.scene.relayout()
        elif isinstance(self.scene, BlackjackScene): self.scene.relayout()
        # Reseed stars to new canvas
        w, h = self.screen.get_size(); self.state.re_seed_stars(w, h)
    def toggle_fullscreen(self): self.apply_window_settings(fullscreen=not self.fullscreen)
    def handle_resize(self, w, h):
        if self.fullscreen: return
        new_w = max(800, w); new_h = max(600, h); self.windowed_size = (new_w, new_h)
        self.screen = pygame.display.set_mode(self.windowed_size, self.flags_windowed)
        # Inform scenes to relayout next frame
        if isinstance(self.scene, IdleScene): self.scene.last_canvas_size = (0,0)
        w, h = self.screen.get_size(); self.state.re_seed_stars(w, h)
    def change_scene(self, new_scene): self.scene = new_scene; self.scene.start_fade_in()
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(self.state.fps_cap) / 1000.0; events = []
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    try: self.state.save()
                    except Exception as ex: print("Save on exit failed:", ex)
                    running = False
                elif e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
                    self.toggle_fullscreen()
                elif e.type == pygame.VIDEORESIZE:
                    self.handle_resize(e.w, e.h)
                else:
                    events.append(e)
            self.scene.update(dt, events); self.scene.draw(self.screen); pygame.display.flip()
        pygame.quit()

if __name__ == "__main__":
    App().run()
