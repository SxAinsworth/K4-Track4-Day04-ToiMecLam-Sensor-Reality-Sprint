"""Tiny PIL plotting helpers (matplotlib is blocked by Application Control on the lab machine)."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont

COLORS = ["#2a6fdb", "#e8553d", "#20a37c", "#9b59b6", "#e0a100", "#111111", "#888888"]


def font(size):
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def line_panel(draw, box, xs, series, title, xlabel, ylabel, ylim=(0, 1.0), xticklabels=None,
               legend=True):
    """series: list of (name, ys, color). box = (x0, y0, x1, y1) in pixels."""
    x0, y0, x1, y1 = box
    L, R, T, B = x0 + 70, x1 - 15, y0 + 40, y1 - 55
    f, fs = font(16), font(13)
    draw.text(((x0 + x1) / 2, y0 + 8), title, fill="black", font=font(18), anchor="mt")
    sx = lambda x: L + (x - xs[0]) / (xs[-1] - xs[0]) * (R - L)
    sy = lambda y: B - (y - ylim[0]) / (ylim[1] - ylim[0]) * (B - T)
    for yt in np.linspace(ylim[0], ylim[1], 6):
        draw.line([(L, sy(yt)), (R, sy(yt))], fill="#e5e5e5")
        draw.text((L - 6, sy(yt)), f"{yt:.2f}", fill="#333", font=fs, anchor="rm")
    for k, x in enumerate(xs):
        lab = xticklabels[k] if xticklabels else str(x)
        draw.text((sx(x), B + 6), lab, fill="#333", font=fs, anchor="mt")
    draw.rectangle([L, T, R, B], outline="#444")
    draw.text(((L + R) / 2, B + 30), xlabel, fill="black", font=f, anchor="mt")
    yl = Image.new("RGBA", (B - T, 22), (255, 255, 255, 0))
    ImageDraw.Draw(yl).text(((B - T) / 2, 2), ylabel, fill="black", font=f, anchor="mt")
    draw._image.paste(yl.rotate(90, expand=True), (x0 + 4, T), yl.rotate(90, expand=True))
    for name, ys, col in series:
        pts = [(sx(x), sy(y)) for x, y in zip(xs, ys)]
        draw.line(pts, fill=col, width=3)
        for p in pts:
            draw.ellipse([p[0] - 4, p[1] - 4, p[0] + 4, p[1] + 4], fill=col)
    if legend:
        ly = T + 8
        for name, _, col in series:
            draw.rectangle([R - 175, ly + 3, R - 163, ly + 15], fill=col)
            draw.text((R - 157, ly), name, fill="black", font=fs)
            ly += 20


def bev_panel(img, box, pc, objs, gt_ids, hit, title, extent=45):
    """Bird's-eye view: points coloured by height, GT boxes green (detected) / red (missed)."""
    draw = ImageDraw.Draw(img)
    x0, y0, x1, y1 = box
    T = y0 + 30
    size = min(x1 - x0, y1 - T) - 10
    cx, cy = (x0 + x1) / 2, T + size / 2
    s = size / (2 * extent)
    draw.rectangle([cx - size / 2, T, cx + size / 2, T + size], fill="#0d1117")
    draw.text(((x0 + x1) / 2, y0 + 6), title, fill="black", font=font(17), anchor="mt")
    xyz = pc["xyz"]
    m = (np.abs(xyz[:, 0]) < extent) & (np.abs(xyz[:, 1]) < extent)
    px, py = cx - xyz[m, 1] * s, cy - xyz[m, 0] * s          # x forward = up
    z = np.clip((xyz[m, 2] + 1.8) / 2.5, 0, 1)
    ghost = pc["label"][m] == -3
    for X, Y, Z, gh in zip(px, py, z, ghost):
        col = (255, 0, 255) if gh else (int(60 + 195 * Z), int(140 + 100 * Z), int(255 - 120 * Z))
        draw.point((X, Y), fill=col)
    for i in gt_ids:
        o = objs[i]
        if abs(o["cx"]) > extent or abs(o["cy"]) > extent:
            continue
        c, sn = np.cos(o["yaw"]), np.sin(o["yaw"])
        corners = [(o["cx"] + a * c - b * sn, o["cy"] + a * sn + b * c)
                   for a, b in [(-o["l"] / 2, -o["w"] / 2), (o["l"] / 2, -o["w"] / 2),
                                (o["l"] / 2, o["w"] / 2), (-o["l"] / 2, o["w"] / 2)]]
        poly = [(cx - y * s, cy - x * s) for x, y in corners]
        draw.polygon(poly, outline="#33dd55" if i in hit else "#ff3333", width=2)
    draw.polygon([(cx, cy - 6), (cx - 4, cy + 4), (cx + 4, cy + 4)], fill="white")
    d = len(gt_ids)
    draw.text((cx - size / 2 + 6, T + size - 22), f"pts={len(xyz)}  recall={len(hit)}/{d}",
              fill="white", font=font(14))
