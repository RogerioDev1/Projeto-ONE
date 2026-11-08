# Gera o vídeo "Quanto custa a política brasileira" (motion graphics 3D, vertical 1080x1920)
# Uso: python3 gerar_video.py   -> saida: custo_politica_brasil.mp4
import math, os, sys, subprocess, wave, struct, random
from multiprocessing import Pool
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
OUT = os.path.dirname(os.path.abspath(__file__))
FRAMES = os.path.join(OUT, "_frames")
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_fc = {}
def F(s, b=True):
    k = (s, b)
    if k not in _fc: _fc[k] = ImageFont.truetype(FB if b else FR, s)
    return _fc[k]

GOLD=(255,196,40); GREEN=(0,200,110); BLUE=(40,120,255); RED=(255,70,70); WHITE=(245,245,250); GREY=(160,165,185)

# ---------------- dados (valores aproximados / estimativas) ----------------
CARGOS = [
 # nome, quantidade, texto qtd, custo anual (bi), texto custo, linhas extras, cor
 ("PRESIDENTE", 1, "1 + vice", 1.0, "≈ R$ 1 bi/ano",
  ["Salário: R$ 46,4 mil/mês", "Presidência: palácios, avião,", "segurança, assessores"], GREEN),
 ("GOVERNADORES", 27, "27 + vices", 2.0, "≈ R$ 2 bi/ano",
  ["Gabinetes e palácios", "dos 26 estados + DF", "Salário: até R$ 41 mil"], BLUE),
 ("SENADORES", 81, "81 (3 por estado)", 6.5, "≈ R$ 6,5 bi/ano",
  ["≈ R$ 80 milhões por senador", "Mandato de 8 anos", "Salário: R$ 46,4 mil/mês"], GOLD),
 ("DEPUTADOS FEDERAIS", 513, "513", 8.0, "≈ R$ 8 bi/ano",
  ["≈ R$ 15 milhões por deputado", "Cota + até 25 assessores", "Salário: R$ 46,4 mil/mês"], GREEN),
 ("DEPUTADOS ESTADUAIS", 1059, "1.059", 20.0, "≈ R$ 20 bi/ano",
  ["27 Assembleias Legislativas", "≈ R$ 19 milhões por deputado", "Salário: até R$ 34,8 mil"], BLUE),
 ("PREFEITOS", 5569, "5.569 + vices", 5.0, "≈ R$ 5 bi/ano",
  ["Um em cada município", "Salários + gabinetes", "Mandato de 4 anos"], GOLD),
 ("VEREADORES", 58000, "≈ 58 mil", 25.0, "≈ R$ 25 bi/ano",
  ["5.569 Câmaras Municipais", "O maior número de políticos", "Salário: até R$ 26 mil"], RED),
]
EXTRAS = [("Fundo Eleitoral", "R$ 4,9 bi por eleição"), ("Fundo Partidário", "≈ R$ 1,2 bi/ano"),
          ("Emendas Parlamentares", "≈ R$ 50 bi/ano")]
TOTAL_BARS = [("Vereadores",25),("Dep. Estaduais",20),("Dep. Federais",8),("Senado",6.5),
              ("Prefeitos",5),("Governos",2),("Fundos",3.7),("Presidência",1),("Emendas",50)]

# ---------------- utilidades ----------------
def clamp(x,a=0,b=1): return max(a,min(b,x))
def ease(t): t=clamp(t); return t*t*(3-2*t)
def eout(t): t=clamp(t); return 1-(1-t)**3
def back(t):
    t=clamp(t); c=1.70158; return 1+(c+1)*(t-1)**3+c*(t-1)**2
def mix(c1,c2,t): return tuple(int(a+(b-a)*t) for a,b in zip(c1,c2))
def shade(c,k): return tuple(int(clamp(v*k,0,255)) for v in c)

def text_c(d, y, s, size, col=WHITE, alpha=1.0, bold=True, x=W//2, glow=False):
    f = F(size, bold); bb = d.textbbox((0,0), s, font=f)
    tw = bb[2]-bb[0]; px = x - tw//2
    a = int(255*clamp(alpha))
    if a <= 0: return
    d.text((px+4, y+5), s, font=f, fill=(0,0,0,int(a*0.6)))
    d.text((px, y), s, font=f, fill=col+(a,))

def fit(s, maxw, size):
    while size > 20 and F(size).getlength(s) > maxw: size -= 2
    return size

# ---------------- mini motor 3D ----------------
class Cam:
    def __init__(s, yaw, pitch, dist, cx=W/2, cy=H/2, f=1300):
        s.yaw, s.pitch, s.dist, s.cx, s.cy, s.f = yaw, pitch, dist, cx, cy, f
    def tr(s, p):
        x,y,z = p
        cy_, sy = math.cos(s.yaw), math.sin(s.yaw)
        x, z = x*cy_ - z*sy, x*sy + z*cy_
        cp, sp = math.cos(s.pitch), math.sin(s.pitch)
        y, z = y*cp - z*sp, y*sp + z*cp
        return (x, y, z + s.dist)
    def pr(s, q):
        x,y,z = q; z = max(z, 1)
        k = s.f/z; return (s.cx + x*k, s.cy - y*k)

def box_faces(cam, x, y, z, w, h, dd, col):
    # retorna lista de (profundidade, poligono, cor)
    v = [(x+dx*w, y+dy*h, z+dz*dd) for dx in (0,1) for dy in (0,1) for dz in (0,1)]
    idx = lambda dx,dy,dz: dx*4+dy*2+dz
    faces = [((0,0,0),(1,0,0),(1,1,0),(0,1,0), (0,0,-1), 0.75),
             ((0,0,1),(1,0,1),(1,1,1),(0,1,1), (0,0,1), 0.55),
             ((0,0,0),(0,0,1),(0,1,1),(0,1,0), (-1,0,0), 0.6),
             ((1,0,0),(1,0,1),(1,1,1),(1,1,0), (1,0,0), 0.9),
             ((0,1,0),(1,1,0),(1,1,1),(0,1,1), (0,1,0), 1.15)]
    T = [cam.tr(p) for p in v]
    out = []
    for *corners, n, k in faces:
        pts = [T[idx(*c)] for c in corners]
        # back-face: normal transformada vs vetor da camera
        a,b,c = pts[0],pts[1],pts[2]
        u=(b[0]-a[0],b[1]-a[1],b[2]-a[2]); w2=(c[0]-a[0],c[1]-a[1],c[2]-a[2])
        nx=(u[1]*w2[2]-u[2]*w2[1], u[2]*w2[0]-u[0]*w2[2], u[0]*w2[1]-u[1]*w2[0])
        cen=[sum(p[i] for p in pts)/4 for i in range(3)]
        if nx[0]*cen[0]+nx[1]*cen[1]+nx[2]*cen[2] >= 0:
            # tenta orientação oposta
            pass
        dot = nx[0]*cen[0]+nx[1]*cen[1]+nx[2]*cen[2]
        out.append((cen[2], [cam.pr(p) for p in pts], shade(col,k), dot))
    return out

def draw_faces(d, faces, alpha=255):
    faces.sort(key=lambda f: -f[0])
    for z, poly, col, _ in faces:
        d.polygon(poly, fill=col+(alpha,), outline=shade(col,1.3)+(alpha,))

# ---------------- fundo ----------------
random.seed(7)
STARS = [(random.uniform(-1,1), random.uniform(-1,1), random.uniform(0.2,1)) for _ in range(140)]
def background(t, tint=(10,14,40)):
    img = Image.new("RGB", (W,H), tint)
    d = ImageDraw.Draw(img, "RGBA")
    for i in range(0, H, 16):  # gradiente vertical
        k = i/H; d.rectangle([0,i,W,i+16], fill=mix((6,8,22), tint, 1-abs(k-0.55)*1.4))
    # chão em grade 3D (perspectiva)
    cam = Cam(0.0, 0.15, 900, cy=H*0.5)
    off = (t*40) % 100
    for gx in range(-1500, 1501, 100):
        a = cam.pr(cam.tr((gx, -300, -200))); b = cam.pr(cam.tr((gx, -300, 3000)))
        d.line([a,b], fill=(60,90,200,45), width=2)
    for gz in range(-200, 3000, 100):
        z = gz - off
        a = cam.pr(cam.tr((-1500,-300,z))); b = cam.pr(cam.tr((1500,-300,z)))
        d.line([a,b], fill=(60,90,200,max(0,55-int(gz/60))), width=2)
    # partículas lentas (poeira dourada)
    for sx, sy, sz in STARS:
        px = (sx*W*0.6 + W/2 + math.sin(t*0.3+sy*9)*30) % W
        py = (sy*H*0.5 + H/2 - t*25*sz) % H
        r = 2+sz*3; d.ellipse([px-r,py-r,px+r,py+r], fill=(255,210,90,int(70*sz)))
    return img, d

def money_rain(d, t, n=26, seed=1):
    rnd = random.Random(seed)
    for i in range(n):
        x0 = rnd.uniform(0, W); sp = rnd.uniform(80,160); ph = rnd.uniform(0, H)
        y = (ph + t*sp) % (H+200) - 100; ang = t*rnd.uniform(0.5,1.5)+i
        w, h = 120*abs(math.cos(ang))+10, 60
        x = x0 + math.sin(t+i)*40
        d.rectangle([x-w/2,y-h/2,x+w/2,y+h/2], fill=(40,170,90,150), outline=(150,255,180,170), width=2)
        if w > 50: d.text((x-14,y-18), "R$", font=F(26), fill=(220,255,230,170))

def cta(d, t, y, alpha=1.0):
    # botões de SEGUIR e LIKE pulsando
    p = 1 + 0.06*math.sin(t*6)
    a = int(255*clamp(alpha))
    if a <= 0: return
    for i,(label,col) in enumerate([("👍  CURTE", BLUE), ("➕  SEGUE", RED)]):
        cx = W/2 + (i*2-1)*235; bw, bh = 210*p, 62*p
        d.rounded_rectangle([cx-bw,y-bh,cx+bw,y+bh], radius=40, fill=col+(a,), outline=(255,255,255,a), width=4)
        s = label.split("  ")[1]
        f = F(int(54*p)); tw = f.getlength(s)
        d.text((cx-tw/2, y-34*p), s, font=f, fill=(255,255,255,a))

# ---------------- cenas ----------------
def scene_intro(t, dur):
    img, d = background(t, (30,10,40))
    money_rain(d, t*0.5)
    # pilha de "cédulas" 3D girando em câmera lenta
    cam = Cam(t*0.25, 0.42, 1400, cy=H*0.62)
    faces=[]; n = int(18*eout(t/4))
    for i in range(n):
        faces += box_faces(cam, -220+math.sin(i)*15, -260+i*26, -120+math.cos(i)*15, 440, 22, 240, (30,160,80) if i%2 else (40,185,95))
    draw_faces(d, faces)
    a = ease(t/1.2)
    text_c(d, 230, "QUANTO CUSTA", fit("QUANTO CUSTA",980,110), WHITE, a)
    text_c(d, 360, "A POLÍTICA", 120, GOLD, ease((t-0.4)/1.2))
    text_c(d, 500, "BRASILEIRA?", 120, GOLD, ease((t-0.8)/1.2))
    text_c(d, 690, "Cada cargo. Cada real. Por ano.", 46, GREY, ease((t-2)/1))
    cta(d, t, 1700, ease((t-3)/1))
    text_c(d, 1590, "Segue e curte pra ver até o final!", 42, WHITE, ease((t-3)/1))
    return img

def scene_eleicoes(t, dur):
    img, d = background(t, (12,20,50))
    text_c(d, 200, "O BRASIL VOTA", 96, WHITE, ease(t/1))
    text_c(d, 320, "A CADA 2 ANOS", 96, GOLD, ease((t-0.5)/1))
    # urnas 3D girando
    cam = Cam(math.sin(t*0.4)*0.5, 0.3, 1600, cy=H*0.52)
    for j,(ano,lab,col) in enumerate([("2026","GERAL",BLUE),("2028","MUNICIPAL",GREEN)]):
        ap = eout((t-1-j*1.2)/1.2)
        if ap <= 0: continue
        faces = box_faces(cam, -520+j*620, -250, 0, 420, 330*ap, 300, col)
        draw_faces(d, faces)
    y0 = 1230
    text_c(d, y0, "2026 → Presidente, Governadores,", 44, WHITE, ease((t-2)/1))
    text_c(d, y0+60, "Senadores e Deputados", 44, WHITE, ease((t-2)/1))
    text_c(d, y0+160, "2028 → Prefeitos e Vereadores", 44, WHITE, ease((t-3.2)/1))
    text_c(d, y0+300, "Ao todo: ≈ 65 MIL", 70, GOLD, ease((t-4.5)/1))
    text_c(d, y0+390, "políticos eleitos", 50, GREY, ease((t-4.5)/1))
    return img

def counter(val, t):
    v = int(val*eout(t))
    return f"{v:,}".replace(",", ".")

def scene_cargo(i):
    nome, qtd, qtxt, custo, ctxt, linhas, col = CARGOS[i]
    def sc(t, dur):
        img, d = background(t, mix((10,14,40), col, 0.18))
        # número da cena
        text_c(d, 120, f"{i+1}/7", 40, GREY, ease(t/0.6))
        s = fit(nome, 1000, 100)
        text_c(d, 180, nome, s, col, ease(t/0.8))
        # torre 3D de blocos de dinheiro (altura ~ custo), giro lento = slow motion
        cam = Cam(0.6 + t*0.18, 0.38, 1500, cy=H*0.47)
        nb = max(2, int(2 + custo*1.1)); nb = min(nb, 30)
        shown = nb*eout((t-0.6)/3.2)
        faces = []
        for b in range(int(shown)+1):
            frac = clamp(shown-b)
            if frac <= 0: break
            yb = -330 + b*24 + (1-frac)*260  # bloco "cai" suavemente
            faces += box_faces(cam, -200, yb, -130, 400, 20, 260, col if b%2 else shade(col,0.85))
        draw_faces(d, faces)
        # quantidade
        text_c(d, 360, "ELEITOS:", 44, GREY, ease((t-0.5)/0.8))
        if qtd > 100:
            num = counter(qtd, (t-0.6)/2.5)
            if qtd == 58000: num = "≈ " + num
        else:
            num = qtxt
        text_c(d, 420, num if qtd>100 else qtxt, 120, WHITE, ease((t-0.6)/0.8))
        # custo
        text_c(d, 1430, "CUSTO ANUAL ESTIMADO", 42, GREY, ease((t-2.5)/0.8))
        text_c(d, 1490, ctxt, fit(ctxt, 1000, 96), GOLD, ease((t-2.8)/0.8))
        for k, ln in enumerate(linhas):
            text_c(d, 1620+k*58, ln, 42, WHITE, ease((t-4-k*0.5)/0.8))
        if i == 3:
            text_c(d, 1820, "Comenta: você acha justo?", 38, GREY, ease((t-6)/0.8))
        return img
    return sc

def scene_extras(t, dur):
    img, d = background(t, (40,12,12))
    money_rain(d, t, 30, 3)
    text_c(d, 200, "E NÃO PARA AÍ...", 92, RED, ease(t/0.8))
    cam = Cam(t*0.2, 0.4, 1500, cy=H*0.5)
    for j,(nm, val) in enumerate(EXTRAS):
        a = ease((t-1-j*1.5)/1)
        if a <= 0: continue
        y = 520 + j*340
        d.rounded_rectangle([90, y, W-90, y+270], radius=34, fill=(20,20,35,int(220*a)), outline=GOLD+(int(255*a),), width=4)
        text_c(d, y+45, nm, fit(nm, 850, 64), WHITE, a)
        text_c(d, y+145, val, fit(val, 850, 70), GOLD, a)
    text_c(d, 1600, "Dinheiro público para", 48, WHITE, ease((t-6)/1))
    text_c(d, 1665, "campanhas e partidos", 48, WHITE, ease((t-6)/1))
    return img

def scene_total(t, dur):
    img, d = background(t, (8,10,30))
    text_c(d, 150, "QUANTO DÁ NO TOTAL?", fit("QUANTO DÁ NO TOTAL?", 1000, 84), WHITE, ease(t/0.8))
    cam = Cam(-0.35 + t*0.08, 0.35, 3300, cy=H*0.62, f=1350)
    faces = []
    mx = max(v for _,v in TOTAL_BARS)
    n = len(TOTAL_BARS)
    for j,(nm,v) in enumerate(TOTAL_BARS):
        g = eout((t-0.5-j*0.35)/1.6)
        hh = 1300*v/mx*g
        col = [RED,BLUE,GREEN,GOLD,GOLD,BLUE,GREY,GREEN,RED][j]
        faces += box_faces(cam, -850+j*190, -500, -60, 140, max(hh,2), 140, col)
    draw_faces(d, faces)
    # rótulos simples na base
    for j,(nm,v) in enumerate(TOTAL_BARS):
        a = ease((t-0.8-j*0.35)/1)
        p = cam.pr(cam.tr((-850+j*190+70, -500+1300*v/mx*eout((t-0.5-j*0.35)/1.6)+30, 10)))
        lbl = (f"{v:g}".replace(".",",")) + " bi"
        f = F(32); tw = f.getlength(lbl)
        if a>0: d.text((p[0]-tw/2, p[1]-40), lbl, font=f, fill=WHITE+(int(255*a),))
    tot = 120*eout((t-4)/3)
    text_c(d, 1450, "TOTAL ESTIMADO", 50, GREY, ease((t-4)/0.8))
    text_c(d, 1520, f"≈ R$ {int(tot)} BILHÕES", fit("≈ R$ 120 BILHÕES", 1000, 104), GOLD, ease((t-4)/0.8))
    text_c(d, 1660, "POR ANO", 70, WHITE, ease((t-5)/0.8))
    return img

def scene_final(t, dur):
    img, d = background(t, (30,10,40))
    money_rain(d, t*0.7, 20, 9)
    text_c(d, 220, "Isso dá cerca de", 56, WHITE, ease(t/0.8))
    text_c(d, 310, "R$ 560", 190, GOLD, ease((t-0.5)/0.8))
    text_c(d, 540, "por brasileiro, por ano", 56, WHITE, ease((t-0.8)/0.8))
    text_c(d, 640, "≈ R$ 330 milhões por DIA", 50, RED, ease((t-2)/0.8))
    text_c(d, 760, "Ou R$ 14 milhões por HORA.", 50, RED, ease((t-3)/0.8))
    # cubo grande girando
    cam = Cam(t*0.5, 0.5+0.1*math.sin(t), 1500, cy=H*0.6)
    draw_faces(d, box_faces(cam, -150, -150, -150, 300, 300, 300, GOLD))
    text_c(d, 1060, "R$", 90, (60,40,0), ease((t-1)/0.8))
    text_c(d, 1390, "Agora você sabe.", 62, WHITE, ease((t-4)/0.8))
    text_c(d, 1480, "Manda esse vídeo pra quem precisa ver!", 40, GREY, ease((t-4.5)/0.8))
    cta(d, t, 1680, ease((t-5)/0.8))
    text_c(d, 1820, "Valores aproximados: orçamentos públicos 2024-2025", 28, GREY, ease((t-1)/1))
    return img

SCENES = [(scene_intro, 8), (scene_eleicoes, 9)] + [(scene_cargo(i), 9) for i in range(7)] + \
         [(scene_extras, 9), (scene_total, 11), (scene_final, 11)]
TOTAL = sum(s for _, s in SCENES)
FADE = 0.5

def render(fi):
    t = fi/FPS; acc = 0
    for fn, dur in SCENES:
        if t < acc+dur: break
        acc += dur
    lt = t-acc
    img = fn(lt, dur)
    # fade preto entre cenas
    k = min(clamp(lt/FADE), clamp((dur-lt)/FADE))
    if k < 1: img = Image.blend(Image.new("RGB",(W,H)), img, k)
    # barra de progresso
    dd = ImageDraw.Draw(img)
    dd.rectangle([0, H-10, int(W*t/TOTAL), H], fill=GOLD)
    img.save(os.path.join(FRAMES, f"{fi:05d}.jpg"), quality=90)

def audio(path):
    # trilha ambiente sintetizada (pad grave + pulso lento)
    sr = 44100; n = int(TOTAL*sr)
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        notes = [55, 65.41, 49, 58.27]
        buf = bytearray()
        for i in range(n):
            t = i/sr; f = notes[int(t/8) % 4]
            env = min(1, t/3, (TOTAL-t)/3)
            puls = 0.6+0.4*math.sin(2*math.pi*t*1.0)**8
            s = (math.sin(2*math.pi*f*t)*0.5 + math.sin(2*math.pi*f*2.005*t)*0.25 + math.sin(2*math.pi*f*3*t)*0.08)*puls
            buf += struct.pack("<h", int(clamp(s*env*0.35,-1,1)*32767))
        w.writeframes(bytes(buf))

if __name__ == "__main__":
    os.makedirs(FRAMES, exist_ok=True)
    nf = int(TOTAL*FPS)
    print("duracao", TOTAL, "s, frames", nf)
    with Pool(os.cpu_count()) as p:
        for k,_ in enumerate(p.imap_unordered(render, range(nf), chunksize=20)):
            if k % 300 == 0: print(k, flush=True)
    wav = os.path.join(FRAMES, "trilha.wav"); audio(wav)
    out = os.path.join(OUT, "custo_politica_brasil.mp4")
    subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate",str(FPS),"-i",os.path.join(FRAMES,"%05d.jpg"),
                    "-i",wav,"-c:v","libx264","-pix_fmt","yuv420p","-crf","20","-preset","medium",
                    "-c:a","aac","-b:a","160k","-shortest","-movflags","+faststart",out], check=True)
    print("ok", out)
