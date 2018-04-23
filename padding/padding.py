import numpy as np


def padding_encode(input_arr, block_size):
    n = block_size - len(input_arr) % block_size
    if n == block_size:
        return np.pad(input_arr, (0, n), 'constant')
    last_block = np.pad(np.ones(n), (block_size - n, 0), 'constant')
    return np.concatenate((np.pad(input_arr, (0, n), 'constant'), last_block))


def padding_decode(input_arr, block_size):
    last_block = input_arr[-block_size:]
    zeros_to_remove = len(np.trim_zeros(last_block))
    return input_arr[:-(block_size + zeros_to_remove)]
