"""Culture de neurones virtuelle, branchee dans le simulateur du SDK Cortical Labs.

Remplace la source aleatoire du simulateur par un vrai reseau de neurones
impulsionnels (modele d'Izhikevich 2003) pose sur une puce de 8 x 8 electrodes :
- les synapses se renforcent ou s'affaiblissent selon l'ordre des impulsions
  (STDP) : la culture peut apprendre ;
- les synapses se fatiguent a court terme, ce qui produit les "bouffees"
  d'activite typiques des vraies cultures ;
- chaque electrode n'entend que les neurones tout proches, et une stimulation
  excite les neurones autour de l'electrode (plus loin si le courant est fort).

Le code d'experience parle a cette culture via l'API officielle `cl`, exactement
comme a une vraie puce CL1.
"""
import bisect
import heapq
import sys

import numpy as np
from cl.sim import DataSourceBatch, DataSourceSpike, SimulatorDataSource, SimulatorDataSourceMetadata

FRAMES_PER_STEP = 25              # 1 ms de simulation (le SDK compte en trames a 25 kHz)
STEPS_PER_BLOCK = 1000            # bruit tire et plasticite appliquee par blocs de 1 s
GRID = 8                          # canal = ligne * 8 + colonne
DEAD_CHANNELS = (0, 4, 7, 56, 63)  # masses et reference, comme sur la vraie puce
METADATA = SimulatorDataSourceMetadata(channel_count=GRID * GRID, seekable=False)

W_EXC = 5.0          # poids initial d'une synapse excitatrice (mV)
W_INH = 6.0          # poids d'une synapse inhibitrice (mV, signe negatif)
W_MAX = 10.0
NOISE = (3.0, 2.0)   # bruit de fond des neurones excitateurs / inhibiteurs
A_PLUS, A_MINUS = 0.05, 0.06
DW_DECAY = 0.5       # les changements STDP s'appliquent sur ~2 s
TARGET_HZ = 1.5      # frequence de tir visee par l'homeostasie (reglable par experience)
USE = 0.3            # part des ressources consommee par impulsion (fatigue)
RECOVERY_MS = 800    # recuperation de la fatigue synaptique
RECORD_RADIUS = 0.3  # en ecarts entre electrodes
STIM_RADIUS = 0.35


class Culture:
    def __init__(self, seed, plastic=True, stdp_tau_ms=20.0, target_hz=TARGET_HZ, n=1000):
        rng = self.rng = np.random.default_rng(seed)
        self.n, self.ne = n, int(0.8 * n)
        self.plastic = plastic
        self.target_hz = target_hz
        exc = np.arange(n) < self.ne
        r = rng.random(n).astype(np.float32)
        f32 = lambda x: np.asarray(x, dtype=np.float32)  # noqa: E731
        self.a = f32(np.where(exc, 0.02, 0.02 + 0.08 * r))
        self.b = f32(np.where(exc, 0.2, 0.25 - 0.05 * r))
        self.c = f32(np.where(exc, -65 + 15 * r**2, -65))
        self.d = f32(np.where(exc, 8 - 6 * r**2, 2))
        self.v = np.full(n, -65, np.float32)
        self.u = self.b * self.v
        self.sigma = f32(np.where(exc, *NOISE))

        # Connexions surtout locales, comme dans une culture qui a pousse sur la puce.
        pos = rng.uniform(0, GRID, size=(n, 2)).astype(np.float32)
        dist = np.linalg.norm(pos[:, None] - pos[None], axis=-1)  # [post, pre]
        conn = rng.random((n, n)) < 0.3 * np.exp(-dist / 1.5)
        np.fill_diagonal(conn, False)
        self.W = conn.astype(np.float32)
        self.W[:, :self.ne] *= W_EXC
        self.W[:, self.ne:] *= -W_INH
        self.mask = conn[:, :self.ne].astype(np.float32)  # seules les synapses excitatrices apprennent

        cols, rows = np.arange(GRID * GRID) % GRID, np.arange(GRID * GRID) // GRID
        elec = np.stack([cols + 0.5, rows + 0.5], axis=1).astype(np.float32)
        de = np.linalg.norm(pos[:, None] - elec[None], axis=-1)  # [neurone, electrode]
        self.rec_ch = np.where(de.min(1) < RECORD_RADIUS, de.argmin(1), -1)
        self.rec_ch[np.isin(self.rec_ch, DEAD_CHANNELS)] = -1
        self.stim_gain = f32(40 * np.exp(-de.T**2 / (2 * STIM_RADIUS**2)))  # [electrode, neurone]

        self.res = np.ones(n, np.float32)              # ressources synaptiques (fatigue)
        self.use = f32(np.where(exc, USE, 0.0))
        self.trace = np.zeros(n, np.float32)           # memoire des impulsions recentes (STDP)
        self.trace_decay = np.float32(np.exp(-1 / stdp_tau_ms))
        self.dW = np.zeros((n, self.ne), np.float32)
        self.count = np.zeros(n, np.float32)           # impulsions de la seconde en cours
        self.rate = np.full(n, target_hz, np.float32)  # frequence moyenne recente (Hz)
        self.isyn = np.zeros(n, np.float32)
        self.stims = []                                 # tas de (trame, canal, intensite)
        self.applied = 0
        self.steps = 0
        self.last_fired = 0

    def add_stim(self, frame, channel, strength):
        heapq.heappush(self.stims, (frame, channel, strength))

    def step(self, t0):
        """Avance d'1 ms a partir de la trame t0. Renvoie les canaux ou une impulsion est enregistree."""
        k = self.steps % STEPS_PER_BLOCK
        if k == 0:
            if self.plastic and self.steps:
                self._apply_plasticity()
            self.noise = self.rng.standard_normal((STEPS_PER_BLOCK, self.n), dtype=np.float32)
            self.noise *= self.sigma
        self.steps += 1

        I = self.noise[k] + self.isyn
        while self.stims and self.stims[0][0] < t0 + FRAMES_PER_STEP:
            _, ch, strength = heapq.heappop(self.stims)
            I += strength * self.stim_gain[ch]
            self.applied += 1

        v, u = self.v, self.u
        for _ in range(2):  # deux demi-pas, comme dans le modele d'origine
            v += 0.5 * ((0.04 * v + 5) * v + 140 - u + I)
        np.minimum(v, 30, out=v)
        u += self.a * (self.b * v - u)
        self.res += (1 - self.res) / RECOVERY_MS
        if self.plastic:
            self.trace *= self.trace_decay

        fired = np.flatnonzero(v >= 30)
        self.last_fired = fired.size
        if not fired.size:
            self.isyn = np.zeros(self.n, np.float32)
            return fired
        v[fired] = self.c[fired]
        u[fired] += self.d[fired]
        self.count[fired] += 1
        eff = self.res[fired]
        self.isyn = self.W[:, fired] @ eff
        self.res[fired] -= self.use[fired] * eff
        if self.plastic:
            self._stdp(fired)
        ch = self.rec_ch[fired]
        return ch[ch >= 0]

    def _stdp(self, fired):
        tr = self.trace
        # Entree active juste avant -> la synapse se renforce.
        self.dW[fired] += A_PLUS * tr[:self.ne] * self.mask[fired]
        # Sortie active juste avant -> la synapse s'affaiblit.
        exc = fired[fired < self.ne]
        if exc.size:
            self.dW[:, exc] -= A_MINUS * tr[:, None] * self.mask[:, exc]
        tr[fired] += 1

    def _apply_plasticity(self):
        w = self.W[:, :self.ne]
        w += (0.005 + self.dW) * self.mask
        self.dW *= DW_DECAY
        # Homeostasie : un neurone qui s'emballe affaiblit ses entrees excitatrices,
        # un neurone trop calme les renforce (synaptic scaling).
        self.rate += 0.1 * (self.count - self.rate)
        self.count[:] = 0
        w *= ((self.target_hz / np.maximum(self.rate, 0.2)) ** 0.05)[:, None]
        np.clip(w, 0, W_MAX, out=w)


class CultureSource(SimulatorDataSource):
    def __init__(self, **config):
        self.config = config
        self.culture = None
        self.t = None
        self.pending = []

    @property
    def metadata(self):
        return METADATA

    def open(self):
        # Construit ici et pas dans __init__ : seul le sous-processus du simulateur en a besoin.
        self.culture = Culture(**self.config)

    def close(self):
        # Le sous-processus du simulateur n'a pas de logging configure : stderr finit dans le journal.
        c = self.culture
        if c is not None:
            print(f"culture {self.config} : {c.steps / 1000:.0f} s simulees, {c.applied} stimulations "
                  f"appliquees, {len(c.stims)} en attente", file=sys.stderr, flush=True)

    def on_stim(self, stim):
        if not stim.phase_currents_uA:
            strength = 1.0
        else:
            strength = max(abs(i) for i in stim.phase_currents_uA) * min(stim.duration_us / 320, 2.0)
        self.culture.add_stim(stim.timestamp, stim.channel, strength)

    def read(self, from_timestamp, frame_count):
        if self.t is None:
            self.t = from_timestamp
        end = from_timestamp + frame_count
        spikes = self.pending
        while self.t < end:
            ch = self.culture.step(self.t)
            if ch.size:
                ts = self.t + self.culture.rng.integers(0, FRAMES_PER_STEP, ch.size)
                spikes.extend(zip(ts.tolist(), ch.tolist()))
            self.t += FRAMES_PER_STEP
        spikes.sort()
        cut = bisect.bisect_left(spikes, (end, -1))
        self.pending = spikes[cut:]
        return DataSourceBatch(spikes=[DataSourceSpike(timestamp=t, channel=c)
                                       for t, c in spikes[:cut] if t >= from_timestamp])


def create_source(seed=0, plastic=True, stdp_tau_ms=20.0, target_hz=TARGET_HZ):
    return CultureSource(seed=seed, plastic=plastic, stdp_tau_ms=stdp_tau_ms, target_hz=target_hz)


if __name__ == "__main__":
    # Banc d'essai sans le SDK : activite spontanee et reponse a une stimulation.
    import time

    seconds = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    c = Culture(seed=1)
    for m in range(0, seconds, 60):
        fired, recorded = [], 0
        start = time.perf_counter()
        for s in range(m * 1000, min(m + 60, seconds) * 1000):
            if s % 500 == 250:
                c.add_stim(s * FRAMES_PER_STEP, 27, 1.0)
            recorded += c.step(s * FRAMES_PER_STEP).size
            fired.append(c.last_fired)
        f = np.array(fired)
        after = np.concatenate([f[i:i + 20] for i in range(250, len(f) - 20, 500)])
        dur = len(f) / 1000
        print(f"min {m // 60}: {dur / (time.perf_counter() - start):.1f}x temps reel | "
              f"{f.sum() / c.n / dur:.2f} Hz | enregistrees {recorded / dur:.0f} imp/s | "
              f"bouffees {(f > c.n // 10).sum()} pas | apres stim {after.mean():.1f}/ms | "
              f"poids {c.W[:, :c.ne][c.mask > 0].mean():.2f}")
