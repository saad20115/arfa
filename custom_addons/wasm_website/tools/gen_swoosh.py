"""ARFA hero wave: the original sweep (low on the left, high on the right, like the logo),
in the logo gold, with extra travelling ripples. Writes 4 SVGs (light / white, animated / static)."""
import math, sys
W, H = 1440, 300
N = 36           # segments per edge
K = 8            # keyframes per loop
DUR = 6          # seconds per loop

def bez(p0, p1, p2, p3, t):
    u = 1 - t
    return (u**3*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t**3*p3[0],
            u**3*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t**3*p3[1])

# the original hero curve: M0,155 C360,230 720,165 1080,80 C1260,35 1380,15 1440,10
SEG = [((0, 150), (360, 228), (720, 165), (1080, 82)), ((1080, 82), (1260, 40), (1380, 22), (1440, 18))]
TAB = [bez(*s, i / 500) for s in SEG for i in range(500)] + [SEG[-1][3]]

def base(x):
    lo, hi = 0, len(TAB) - 1
    while hi - lo > 1:
        m = (lo + hi) // 2
        if TAB[m][0] <= x: lo = m
        else: hi = m
    (x0, y0), (x1, y1) = TAB[lo], TAB[hi]
    return y0 + (y1 - y0) * ((x - x0) / (x1 - x0) if x1 != x0 else 0)

def ripple(x, ph, amp, wl):
    env = 0.55 + 0.45 * math.sin(math.pi * min(max(x / W, 0), 1))   # strongest mid-width
    return amp * env * (math.sin(2 * math.pi * x / wl - ph) + 0.35 * math.sin(2 * math.pi * x / (wl * 0.53) - 1.7 * ph))

def cr(pts):
    out = []
    for i in range(len(pts) - 1):
        p0 = pts[max(i - 1, 0)]; p1 = pts[i]; p2 = pts[i + 1]; p3 = pts[min(i + 2, len(pts) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        out.append('C%.1f %.1f %.1f %.1f %.1f %.1f' % (c1 + c2 + p2))
    return ' '.join(out)

def layer(ph, off, amp, wl, lag):
    xs = [-30 + (W + 60) * i / N for i in range(N + 1)]
    pts = [(x, base(x) + off + ripple(x, ph + lag, amp, wl)) for x in xs]
    return 'M%.1f %.1f ' % pts[0] + cr(pts) + ' L%d %d L-30 %d Z' % (W + 30, H + 20, H + 20)

LAYERS = [  # (offset px, ripple amp, wavelength, phase lag, fill)
    (-12, 21, 540, 0.0, 'url(#awA)'),    # light gold, top
    (14, 19, 540, 0.45, 'url(#awB)'),    # deep gold
    (40, 17, 540, 0.9, 'NEXT'),          # colour of the next section
]

def svg(next_color, animated=True):
    p = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" preserveAspectRatio="none">' % (W, H),
         '<defs><linearGradient id="awA" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#F6D365"/>'
         '<stop offset=".5" stop-color="#F8DC7E"/><stop offset="1" stop-color="#F2B91E"/></linearGradient>'
         '<linearGradient id="awB" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#E3A015"/>'
         '<stop offset=".45" stop-color="#F2B91E"/><stop offset="1" stop-color="#E3A015"/></linearGradient></defs>']
    for off, amp, wl, lag, fill in LAYERS:
        fill = next_color if fill == 'NEXT' else fill
        fn = lambda ph: layer(ph, off, amp, wl, lag)
        if animated:
            frames = [fn(2 * math.pi * k / K) for k in range(K)] + [fn(0)]
            p.append('<path fill="%s" d="%s"><animate attributeName="d" dur="%ss" repeatCount="indefinite" values="%s"/></path>'
                     % (fill, frames[0], DUR, ';'.join(frames)))
        else:
            p.append('<path fill="%s" d="%s"/>' % (fill, fn(0)))
    p.append('</svg>')
    return ''.join(p)

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else '.'
    for nm, col in (('light', '#F4F6FB'), ('white', '#FFFFFF')):
        open('%s/arfa_swoosh_%s.svg' % (out, nm), 'w').write(svg(col))
        open('%s/arfa_swoosh_%s_static.svg' % (out, nm), 'w').write(svg(col, animated=False))
