#!/usr/bin/env python
"""
Reads from stdin and parses file into size and rows summary
"""


import sys

def read_input(file):
    for line in file:
        # split the line into words
        x = 0
        if 'asize' in line:
            x = int(line.split(':')[2].split(',')[0])
        yield x


def main(separator='\t'):
    # input comes from STDIN (standard input)
    import time
    start = time.time()
    data = read_input(sys.stdin)
    total = 0
    count = 0
    for line in data:
        total += line
        count += 1
    end = time.time()
    msg = '{"total_lines":%s,"total_size":%s,"parse_time":%s}' % (str(count),str(total),str(end-start))
    print msg


if __name__ == "__main__":
    main()