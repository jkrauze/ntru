from ntru.mathutils import *
import numpy as np
from sympy.abc import x
from sympy.polys.polyerrors import NotInvertible
from sympy import ZZ, Poly
import logging
from collections import Counter

log = logging.getLogger("ntrucipher")


class NtruCipher:
    N = None
    p = None
    q = None
    f_poly = None
    g_poly = None
    h_poly = None
    f_p_poly = None
    f_q_poly = None
    R_poly = None

    def __init__(self, N, p, q):
        self.N = N
        self.p = p
        self.q = q
        self.R_poly = Poly(x ** N - 1, x).set_domain(ZZ)
        log.info("NTRU(N={},p={},q={}) initiated".format(N, p, q))

    def generate_random_keys(self):
        g_poly = random_poly(self.N, int(math.sqrt(self.q)))
        log.info("g: {}".format(g_poly))
        log.info("g coeffs: {}".format(Counter(g_poly.coeffs())))


        tries = 10
        while tries > 0 and (self.h_poly is None):
            f_poly = random_poly(self.N, self.N // 3, neg_ones_diff=-1)
            log.info("f: {}".format(f_poly))
            log.info("f coeffs: {}".format(Counter(f_poly.coeffs())))
            try:
                self.generate_public_key(f_poly, g_poly)
            except NotInvertible as ex:
                log.info("Failed to invert f (tries left: {})".format(tries))
                log.debug(ex)
                tries -= 1
        if self.h_poly is None:
            raise Exception("Couldn't generate invertible f")

    def generate_public_key(self, f_poly, g_poly):
        self.f_poly = f_poly
        self.g_poly = g_poly
        log.debug("Trying to invert: {}".format(self.f_poly))
        self.f_p_poly = invert_poly(self.f_poly, self.R_poly, self.p)
        log.debug("f_p ok!")
        self.f_q_poly = invert_poly(self.f_poly, self.R_poly, self.q)
        log.debug("f_q ok!")
        log.info("f_p: {}".format(self.f_p_poly))
        log.info("f_q: {}".format(self.f_q_poly))
        log.debug("f*f_p mod (x^n - 1): {}".format(((self.f_poly * self.f_p_poly) % self.R_poly).trunc(self.p)))
        log.debug("f*f_q mod (x^n - 1): {}".format(((self.f_poly * self.f_q_poly) % self.R_poly).trunc(self.q)))
        p_f_q_poly = (self.p * self.f_q_poly).trunc(self.q)
        log.debug("p_f_q: {}".format(p_f_q_poly))
        h_before_mod = (p_f_q_poly * self.g_poly).trunc(self.q)
        log.debug("h_before_mod: {}".format(h_before_mod))
        self.h_poly = (h_before_mod % self.R_poly).trunc(self.q)
        log.info("h: {}".format(self.h_poly))

    def encrypt(self, msg_poly, rand_poly):
        log.info("r: {}".format(rand_poly))
        log.info("r coeffs: {}".format(Counter(rand_poly.coeffs())))
        log.info("msg: {}".format(msg_poly))
        log.info("h: {}".format(self.h_poly))
        return (((rand_poly * self.h_poly).trunc(self.q) + msg_poly) % self.R_poly).trunc(self.q)

    def decrypt(self, msg_poly):
        log.info("f: {}".format(self.f_poly))
        log.info("f_p: {}".format(self.f_p_poly))
        a_poly = ((self.f_poly * msg_poly) % self.R_poly).trunc(self.q)
        log.info("a: {}".format(a_poly))
        b_poly = a_poly.trunc(self.p)
        log.info("b: {}".format(b_poly))
        return ((self.f_p_poly * b_poly) % self.R_poly).trunc(self.p)
