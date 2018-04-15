#!/usr/bin/env python3
"""NTRU v0.1

Usage:
  ntru.py [options] enc PUB_KEY_FILE [FILE]
  ntru.py [options] dec PRIV_KEY_FILE [FILE]
  ntru.py [options] gen N P Q PRIV_KEY_FILE PUB_KEY_FILE
  ntru.py [options] sav N P Q F G PRIV_KEY_FILE PUB_KEY_FILE
  ntru.py (-h | --help)
  ntru.py --version

Options:
  -p, --poly     Interpret input (enc) or output (dec)
                   as polynomial represented by integer array.
  -h, --help     Show this screen.
  --version      Show version.
  -d, --debug    Debug mode.
  -v, --verbose  Verbose mode.

"""
from docopt import docopt
from ntru.ntrucipher import NtruCipher
from sympy.abc import x
from sympy import ZZ, Poly
import numpy as np
import sys
import logging

log = logging.getLogger("ntru")

debug = False
verbose = False


def generate(N, p, q, priv_key_file, pub_key_file):
    ntru = NtruCipher(N, p, q)
    ntru.generate_random_keys()
    h = np.array(ntru.h_poly.all_coeffs()[::-1])
    f, f_p = ntru.f_poly.all_coeffs()[::-1], ntru.f_p_poly.all_coeffs()[::-1]
    np.savez_compressed(priv_key_file, N=N, p=p, q=q, f=f, f_p=f_p)
    log.info("Private key saved to {} file".format(priv_key_file))
    np.savez_compressed(pub_key_file, N=N, p=p, q=q, h=h)
    log.info("Private key saved to {} file".format(pub_key_file))


def encrypt(pub_key_file, input_arr):
    pub_key = np.load(pub_key_file)
    ntru = NtruCipher(int(pub_key['N']), int(pub_key['p']), int(pub_key['q']))
    if (ntru.N < len(input_arr)):
        raise Exception("Input is too large for current N")
    ntru.h_poly = Poly(pub_key['h'].astype(np.int)[::-1], x).set_domain(ZZ)
    return (ntru.encrypt(Poly(input_arr[::-1], x).set_domain(ZZ),
                         Poly(np.random.randint(-1, 2, size=ntru.N), x).set_domain(ZZ)).all_coeffs()[::-1])


def decrypt(priv_key_file, input_arr):
    pub_key = np.load(priv_key_file)
    ntru = NtruCipher(int(pub_key['N']), int(pub_key['p']), int(pub_key['q']))
    ntru.f_poly = Poly(pub_key['f'].astype(np.int)[::-1], x).set_domain(ZZ)
    ntru.f_p_poly = Poly(pub_key['f_p'].astype(np.int)[::-1], x).set_domain(ZZ)
    return (ntru.decrypt(Poly(input_arr[::-1], x).set_domain(ZZ)).all_coeffs()[::-1])


if __name__ == '__main__':
    args = docopt(__doc__, version='NTRU v0.1')
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    ch = logging.StreamHandler(sys.stdout)
    if args['--debug']:
        ch.setLevel(logging.DEBUG)
    elif args['--verbose']:
        ch.setLevel(logging.INFO)
    else:
        ch.setLevel(logging.WARN)
    root.addHandler(ch)

    log.debug(args)
    polynomial = bool(args['--poly'])
    if not args['gen']:
        if args['FILE'] is None or args['FILE'] == '-':
            input = sys.stdin.read()
        else:
            with open(args['FILE'], 'rb') as file:
                input = file.read()
        log.info("---INPUT---")
        log.info(input)
        log.info("-----------")

    if args['gen']:
        generate(int(args['N']), int(args['P']), int(args['Q']), args['PRIV_KEY_FILE'], args['PUB_KEY_FILE'])
    elif args['enc']:
        if polynomial:
            input_arr = eval(input)
        else:
            input_arr = np.unpackbits(np.frombuffer(input, dtype=np.uint8))
        log.info("POLYNOMIAL LENGTH: {}".format(len(input_arr)))
        log.debug("BINARY: {}".format(input_arr))
        print(str(encrypt(args['PUB_KEY_FILE'], input_arr)))
    elif args['dec']:
        output = decrypt(args['PRIV_KEY_FILE'], eval(input))
        if polynomial:
            print(str(output))
        else:
            sys.stdout.buffer.write(np.packbits(np.array(output).astype(np.int)).tobytes())
