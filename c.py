import math
import random
import json
import sys
import time
import os

# ==========================================
# 1. 物理內核 V6
# ==========================================
class PhysicsKernel:
    G_CONST = 0.8
    C_SPEED = 15.0
    COOLING_RATE = 0.995
    SOLAR_CONSTANT = 130.0
    UNIVERSE_RADIUS = 2800.0
    UNIVERSE_SPIN = 0.0003
    ENERGY_INJECT_INTERVAL = 80
    ENERGY_INJECT_COUNT = 2
    BOUNDARY_START = 0.78
    TIDAL_SHRED_THRESHOLD = 0.95

    @staticmethod
    def get_density(spin):
        return 1.0 / (1.0 + spin * 0.002)

    @staticmethod
    def get_radius(mass, spin):
        return math.sqrt(mass / PhysicsKernel.get_density(spin)) * 3.0

    @staticmethod
    def apply_relativity(vx, vy):
        speed = math.hypot(vx, vy)
        if speed > PhysicsKernel.C_SPEED:
            s = PhysicsKernel.C_SPEED / speed
            return vx * s, vy * s
        return vx, vy

    @staticmethod
    def calc_equilibrium_temp(star_temp, dist):
        rad = (star_temp * PhysicsKernel.SOLAR_CONSTANT) / (dist * dist + 1.0)
        return rad / (1.0 - PhysicsKernel.COOLING_RATE)

    @staticmethod
    def export_params():
        return {
            "G": PhysicsKernel.G_CONST, "C": PhysicsKernel.C_SPEED,
            "CR": PhysicsKernel.COOLING_RATE, "SC": PhysicsKernel.SOLAR_CONSTANT,
            "UR": PhysicsKernel.UNIVERSE_RADIUS, "US": PhysicsKernel.UNIVERSE_SPIN,
            "EI": PhysicsKernel.ENERGY_INJECT_INTERVAL,
            "EC": PhysicsKernel.ENERGY_INJECT_COUNT,
            "BS": PhysicsKernel.BOUNDARY_START,
            "TS": PhysicsKernel.TIDAL_SHRED_THRESHOLD
        }

    @staticmethod
    def import_params(data):
        if not data: return
        m = {"G":"G_CONST","C":"C_SPEED","CR":"COOLING_RATE",
             "SC":"SOLAR_CONSTANT","UR":"UNIVERSE_RADIUS",
             "US":"UNIVERSE_SPIN","EI":"ENERGY_INJECT_INTERVAL",
             "EC":"ENERGY_INJECT_COUNT","BS":"BOUNDARY_START",
             "TS":"TIDAL_SHRED_THRESHOLD"}
        for short, full in m.items():
            if short in data: setattr(PhysicsKernel, full, data[short])


# ==========================================
# 2. 天體模型（黑洞邊界版）
# ==========================================
class CelestialBody:
    def __init__(self, x, y, mass, spin, temp):
        self.x = x; self.y = y
        self.vx = 0.0; self.vy = 0.0
        self.mass = mass; self.spin = spin; self.temp = temp
        self.radius = PhysicsKernel.get_radius(mass, spin)
        self.cid = random.randint(100000, 999999)
        self.composition = {"Fe": mass*0.3, "Si": mass*0.4, "Vo": mass*0.3}
        self.axial_tilt = random.uniform(0, 30)
        self.is_star = False; self.is_active = True
        self.birth_dist = 0.0
        self.boundary_hits = 0
        self.origin = "bigbang"
        self.in_buffer_zone = False
        self.tidal_damage = 0.0
        self.shred_immunity = 0        # 碎片免疫期

    def to_compact(self):
        return [
            self.cid,                           # 0
            round(self.x, 1),                   # 1
            round(self.y, 1),                   # 2
            round(self.vx, 3),                  # 3
            round(self.vy, 3),                  # 4
            round(self.mass, 2),                # 5
            round(self.spin, 2),                # 6
            round(self.temp, 1),                # 7
            round(self.radius, 1),              # 8
            round(self.composition["Fe"], 1),   # 9
            round(self.composition["Si"], 1),   # 10
            round(self.composition["Vo"], 1),   # 11
            round(self.axial_tilt, 1),          # 12
            1 if self.is_star else 0,           # 13
            round(self.birth_dist, 0),          # 14
            self.boundary_hits,                 # 15
            self.origin,                        # 16
            round(self.tidal_damage, 3),        # 17
            self.shred_immunity                 # 18
        ]

    @staticmethod
    def from_compact(arr):
        b = CelestialBody(arr[1], arr[2], arr[5], arr[6], arr[7])
        b.cid = arr[0]
        b.vx = arr[3]; b.vy = arr[4]
        b.radius = arr[8]
        b.composition = {"Fe": arr[9], "Si": arr[10], "Vo": arr[11]}
        b.axial_tilt = arr[12]
        b.is_star = (arr[13] == 1)
        b.is_active = True
        if len(arr) > 14: b.birth_dist = arr[14]
        if len(arr) > 15: b.boundary_hits = arr[15]
        if len(arr) > 16: b.origin = arr[16]
        if len(arr) > 17: b.tidal_damage = arr[17]
        if len(arr) > 18: b.shred_immunity = arr[18]
        return b

    def update_thermodynamics(self, main_star):
        if not self.is_active: return
        if self.is_star:
            target = 5500 + (self.mass * 0.1)
            self.temp = self.temp * 0.9 + target * 0.1
            self.mass -= self.mass * 0.00001
            self.radius = PhysicsKernel.get_radius(self.mass, self.spin)
            return
        dx = self.x - main_star.x; dy = self.y - main_star.y
        dist_sq = dx * dx + dy * dy + 1.0
        rad_in = (main_star.temp * PhysicsKernel.SOLAR_CONSTANT) / dist_sq
        self.temp = (self.temp * PhysicsKernel.COOLING_RATE) + rad_in
        if self.temp < -273.15: self.temp = -273.15
        self.radius = PhysicsKernel.get_radius(self.mass, self.spin)

    def move(self):
        self.vx, self.vy = PhysicsKernel.apply_relativity(self.vx, self.vy)
        self.x += self.vx; self.y += self.vy

    def apply_black_hole_boundary(self, center, engine):
        """黑洞邊界：流動膜 + 潮汐撕碎 + 物質回收"""
        dx = self.x - center; dy = self.y - center
        dist = math.hypot(dx, dy)
        R = PhysicsKernel.UNIVERSE_RADIUS

        # 免疫期中：只做硬邊界檢查
        if self.shred_immunity > 0:
            self.shred_immunity -= 1
            self.in_buffer_zone = False
            if dist > R * 0.98:
                nx = dx / dist; ny = dy / dist
                self.x = center + nx * R * 0.97
                self.y = center + ny * R * 0.97
                self.vx *= 0.05; self.vy *= 0.05
            return

        buf_start = R * PhysicsKernel.BOUNDARY_START
        shred_zone = R * PhysicsKernel.TIDAL_SHRED_THRESHOLD

        self.in_buffer_zone = False

        if dist <= buf_start:
            # 正常空間，潮汐損傷自然恢復
            if self.tidal_damage > 0:
                self.tidal_damage = max(0, self.tidal_damage - 0.005)
            return

        # ---- 進入邊界緩衝帶 ----
        self.in_buffer_zone = True
        depth = (dist - buf_start) / (R - buf_start)
        depth = min(depth, 0.99)

        # 時間膨脹：越靠近邊界越慢
        time_dilation = 1.0 - depth * 0.8
        self.vx *= time_dilation
        self.vy *= time_dilation

        # 重力紅移：溫度降低
        self.temp *= (1.0 - depth * 0.15)

        # 潮汐損傷累積
        self.tidal_damage += depth * 0.02
        self.tidal_damage = min(self.tidal_damage, 1.0)

        # ---- 撕碎區域 ----
        if dist > shred_zone and self.tidal_damage > 0.3:
            self.boundary_hits += 1
            engine.boundary_events += 1

            if self.tidal_damage > 0.8 or self.mass < 5:
                self._shred_complete(center, engine)
            else:
                self._shred_partial(center, engine)

        # 硬邊界
        if dist > R * 0.98:
            nx = dx / dist; ny = dy / dist
            self.x = center + nx * R * 0.97
            self.y = center + ny * R * 0.97
            self.vx *= 0.05; self.vy *= 0.05

    def _shred_partial(self, center, engine):
        """部分撕碎：損失質量，碎片向內飛"""
        loss_pct = random.uniform(0.2, 0.4) * self.tidal_damage
        lost_mass = self.mass * loss_pct
        self.mass -= lost_mass
        self.radius = PhysicsKernel.get_radius(self.mass, self.spin)
        for k in self.composition:
            self.composition[k] *= (1 - loss_pct)

        n_frags = random.randint(1, 2)
        for _ in range(n_frags):
            fm = lost_mass / n_frags
            if fm < 1: continue
            angle = random.uniform(0, 6.2832)
            fx = self.x + math.cos(angle) * 20
            fy = self.y + math.sin(angle) * 20
            frag = CelestialBody(fx, fy, fm, random.uniform(1, 5), self.temp * 1.5)
            frag.origin = "recycled"
            frag.birth_dist = math.hypot(fx - center, fy - center)
            frag.shred_immunity = 60  # 免疫期
            cdx = center - fx; cdy = center - fy
            cd = math.hypot(cdx, cdy)
            if cd > 0:
                speed = random.uniform(2, 5)
                frag.vx = (cdx / cd) * speed + random.uniform(-0.5, 0.5)
                frag.vy = (cdy / cd) * speed + random.uniform(-0.5, 0.5)
            engine.bodies.append(frag)
            engine.recycled_mass += fm
            engine.recycled_count += 1

        self.tidal_damage *= 0.5

    def _shred_complete(self, center, engine):
        """完全撕碎：整個天體變成碎片雨"""
        n_frags = random.randint(2, 4)
        fm = self.mass / n_frags
        for _ in range(n_frags):
            if fm < 0.5: continue
            angle = random.uniform(0, 6.2832)
            fx = self.x + math.cos(angle) * 30
            fy = self.y + math.sin(angle) * 30
            frag = CelestialBody(fx, fy, fm, random.uniform(1, 5), self.temp * 2.0)
            frag.origin = "recycled"
            frag.birth_dist = math.hypot(fx - center, fy - center)
            frag.shred_immunity = 60  # 免疫期
            cdx = center - fx; cdy = center - fy
            cd = math.hypot(cdx, cdy)
            if cd > 0:
                speed = random.uniform(3, 6)
                frag.vx = (cdx / cd) * speed + random.uniform(-1, 1)
                frag.vy = (cdy / cd) * speed + random.uniform(-1, 1)
            engine.bodies.append(frag)
            engine.recycled_mass += fm
            engine.recycled_count += 1

        self.is_active = False

    def calc_kinetic_energy(self):
        return 0.5 * self.mass * (self.vx ** 2 + self.vy ** 2)

    def calc_potential_energy(self, star):
        d = math.hypot(self.x - star.x, self.y - star.y)
        if d < 1: d = 1
        return -PhysicsKernel.G_CONST * star.mass * self.mass / d


# ==========================================
# 3. 創世引擎（物質回收版）
# ==========================================
class GenesisEngine:
    def __init__(self):
        self.bodies = []
        self.center_pos = 5000
        self.current_epoch = 0
        self.total_steps_run = 0
        self.run_id = random.randint(10000, 99999)
        self.boundary_events = 0
        self.injected_mass_total = 0.0
        self.injected_count = 0
        self.absorbed_by_star = 0.0
        self.merge_events = 0
        self.recycled_mass = 0.0
        self.recycled_count = 0
        self.epoch_history = []

    def to_compact(self):
        return {
            "r": self.run_id, "e": self.current_epoch,
            "s": self.total_steps_run,
            "n": len([b for b in self.bodies if b.is_active]),
            "sv": {
                "be": self.boundary_events,
                "im": round(self.injected_mass_total, 1),
                "ic": self.injected_count,
                "as": round(self.absorbed_by_star, 1),
                "me": self.merge_events,
                "rm": round(self.recycled_mass, 1),
                "rc": self.recycled_count
            },
            "eh": self.epoch_history[-20:],
            "b": [b.to_compact() for b in self.bodies if b.is_active]
        }

    def from_compact(self, data):
        self.run_id = data.get("r", self.run_id)
        self.current_epoch = data.get("e", 0)
        self.total_steps_run = data.get("s", 0)
        sv = data.get("sv", {})
        self.boundary_events = sv.get("be", 0)
        self.injected_mass_total = sv.get("im", 0)
        self.injected_count = sv.get("ic", 0)
        self.absorbed_by_star = sv.get("as", 0)
        self.merge_events = sv.get("me", 0)
        self.recycled_mass = sv.get("rm", 0)
        self.recycled_count = sv.get("rc", 0)
        self.epoch_history = data.get("eh", [])
        self.bodies = []
        for arr in data.get("b", []):
            self.bodies.append(CelestialBody.from_compact(arr))

    def big_bang(self, n_particles):
        self.bodies = []
        center = self.center_pos
        sun = CelestialBody(center, center, 6000, 5, 5500)
        sun.is_star = True; sun.origin = "bigbang"
        self.bodies.append(sun)
        for i in range(n_particles):
            dist = random.uniform(400, 2200)
            angle = random.uniform(0, 6.2832)
            bx = center + math.cos(angle) * dist
            by = center + math.sin(angle) * dist
            mass = random.uniform(5.0, 30.0)
            spin = random.uniform(1, 10)
            est = PhysicsKernel.calc_equilibrium_temp(5500, dist)
            body = CelestialBody(bx, by, mass, spin, est * random.uniform(0.5, 1.5))
            body.birth_dist = dist; body.origin = "bigbang"
            v_orb = math.sqrt(PhysicsKernel.G_CONST * sun.mass / dist)
            body.vx = -math.sin(angle) * v_orb + random.uniform(-0.15, 0.15)
            body.vy = math.cos(angle) * v_orb + random.uniform(-0.15, 0.15)
            body.vx += -math.sin(angle) * v_orb * PhysicsKernel.UNIVERSE_SPIN
            body.vy += math.cos(angle) * v_orb * PhysicsKernel.UNIVERSE_SPIN
            self.bodies.append(body)

    def inject_external_energy(self, step):
        if step % PhysicsKernel.ENERGY_INJECT_INTERVAL != 0: return
        center = self.center_pos
        for _ in range(PhysicsKernel.ENERGY_INJECT_COUNT):
            angle = random.uniform(0, 6.2832)
            sd = PhysicsKernel.UNIVERSE_RADIUS * PhysicsKernel.BOUNDARY_START * 0.95
            bx = center + math.cos(angle) * sd
            by = center + math.sin(angle) * sd
            mass = random.uniform(3.0, 12.0)
            body = CelestialBody(bx, by, mass, random.uniform(1, 8), random.uniform(50, 250))
            body.birth_dist = sd; body.origin = "injected"
            ins = random.uniform(1.5, 3.0)
            body.vx = -math.cos(angle) * ins
            body.vy = -math.sin(angle) * ins
            tan = ins * random.uniform(0.3, 0.8)
            body.vx += -math.sin(angle) * tan
            body.vy += math.cos(angle) * tan
            self.bodies.append(body)
            self.injected_mass_total += mass
            self.injected_count += 1

    def run_epoch(self, steps):
        main_star = self.bodies[0]
        cell_size = 50; center = self.center_pos

        for step in range(steps):
            self.inject_external_energy(self.total_steps_run)
            self.total_steps_run += 1
            grid = {}

            body_count = len(self.bodies)
            for idx in range(body_count):
                b = self.bodies[idx]
                if not b.is_active: continue
                b.update_thermodynamics(main_star)
                b.move()
                if not b.is_star:
                    b.apply_black_hole_boundary(center, self)
                if not b.is_active: continue

                gx = int(b.x / cell_size); gy = int(b.y / cell_size)
                key = (gx, gy)
                if key not in grid: grid[key] = []
                grid[key].append(b)
                if b is not main_star:
                    ddx = main_star.x - b.x; ddy = main_star.y - b.y
                    dsq = ddx * ddx + ddy * ddy + 100.0
                    dd = math.sqrt(dsq)
                    f = (PhysicsKernel.G_CONST * main_star.mass * b.mass) / dsq
                    b.vx += (ddx / dd) * f / b.mass
                    b.vy += (ddy / dd) * f / b.mass

            for key in grid:
                cell = grid[key]
                if len(cell) < 2: continue
                for i in range(len(cell)):
                    b1 = cell[i]
                    if not b1.is_active: continue
                    for j in range(i + 1, len(cell)):
                        b2 = cell[j]
                        if not b2.is_active: continue
                        cd = math.hypot(b1.x - b2.x, b1.y - b2.y)
                        if cd < (b1.radius + b2.radius) * 0.8:
                            self.merge_bodies(b1, b2)

            main_star.x = center; main_star.y = center
            main_star.vx = 0; main_star.vy = 0

            if step % 60 == 0:
                self.bodies = [b for b in self.bodies if b.is_active]

        self.absorbed_by_star = main_star.mass - 6000
        snapshot = self.collect_snapshot()
        self.epoch_history.append({
            "ep": self.current_epoch,
            "sn": snapshot,
            "sm": round(main_star.mass, 1),
            "ts": self.total_steps_run
        })
        self.current_epoch += 1

    def merge_bodies(self, b1, b2):
        if not b1.is_active or not b2.is_active: return
        self.merge_events += 1
        if b1.is_star:
            b1.mass += b2.mass
            b1.radius = PhysicsKernel.get_radius(b1.mass, b1.spin)
            b2.is_active = False; return
        if b2.is_star:
            b2.mass += b1.mass
            b2.radius = PhysicsKernel.get_radius(b2.mass, b2.spin)
            b1.is_active = False; return
        w, l = (b1, b2) if b1.mass > b2.mass else (b2, b1)
        tm = w.mass + l.mass
        w.vx = (w.vx * w.mass + l.vx * l.mass) / tm
        w.vy = (w.vy * w.mass + l.vy * l.mass) / tm
        w.temp = ((w.temp * w.mass + l.temp * l.mass) / tm) + random.uniform(50, 200)
        w.spin = (w.spin * w.mass + l.spin * l.mass) / tm
        for k in w.composition:
            w.composition[k] += l.composition.get(k, 0)
        w.mass = tm
        w.radius = PhysicsKernel.get_radius(w.mass, w.spin)
        w.boundary_hits = max(w.boundary_hits, l.boundary_hits)
        w.tidal_damage = max(w.tidal_damage, l.tidal_damage) * 0.7
        w.shred_immunity = max(w.shred_immunity, l.shred_immunity)
        l.is_active = False

    def collect_snapshot(self):
        star = self.bodies[0] if self.bodies else None
        active = [b for b in self.bodies if b.is_active and not b.is_star]
        if not active or not star: return {"n": 0}

        zones = {"i": [], "m": [], "o": []}
        org = {"bigbang": 0, "injected": 0, "recycled": 0}
        dists = []; bound_count = 0; buffer_count = 0

        for b in active:
            d = math.hypot(b.x - star.x, b.y - star.y)
            dists.append(d)
            org[b.origin] = org.get(b.origin, 0) + 1
            ke = b.calc_kinetic_energy()
            pe = b.calc_potential_energy(star)
            if ke + pe < 0: bound_count += 1
            if b.in_buffer_zone: buffer_count += 1
            if d < 700: zones["i"].append(b)
            elif d < 1400: zones["m"].append(b)
            else: zones["o"].append(b)

        abins = [0] * 8
        for b in active:
            ang = math.atan2(b.y - star.y, b.x - star.x) + math.pi
            abins[int(ang / (2 * math.pi) * 8) % 8] += 1
        avg_bin = len(active) / 8
        max_dev = max(abs(c - avg_bin) for c in abins) if avg_bin > 0 else 0
        uni = round(1.0 - (max_dev / max(avg_bin, 1)), 3)

        zs = {}
        for zn, zb in zones.items():
            if zb:
                zs[zn] = {
                    "n": len(zb),
                    "t": [round(min(b.temp for b in zb), 1),
                          round(max(b.temp for b in zb), 1)],
                    "m": [round(min(b.mass for b in zb), 1),
                          round(max(b.mass for b in zb), 1)],
                    "bh": sum(b.boundary_hits for b in zb)
                }
            else:
                zs[zn] = {"n": 0}

        return {
            "n": len(active), "st": round(star.temp, 1), "sm": round(star.mass, 1),
            "z": zs, "org": org,
            "avg_d": round(sum(dists) / len(dists), 1),
            "bound": bound_count,
            "bound_pct": round(bound_count / len(active) * 100, 1),
            "uni": uni, "abins": abins,
            "tbh": sum(b.boundary_hits for b in active),
            "buf": buffer_count,
            "buf_pct": round(buffer_count / len(active) * 100, 1)
        }


# ==========================================
# 4. 地球物理
# ==========================================
class PlanetaryGeophysics:
    @staticmethod
    def calculate_atmosphere(mass, temp):
        gh = max(0, mass - 8) / 12.0
        te = max(0.1, 1.0 - (temp / 1500.0))
        p = gh * te * random.uniform(0.6, 1.4)
        comp = {}
        if p < 0.1:
            comp = {"CO2": 0.95, "N2": 0.05}
        elif p > 5.0:
            comp = {"H2": 0.6, "He": 0.3, "Ar": 0.1}
        else:
            n2 = random.uniform(0.7, 0.8)
            co2 = random.uniform(0.01, 0.1)
            o2 = random.uniform(0.05, 0.25) if -5 < temp < 60 else 0.0
            t = n2 + co2 + o2
            if t > 0:
                comp = {"N2": round(n2/t, 3), "CO2": round(co2/t, 3), "O2": round(o2/t, 3)}
            else:
                comp = {"N2": 1.0}
        return round(p, 3), comp

    @staticmethod
    def analyze_habitability(temp, pressure, mass, volatiles):
        wp = (volatiles / mass) * 3.0 if mass > 0 else 0
        sw = min(100, wp * 100 * random.uniform(0.8, 1.2))
        if pressure < 0.06: bp = -100
        elif pressure > 0: bp = 100.0 * (pressure ** 0.15)
        else: bp = -100
        if pressure < 0.2:
            state = "Sublimation"; biome = "Barren"
        elif temp < 0:
            state = "Ice"; biome = "Snowball"
        elif temp > min(bp, 65.0):
            state = "Gas"; biome = "Scorched"
        else:
            state = "Liquid"
            if sw < 20: biome = "Desert"
            elif sw < 50: biome = "Arid"
            elif sw < 80: biome = "Gaia"
            else: biome = "Ocean"
        return {"state": state, "biome": biome, "water": round(sw, 1)}


# ==========================================
# 5. 數據提取
# ==========================================
class DataExtraction:
    @staticmethod
    def classify(mass, is_star=False):
        if is_star: return "S"
        if mass > 300: return "BD"
        if mass > 80: return "GG"
        if mass > 30: return "IG"
        if mass > 10: return "RP"
        return "DP"

    @staticmethod
    def compact_planet(target, star, dist):
        p, a = PlanetaryGeophysics.calculate_atmosphere(target.mass, target.temp)
        h = PlanetaryGeophysics.analyze_habitability(
            target.temp, p, target.mass, target.composition['Vo']
        )
        return {
            "id": target.cid, "tp": DataExtraction.classify(target.mass),
            "m": round(target.mass, 1), "d": round(dist, 0),
            "t": round(target.temp, 1), "p": p, "a": a,
            "w": h["water"], "ws": h["state"], "bi": h["biome"],
            "tl": round(target.axial_tilt, 1),
            "og": target.origin, "bh": target.boundary_hits,
            "td": round(target.tidal_damage, 2)
        }


# ==========================================
# 6. 存檔管理
# ==========================================
SAVE_DIR = "universe_saves"
SAVE_FILE = os.path.join(SAVE_DIR, "state.json")
REPORT_FILE = os.path.join(SAVE_DIR, "report_summary.json")

class SaveManager:
    @staticmethod
    def ensure_dir():
        if not os.path.exists(SAVE_DIR): os.makedirs(SAVE_DIR)

    @staticmethod
    def load():
        if not os.path.exists(SAVE_FILE): return None
        try:
            with open(SAVE_FILE, 'r') as f: return json.load(f)
        except: return None

    @staticmethod
    def load_engine():
        data = SaveManager.load()
        if not data: return None
        for c in reversed(data.get("chunks", [])):
            if c.get("type") == "ENGINE": return c["data"]
        return None

