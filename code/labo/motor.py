"""Decodeur moteur calibre sur l'activite spontanee, sans acces a la balle."""
import math


class MotorDecoder:
    def __init__(self, dt=0.01, smoothing_s=0.15):
        self.dt = dt
        self.alpha = 1 - math.exp(-dt / smoothing_s)
        self.seconds = 0.0
        self.totals = [0, 0]
        self.baseline = [1.0, 1.0]
        self.rates = [0.0, 0.0]
        self.ready = False

    def update(self, up, down, calibrating=False):
        if calibrating:
            self.seconds += self.dt
            self.totals[0] += up
            self.totals[1] += down
            self.baseline = [max(1.0, n / self.seconds) for n in self.totals]
            return 0.0
        if not self.ready:
            self.ready = True
            self.rates = [0.0, 0.0]
        for i, count in enumerate((up, down)):
            self.rates[i] += self.alpha * (count / self.dt - self.rates[i])
        # Aucun signal ne produit aucun deplacement. Les taux sont integres sur
        # 150 ms pour eviter les petites secousses de chaque impulsion isolee.
        if sum(self.rates) < 1.0:
            return 0.0
        u, d = (rate / base for rate, base in zip(self.rates, self.baseline))
        return (d - u) / max(u + d, 1.0)
