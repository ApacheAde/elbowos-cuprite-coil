#!/usr/bin/env python3
"""Cuprite Coil — neon three-rail helix arcade for ElbowOS."""
from __future__ import annotations

import math
import os
import random
import subprocess
import sys

import pygame

W, H = 1080, 1920
FPS = 30
TITLE = "CUPRITE COIL"
HANDLE = "x.com/ElbowOS"
BG = (12, 4, 8)
RUST = (42, 14, 16)
COPPER = (255, 122, 48)
EMBER = (255, 72, 36)
TEAL = (48, 232, 196)
GOLD = (255, 204, 72)
SLAG = (88, 48, 120)
FOAM = (255, 236, 210)
LANES = (280, 540, 800)


class Spark:
    __slots__ = ("x", "y", "vx", "vy", "life", "col", "r")

    def __init__(self, x, y, vx, vy, life, col, r=5):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life, self.col, self.r = life, col, r


class Token:
    __slots__ = ("lane", "y", "kind", "spin")

    def __init__(self, lane, y, kind):
        self.lane, self.y, self.kind, self.spin = lane, y, kind, random.random() * math.tau


class Game:
    def __init__(self, record: bool):
        self.record = record
        self.surf = pygame.Surface((W, H))
        self.clock = pygame.time.Clock()
        self.font_lg = pygame.font.Font(None, 62)
        self.font_md = pygame.font.Font(None, 42)
        self.font_sm = pygame.font.Font(None, 28)
        self.score = 0
        self.reset()

    def reset(self) -> None:
        self.t = 0.0
        self.lane = 1
        self.tx = float(LANES[1])
        self.y = 1380.0
        self.vy = 0.0
        self.heat = 0.0
        self.combo = 1
        self.tokens: list[Token] = []
        self.sparks: list[Spark] = []
        self.embers = [[random.uniform(0, W), random.uniform(0, H), random.uniform(0.4, 1.8)]
                       for _ in range(90)]
        self.spawn_cd = 0.0
        self.flash = 0.0
        self.alive = True

    def burst(self, x, y, col, n=12) -> None:
        for _ in range(n):
            a = random.random() * math.tau
            spd = random.uniform(50, 380)
            self.sparks.append(Spark(x, y, math.cos(a) * spd, math.sin(a) * spd,
                                     random.uniform(0.16, 0.42), col, random.randint(3, 7)))

    def autoplay(self) -> None:
        danger = [False, False, False]
        prize = [0.0, 0.0, 0.0]
        for tok in self.tokens:
            if 700 < tok.y < 1550:
                if tok.kind == "slag":
                    danger[tok.lane] = True
                else:
                    prize[tok.lane] += 1.0 / max(40.0, abs(tok.y - self.y))
        if danger[self.lane]:
            opts = [i for i in range(3) if not danger[i]]
            if opts:
                self.lane = max(opts, key=lambda i: prize[i])
        elif prize[self.lane] < max(prize) - 1e-6:
            self.lane = prize.index(max(prize))
        elif random.random() < 0.012:
            self.lane = max(0, min(2, self.lane + random.choice((-1, 1))))

    def handle(self, ev) -> None:
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_LEFT, pygame.K_a):
                self.lane = max(0, self.lane - 1)
            elif ev.key in (pygame.K_RIGHT, pygame.K_d):
                self.lane = min(2, self.lane + 1)
            elif ev.key == pygame.K_r:
                self.score = 0
                self.reset()

    def update(self, dt: float) -> None:
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        if self.record:
            self.autoplay()
        target = float(LANES[self.lane])
        self.tx += (target - self.tx) * min(1.0, 14.0 * dt)
        self.spawn_cd -= dt
        speed = 420 + min(280, self.score * 0.08)
        if self.spawn_cd <= 0:
            kind = "slag" if random.random() < 0.38 else "ore"
            lane = random.randrange(3)
            if self.tokens and self.tokens[-1].kind == "slag" and random.random() < 0.55:
                lane = (self.tokens[-1].lane + random.choice((1, 2))) % 3
            self.tokens.append(Token(lane, -40, kind))
            self.spawn_cd = max(0.28, 0.72 - self.score * 0.0004)
        live: list[Token] = []
        px, py = self.tx, self.y
        for tok in self.tokens:
            tok.y += speed * dt
            tok.spin += 4.2 * dt
            if tok.y > H + 50:
                continue
            dx, dy = LANES[tok.lane] - px, tok.y - py
            if dx * dx + dy * dy < 52 * 52:
                if tok.kind == "ore":
                    self.score += 25 * self.combo
                    self.combo = min(9, self.combo + 1)
                    self.heat = min(1.0, self.heat + 0.18)
                    self.flash = 0.09
                    self.burst(LANES[tok.lane], tok.y, GOLD, 16)
                    continue
                self.combo = 1
                self.heat = max(0.0, self.heat - 0.35)
                self.flash = 0.16
                self.burst(px, py, SLAG, 22)
                self.tx += random.choice((-70, 70))
                continue
            live.append(tok)
        self.tokens = live
        self.heat = max(0.0, self.heat - 0.08 * dt)
        for em in self.embers:
            em[1] -= (18 + em[2] * 40) * dt
            em[0] += math.sin(self.t * 1.4 + em[2]) * 12 * dt
            if em[1] < -8:
                em[1] = H + 8
                em[0] = random.uniform(0, W)
        sparks: list[Spark] = []
        for sp in self.sparks:
            sp.life -= dt
            if sp.life <= 0:
                continue
            sp.x += sp.vx * dt
            sp.y += sp.vy * dt
            sparks.append(sp)
        self.sparks = sparks

    def _coil_x(self, lane: int, y: float) -> float:
        phase = self.t * 2.1 + lane * 2.09 + y * 0.012
        return LANES[lane] + math.sin(phase) * 18

    def draw(self, s: pygame.Surface) -> None:
        s.fill(BG)
        glow = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.rect(glow, (80, 16, 8, 70), (0, 0, W, H))
        s.blit(glow, (0, 0))
        for x, y, r in self.embers:
            col = COPPER if r > 1.1 else EMBER
            pygame.draw.circle(s, col, (int(x), int(y)), max(1, int(r)))
        shaft = pygame.Rect(150, 190, 780, 1580)
        pygame.draw.rect(s, RUST, shaft, border_radius=48)
        pygame.draw.rect(s, COPPER, shaft, 4, border_radius=48)
        for i in range(16):
            yy = 220 + i * 96 + int(math.sin(self.t * 1.7 + i) * 6)
            shade = 18 + (i * 7) % 22
            pygame.draw.line(s, (shade + 20, 8, 10), (170, yy), (910, yy), 2)
        for lane in range(3):
            pts = []
            for k in range(28):
                yy = 220 + k * 58
                pts.append((self._coil_x(lane, yy), yy))
            if len(pts) > 1:
                pygame.draw.lines(s, (90, 32, 24), False, pts, 10)
                pygame.draw.lines(s, COPPER if lane == self.lane else (160, 70, 40), False, pts, 4)
        for tok in self.tokens:
            x = self._coil_x(tok.lane, tok.y)
            if tok.kind == "ore":
                pygame.draw.circle(s, GOLD, (int(x), int(tok.y)), 22)
                pygame.draw.circle(s, FOAM, (int(x - 5), int(tok.y - 6)), 6)
                arm = 16 + 4 * math.sin(tok.spin * 3)
                pygame.draw.circle(s, TEAL, (int(x), int(tok.y)), int(arm), 2)
            else:
                pygame.draw.rect(s, SLAG, pygame.Rect(int(x) - 24, int(tok.y) - 18, 48, 36), border_radius=8)
                pygame.draw.rect(s, EMBER, pygame.Rect(int(x) - 24, int(tok.y) - 18, 48, 36), 3, border_radius=8)
        px = self._coil_x(self.lane, self.y) + (self.tx - LANES[self.lane])
        pygame.draw.circle(s, (40, 10, 8), (int(px + 5), int(self.y + 8)), 30)
        pygame.draw.circle(s, COPPER, (int(px), int(self.y)), 28)
        pygame.draw.circle(s, GOLD, (int(px), int(self.y)), 28, 3)
        pygame.draw.circle(s, FOAM, (int(px - 8), int(self.y - 9)), 7)
        ring = 34 + int(8 * self.heat)
        pygame.draw.circle(s, TEAL, (int(px), int(self.y)), ring, 2)
        for sp in self.sparks:
            pygame.draw.circle(s, sp.col, (int(sp.x), int(sp.y)), max(1, int(sp.r * sp.life * 2.5)))
        if self.flash > 0:
            fl = pygame.Surface((W, H), pygame.SRCALPHA)
            fl.fill((255, 140, 60, int(50 * self.flash / 0.16)))
            s.blit(fl, (0, 0))
        title = self.font_lg.render(TITLE, True, COPPER)
        s.blit(title, title.get_rect(center=(W // 2, 54)))
        handle = self.font_sm.render(HANDLE, True, GOLD)
        s.blit(handle, handle.get_rect(center=(W // 2, 104)))
        hud = self.font_md.render(f"SCORE  {self.score}    x{self.combo}", True, TEAL)
        s.blit(hud, hud.get_rect(center=(W // 2, 154)))
        hint = self.font_sm.render("A / D switch rails    R reset    x.com/ElbowOS", True, EMBER)
        s.blit(hint, hint.get_rect(center=(W // 2, H - 46)))

    def play(self) -> None:
        screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption(TITLE)
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                    running = False
                else:
                    self.handle(ev)
            self.update(dt)
            self.draw(self.surf)
            screen.blit(self.surf, (0, 0))
            pygame.display.flip()

    def record_mp4(self, path: str) -> None:
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart", path,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        frames = FPS * 15
        for i in range(frames):
            self.update(1.0 / FPS)
            self.draw(self.surf)
            proc.stdin.write(pygame.image.tostring(self.surf, "RGB"))
            if i % 30 == 0:
                print(f"frame {i}/{frames}", flush=True)
        proc.stdin.close()
        rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed: {rc}")
        print("wrote", path)


def main() -> None:
    record = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
    play = "--play" in sys.argv
    if record or not play:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.font.init()
    g = Game(record or not play)
    if record or not play:
        out = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/CUPRITE_COIL_ElbowOS.mp4")
        g.record_mp4(out)
    else:
        g.play()
    pygame.quit()


if __name__ == "__main__":
    main()
