#!/usr/bin/env python3
"""NTRU v0.1

Usage:
  ntru.py [options] enc PUB_KEY_FILE [FILE]
  ntru.py [options] dec PRIV_KEY_FILE [FILE]
  ntru.py [options] gen N P Q PRIV_KEY_FILE PUB_KEY_FILE
  ntru.py (-h | --help)
  ntru.py --version

Options:
  -b, --block        Interpret input/output as
                       block stream.
  -i, --poly-input   Interpret input as polynomial
                       represented by integer array.
  -o, --poly-output  Interpret output as polynomial
                       represented by integer array.
  -h, --help         Show this screen.
  --version          Show version.
  -d, --debug        Debug mode.
  -v, --verbose      Verbose mode.

"""
from docopt import docopt
from ntru.ntrucipher import NtruCipher
from ntru.mathutils import random_poly
from sympy.abc import x
from sympy import ZZ, Poly
from padding.padding import *
import numpy as np
import sys
import logging
import math

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
    log.info("Public key saved to {} file".format(pub_key_file))


def encrypt(pub_key_file, input_arr, bin_output=False, block=False):
    pub_key = np.load(pub_key_file, allow_pickle=True)
    ntru = NtruCipher(int(pub_key['N']), int(pub_key['p']), int(pub_key['q']))
    ntru.h_poly = Poly(pub_key['h'].astype(np.int)[::-1], x).set_domain(ZZ)
    if not block:
        if ntru.N < len(input_arr):
            raise Exception("Input is too large for current N")
        output = (ntru.encrypt(Poly(input_arr[::-1], x).set_domain(ZZ),
                               random_poly(ntru.N, int(math.sqrt(ntru.q)))).all_coeffs()[::-1])
    else:
        input_arr = padding_encode(input_arr, ntru.N)
        input_arr = input_arr.reshape((-1, ntru.N))
        output = np.array([])
        block_count = input_arr.shape[0]
        for i, b in enumerate(input_arr, start=1):
            log.info("Processing block {} out of {}".format(i, block_count))
            next_output = (ntru.encrypt(Poly(b[::-1], x).set_domain(ZZ),
                                        random_poly(ntru.N, int(math.sqrt(ntru.q)))).all_coeffs()[::-1])
            if len(next_output) < ntru.N:
                next_output = np.pad(next_output, (0, ntru.N - len(next_output)), 'constant')
            output = np.concatenate((output, next_output))

    if bin_output:
        k = int(math.log2(ntru.q))
        output = [[0 if c == '0' else 1 for c in np.binary_repr(n, width=k)] for n in output]
    return np.array(output).flatten()


def decrypt(priv_key_file, input_arr, bin_input=False, block=False):
    priv_key = np.load(priv_key_file, allow_pickle=True)
    ntru = NtruCipher(int(priv_key['N']), int(priv_key['p']), int(priv_key['q']))
    ntru.f_poly = Poly(priv_key['f'].astype(np.int)[::-1], x).set_domain(ZZ)
    ntru.f_p_poly = Poly(priv_key['f_p'].astype(np.int)[::-1], x).set_domain(ZZ)

    if bin_input:
        k = int(math.log2(ntru.q))
        pad = k - len(input_arr) % k
        if pad == k:
            pad = 0
        input_arr = np.array([int("".join(n.astype(str)), 2) for n in
                              np.pad(np.array(input_arr), (0, pad), 'constant').reshape((-1, k))])
    if not block:
        if ntru.N < len(input_arr):
            raise Exception("Input is too large for current N")
        log.info("POLYNOMIAL DEGREE: {}".format(max(0, len(input_arr) - 1)))
        return ntru.decrypt(Poly(input_arr[::-1], x).set_domain(ZZ)).all_coeffs()[::-1]

    input_arr = input_arr.reshape((-1, ntru.N))
    output = np.array([])
    block_count = input_arr.shape[0]
    for i, b in enumerate(input_arr, start=1):
        log.info("Processing block {} out of {}".format(i, block_count))
        next_output = ntru.decrypt(Poly(b[::-1], x).set_domain(ZZ)).all_coeffs()[::-1]
        if len(next_output) < ntru.N:
            next_output = np.pad(next_output, (0, ntru.N - len(next_output)), 'constant')
        output = np.concatenate((output, next_output))
    return padding_decode(output, ntru.N)


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
    poly_input = bool(args['--poly-input'])
    poly_output = bool(args['--poly-output'])
    block = bool(args['--block'])
    input_arr, output = None, None
    if not args['gen']:
        if args['FILE'] is None or args['FILE'] == '-':
            input = sys.stdin.read() if poly_input else sys.stdin.buffer.read()
        else:
            with open(args['FILE'], 'rb') as file:
                input = file.read()
        log.info("---INPUT---")
        log.info(input)
        log.info("-----------")
        if poly_input:
            input_arr = np.array(eval(input))
        else:
            input_arr = np.unpackbits(np.frombuffer(input, dtype=np.uint8))
        input_arr = np.trim_zeros(input_arr, 'b')
        log.info("POLYNOMIAL DEGREE: {}".format(max(0, len(input_arr) - 1)))
        log.debug("BINARY: {}".format(input_arr))

    if args['gen']:
        generate(int(args['N']), int(args['P']), int(args['Q']), args['PRIV_KEY_FILE'], args['PUB_KEY_FILE'])
    elif args['enc']:
        output = encrypt(args['PUB_KEY_FILE'], input_arr, bin_output=not poly_output, block=block)
    elif args['dec']:
        output = decrypt(args['PRIV_KEY_FILE'], input_arr, bin_input=not poly_input, block=block)

    if not args['gen']:
        if poly_output:
            print(list(output.astype(np.int)))
        else:
            sys.stdout.buffer.write(np.packbits(np.array(output).astype(np.int)).tobytes())
