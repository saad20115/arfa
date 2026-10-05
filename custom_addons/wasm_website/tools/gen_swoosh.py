import math, sys
W, H = 1440, 200
N = 28            # segments per edge
K = 6             # animation keyframes
DUR = 7           # seconds per undulation loop

def bez(p0, p1, p2, p3, t):
    u = 1 - t
    return (u**3*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t**3*p3[0],
            u**3*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t**3*p3[1])

# Logo-like sweep: low on the left, a soft sag, then a long rise to the right.
SEG = [((0, 128), (230, 182), (580, 184), (910, 130)),
       ((910, 130), (1160, 92), (1330, 58), (1440, 38))]
_tab = []
for s in SEG:
    for i in range(400):
        _tab.append(bez(*s, i / 400))
_tab.append(SEG[-1][3])

def base(x):
    lo, hi = 0, len(_tab) - 1
    while hi - lo > 1:
        m = (lo + hi) // 2
        if _tab[m][0] <= x: lo = m
        else: hi = m
    (x0, y0), (x1, y1) = _tab[lo], _tab[hi]
    return y0 + (y1 - y0) * ((x - x0) / (x1 - x0) if x1 != x0 else 0)

def wave(x, ph, amp):
    t = x / W
    return amp * (0.45 + 0.55 * t) * math.sin(2 * math.pi * x / 760 - ph)

def cr(points):
    """Catmull-Rom -> cubic bezier path string (no M)."""
    out = []
    for i in range(len(points) - 1):
        p0 = points[max(i - 1, 0)]; p1 = points[i]; p2 = points[i + 1]; p3 = points[min(i + 2, len(points) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        out.append('C%.1f %.1f %.1f %.1f %.1f %.1f' % (c1 + c2 + p2))
    return ' '.join(out)

def xs(x0, x1):
    return [x0 + (x1 - x0) * i / N for i in range(N + 1)]

def fill_path(ph, off=0, amp=7):
    pts = [(x, base(x) + off + wave(x, ph, amp)) for x in xs(-20, W + 20)]
    return 'M%.1f %.1f ' % pts[0] + cr(pts) + ' L%d %d L-20 %d Z' % (W + 20, H + 10, H + 10)

def ribbon_path(ph, lift, thick, x0, x1, amp=7, lag=0.0):
    """Tapered blade: bottom edge follows the sweep `lift` px above it, top edge = bottom - thickness."""
    X = xs(x0, x1)
    bot = [(x, base(x) - lift + wave(x, ph + lag, amp)) for x in X]
    top = [(x, y - thick((x - x0) / (x1 - x0))) for x, y in bot]
    top = top[::-1]
    return 'M%.1f %.1f ' % bot[0] + cr(bot) + ' L%.1f %.1f ' % top[0] + cr(top) + ' Z'

# thickness profiles (t = 0 at the left end, 1 at the right tip)
main_th = lambda t: 36 * (1 - t) ** 1.25 * (0.42 + 1.9 * t) + 0.0
echo_th = lambda t: 11 * math.sin(math.pi * t) ** 1.3
ghost_th = lambda t: 6 * math.sin(math.pi * t) ** 1.6

def anim(fn):
    frames = [fn(2 * math.pi * k / K) for k in range(K)] + [fn(0)]
    return frames

def svg(next_color, animated=True):
    layers = [
        ('ghost', lambda ph: ribbon_path(ph, 78, ghost_th, 280, W - 90, amp=9, lag=1.2), '#B98A2E', ''),
        ('echo',  lambda ph: ribbon_path(ph, 46, echo_th, 90, W - 40, amp=8, lag=0.6), 'url(#asG)', 'opacity=".9"'),
        ('main',  lambda ph: ribbon_path(ph, 9, main_th, -30, W - 4), 'url(#asG)', ''),
        ('shine', lambda ph: ribbon_path(ph, 9, main_th, -30, W - 4), 'url(#asS)', ''),
        ('fill',  lambda ph: fill_path(ph), next_color, ''),
    ]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" preserveAspectRatio="none">' % (W, H),
             '<defs>'
             '<linearGradient id="asG" x1="0" y1="0" x2="1" y2="0">'
             '<stop offset="0" stop-color="#E3A015"/><stop offset=".35" stop-color="#F2B91E"/>'
             '<stop offset=".75" stop-color="#F6D365"/><stop offset="1" stop-color="#F2B91E"/></linearGradient>'
             '<linearGradient id="asS" gradientUnits="userSpaceOnUse" x1="-400" y1="0" x2="0" y2="0">'
             '<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#FFF6D6" stop-opacity=".85"/>'
             '<stop offset="1" stop-color="#fff" stop-opacity="0"/>'
             + ('<animateTransform attributeName="gradientTransform" type="translate" values="0 0;%d 0" dur="3.6s" repeatCount="indefinite"/>' % (W + 500) if animated else '')
             + '</linearGradient></defs>']
    for name, fn, fill, extra in layers:
        if name == 'shine' and not animated:
            continue
        d0 = fn(0)
        if animated:
            frames = anim(fn)
            ks = ';'.join(['.45 0 .55 1'] * (len(frames) - 1))
            parts.append('<path fill="%s" %s d="%s"><animate attributeName="d" dur="%ds" repeatCount="indefinite" calcMode="spline" keySplines="%s" values="%s"/></path>'
                         % (fill, extra, d0, DUR, ks, ';'.join(frames)))
        else:
            parts.append('<path fill="%s" %s d="%s"/>' % (fill, extra, d0))
    parts.append('</svg>')
    return ''.join(parts)

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else '.'
    for nm, col in (('light', '#F4F6FB'), ('white', '#FFFFFF')):
        open('%s/arfa_swoosh_%s.svg' % (out, nm), 'w').write(svg(col))
        open('%s/arfa_swoosh_%s_static.svg' % (out, nm), 'w').write(svg(col, animated=False))
