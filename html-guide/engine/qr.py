"""engine.qr -- a QR code as an SVG, standard library only (Hugo's `qr`).

    svg("https://example.org", level="medium") -> "<svg ...>...</svg>"
    matrix(text, level) -> rows of booleans (True is a dark module)

Byte mode (the text as UTF-8), any of the four error-correction levels, the
smallest of the forty versions the text fits, and the mask with the lowest
penalty -- ISO/IEC 18004 as Project Nayuki's reference implementation
("QR Code generator library", MIT) lays it out, which is what the tables
and the steps below follow.  A code is always drawn dark on light, with the
four-module quiet zone around it that a scanner needs, whatever the page's
theme: a light code on a dark ground is one many phones will not read.
"""

# error-correction codewords per block, and the number of blocks, by level
# (L, M, Q, H) and version (index 0 unused)
_ECC_PER_BLOCK = (
    (-1, 7, 10, 15, 20, 26, 18, 20, 24, 30, 18, 20, 24, 26, 30, 22, 24, 28, 30, 28, 28,
     28, 28, 30, 30, 26, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
    (-1, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26, 26, 26,
     26, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28),
    (-1, 13, 22, 18, 26, 18, 24, 18, 22, 20, 24, 28, 26, 24, 20, 30, 24, 28, 28, 26, 30,
     28, 30, 30, 30, 30, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
    (-1, 17, 28, 22, 16, 22, 28, 26, 26, 24, 28, 24, 28, 22, 24, 24, 30, 28, 28, 26, 28,
     30, 24, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
)
_NUM_BLOCKS = (
    (-1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 4, 4, 4, 4, 4, 6, 6, 6, 6, 7, 8,
     8, 9, 9, 10, 12, 12, 12, 13, 14, 15, 16, 17, 18, 19, 19, 20, 21, 22, 24, 25),
    (-1, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16,
     17, 17, 18, 20, 21, 23, 25, 26, 28, 29, 31, 33, 35, 37, 38, 40, 43, 45, 47, 49),
    (-1, 1, 1, 2, 2, 4, 4, 6, 6, 8, 8, 8, 10, 12, 16, 12, 17, 16, 18, 21, 20,
     23, 23, 25, 27, 29, 34, 34, 35, 38, 40, 43, 45, 48, 51, 53, 56, 59, 62, 65, 68),
    (-1, 1, 1, 2, 4, 4, 4, 5, 6, 8, 8, 11, 11, 16, 16, 18, 16, 19, 21, 25, 25,
     25, 34, 30, 32, 35, 37, 40, 42, 45, 48, 51, 54, 57, 60, 63, 66, 70, 74, 77, 81),
)
_LEVELS = {"low": 0, "l": 0, "medium": 1, "m": 1, "quartile": 2, "q": 2, "high": 3, "h": 3}
_FORMAT_BITS = (1, 0, 3, 2)          # L M Q H, as the format information writes them

_MASKS = (
    lambda x, y: (x + y) % 2,
    lambda x, y: y % 2,
    lambda x, y: x % 3,
    lambda x, y: (x + y) % 3,
    lambda x, y: (x // 3 + y // 2) % 2,
    lambda x, y: x * y % 2 + x * y % 3,
    lambda x, y: (x * y % 2 + x * y % 3) % 2,
    lambda x, y: ((x + y) % 2 + x * y % 3) % 2,
)


def _bit(x, i):
    return (x >> i) & 1 != 0


def _raw_modules(ver):
    n = (16 * ver + 128) * ver + 64
    if ver >= 2:
        align = ver // 7 + 2
        n -= (25 * align - 10) * align - 55
        if ver >= 7:
            n -= 36
    return n


def _data_codewords(ver, ecl):
    return _raw_modules(ver) // 8 - _ECC_PER_BLOCK[ecl][ver] * _NUM_BLOCKS[ecl][ver]


def _gf_mul(x, y):
    z = 0
    for i in reversed(range(8)):
        z = (z << 1) ^ ((z >> 7) * 0x11D)
        z ^= ((y >> i) & 1) * x
    return z


def _rs_divisor(degree):
    result = [0] * (degree - 1) + [1]
    root = 1
    for _ in range(degree):
        for j in range(degree):
            result[j] = _gf_mul(result[j], root)
            if j + 1 < degree:
                result[j] ^= result[j + 1]
        root = _gf_mul(root, 0x02)
    return result


def _rs_remainder(data, divisor):
    result = [0] * len(divisor)
    for b in data:
        factor = b ^ result.pop(0)
        result.append(0)
        for i, coef in enumerate(divisor):
            result[i] ^= _gf_mul(coef, factor)
    return result


def _codewords(data, ver, ecl):
    """The data bytes -> every codeword of the symbol, blocks interleaved."""
    blocks_n = _NUM_BLOCKS[ecl][ver]
    ecc_len = _ECC_PER_BLOCK[ecl][ver]
    raw = _raw_modules(ver) // 8
    short_n = blocks_n - raw % blocks_n
    short_len = raw // blocks_n
    div = _rs_divisor(ecc_len)
    blocks, k = [], 0
    for i in range(blocks_n):
        take = short_len - ecc_len + (0 if i < short_n else 1)
        dat = data[k:k + take]
        k += take
        ecc = _rs_remainder(dat, div)
        if i < short_n:
            dat = dat + [0]
        blocks.append(dat + ecc)
    out = []
    for i in range(len(blocks[0])):
        for j, blk in enumerate(blocks):
            if i != short_len - ecc_len or j >= short_n:
                out.append(blk[i])
    return out


class _Symbol:
    def __init__(self, ver, ecl):
        self.ver, self.ecl = ver, ecl
        self.size = ver * 4 + 17
        self.mod = [[False] * self.size for _ in range(self.size)]
        self.fn = [[False] * self.size for _ in range(self.size)]

    def set_fn(self, x, y, dark):
        self.mod[y][x] = dark
        self.fn[y][x] = True

    def draw_patterns(self):
        size = self.size
        for i in range(size):
            self.set_fn(6, i, i % 2 == 0)
            self.set_fn(i, 6, i % 2 == 0)
        for cx, cy in ((3, 3), (size - 4, 3), (3, size - 4)):
            for dy in range(-4, 5):
                for dx in range(-4, 5):
                    x, y = cx + dx, cy + dy
                    if 0 <= x < size and 0 <= y < size:
                        self.set_fn(x, y, max(abs(dx), abs(dy)) not in (2, 4))
        pos = self.alignment_positions()
        n = len(pos)
        for i in range(n):
            for j in range(n):
                if (i, j) in ((0, 0), (0, n - 1), (n - 1, 0)):
                    continue
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        self.set_fn(pos[i] + dx, pos[j] + dy, max(abs(dx), abs(dy)) != 1)
        self.draw_format(0)
        if self.ver >= 7:
            rem = self.ver
            for _ in range(12):
                rem = (rem << 1) ^ ((rem >> 11) * 0x1F25)
            bits = self.ver << 12 | rem
            for i in range(18):
                bit = _bit(bits, i)
                a, b = size - 11 + i % 3, i // 3
                self.set_fn(a, b, bit)
                self.set_fn(b, a, bit)

    def alignment_positions(self):
        if self.ver == 1:
            return []
        n = self.ver // 7 + 2
        step = (self.ver * 8 + n * 3 + 5) // (n * 4 - 4) * 2
        return list(reversed([self.size - 7 - i * step for i in range(n - 1)] + [6]))

    def draw_format(self, mask):
        data = _FORMAT_BITS[self.ecl] << 3 | mask
        rem = data
        for _ in range(10):
            rem = (rem << 1) ^ ((rem >> 9) * 0x537)
        bits = (data << 10 | rem) ^ 0x5412
        size = self.size
        for i in range(6):
            self.set_fn(8, i, _bit(bits, i))
        self.set_fn(8, 7, _bit(bits, 6))
        self.set_fn(8, 8, _bit(bits, 7))
        self.set_fn(7, 8, _bit(bits, 8))
        for i in range(9, 15):
            self.set_fn(14 - i, 8, _bit(bits, i))
        for i in range(8):
            self.set_fn(size - 1 - i, 8, _bit(bits, i))
        for i in range(8, 15):
            self.set_fn(8, size - 15 + i, _bit(bits, i))
        self.set_fn(8, size - 8, True)

    def draw_codewords(self, data):
        i, size = 0, self.size
        right = size - 1
        while right >= 1:
            if right == 6:
                right = 5
            for vert in range(size):
                for j in range(2):
                    x = right - j
                    upward = ((right + 1) & 2) == 0
                    y = size - 1 - vert if upward else vert
                    if not self.fn[y][x] and i < len(data) * 8:
                        self.mod[y][x] = _bit(data[i >> 3], 7 - (i & 7))
                        i += 1
            right -= 2

    def apply_mask(self, mask):
        f = _MASKS[mask]
        for y in range(self.size):
            for x in range(self.size):
                if not self.fn[y][x] and f(x, y) == 0:
                    self.mod[y][x] = not self.mod[y][x]


def _penalty(m):
    size, score = len(m), 0
    for lines in (m, [list(col) for col in zip(*m)]):
        for row in lines:
            run = 1
            for k in range(1, size):
                if row[k] == row[k - 1]:
                    run += 1
                else:
                    if run >= 5:
                        score += run - 2
                    run = 1
            if run >= 5:
                score += run - 2
            # a finder-like 1:1:3:1:1 with four light modules on a side
            s = "".join("1" if v else "0" for v in row)
            for pat in ("10111010000", "00001011101"):
                start = s.find(pat)
                while start >= 0:
                    score += 40
                    start = s.find(pat, start + 1)
    for y in range(size - 1):
        for x in range(size - 1):
            c = m[y][x]
            if c == m[y][x + 1] == m[y + 1][x] == m[y + 1][x + 1]:
                score += 3
    dark = sum(sum(1 for v in row if v) for row in m)
    total = size * size
    k = (abs(dark * 20 - total * 10) + total - 1) // total - 1
    return score + max(0, k) * 10


def matrix(text, level="medium"):
    """The text -> the symbol's modules, rows of booleans, no quiet zone."""
    ecl = _LEVELS.get(str(level).strip().lower())
    if ecl is None:
        raise ValueError("no such error-correction level: %r (low, medium, quartile, high)"
                         % level)
    data = text.encode("utf-8")
    for ver in range(1, 41):
        count_bits = 8 if ver <= 9 else 16
        if 4 + count_bits + len(data) * 8 <= _data_codewords(ver, ecl) * 8:
            break
    else:
        raise ValueError("%d bytes do not fit in the largest QR code" % len(data))
    bits = [0, 1, 0, 0]
    bits += [(len(data) >> i) & 1 for i in reversed(range(count_bits))]
    for byte in data:
        bits += [(byte >> i) & 1 for i in reversed(range(8))]
    cap = _data_codewords(ver, ecl) * 8
    bits += [0] * min(4, cap - len(bits))
    bits += [0] * (-len(bits) % 8)
    words = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
    pad = 0xEC
    while len(words) < cap // 8:
        words.append(pad)
        pad ^= 0xEC ^ 0x11
    sym = _Symbol(ver, ecl)
    sym.draw_patterns()
    sym.draw_codewords(_codewords(words, ver, ecl))
    best, best_score = None, None
    for mask in range(8):
        sym.apply_mask(mask)
        sym.draw_format(mask)
        score = _penalty(sym.mod)
        if best_score is None or score < best_score:
            best, best_score = mask, score
        sym.apply_mask(mask)            # a mask is its own inverse
    sym.apply_mask(best)
    sym.draw_format(best)
    return sym.mod


def svg(text, level="medium", scale=4, border=4):
    """The text as a QR code: an SVG `scale` pixels a module, `border`
    modules of quiet zone round it."""
    m = matrix(text, level)
    n = len(m) + 2 * border
    path = "".join("M%d %dh1v1h-1z" % (x + border, y + border)
                   for y, row in enumerate(m) for x, dark in enumerate(row) if dark)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d"'
            ' shape-rendering="crispEdges" class="g-qr-code"><rect width="%d" height="%d"'
            ' fill="#fff"/><path d="%s" fill="#000"/></svg>'
            % (n, n, n * scale, n * scale, n, n, path))
