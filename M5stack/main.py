from m5stack import *
from m5stack_ui import *
from uiflow import *
from MediaTrans.MicRecord import MicRecord
from m5stack import speaker

import network
import wifiCfg
import unit
import urequests
import usocket
import ussl
import time
import ntptime
import json
import os
import gc

# ╔══════════════════════════════════════════════════════╗
# ║                    WIFI AUTO                         ║
# ╚══════════════════════════════════════════════════════╝
from m5stack import btnA
time.sleep_ms(1500)
if btnA.isPressed():
    raise SystemExit   # maintenir A au boot = rester dans UIFlow

wifiCfg.doConnect('Zakaria', '12345678')
_wlan = network.WLAN(network.STA_IF)
for _ in range(20):
    if _wlan.isconnected():
        break
    time.sleep_ms(500)

# ╔══════════════════════════════════════════════════════╗
# ║                    CONFIGURATION                     ║
# ╚══════════════════════════════════════════════════════╝
OW_API_KEY    = '225b371ea357af5179adf9b196eb4be6'
LAT           = '46.2044'
LON           = '6.1432'

# Cloud Run — données capteurs
CLOUD_HOST    = 'weather-service-622761578105.europe-west6.run.app'
CLOUD_PORT    = 443
CLOUD_API_KEY = 'weather123'

# Cloud Run — voice pipeline
VOICE_HOST    = 'weather-voice-622761578105.europe-west6.run.app'
ASK_HOST      = 'weather-ask-622761578105.europe-west6.run.app'
RESP_HOST     = 'weather-resp-622761578105.europe-west6.run.app'

VOICE_FILE      = '/flash/voice.wav'
RESP_FILE_FLASH = '/flash/res/resp.wav'
RECORD_SECONDS  = 3

ROOMS = ['Salon', 'Chambre', 'Cuisine', 'Bureau']

FREQ_OPTS = [
    ('30s',  30000),
    ('1min', 60000),
    ('5min', 300000),
    ('10m',  600000),
    ('30m',  1800000),
    ('1h',   3600000),
]

freq_indoor_idx  = 0
freq_weather_idx = 2
freq_fetch_idx   = 2

# ╔══════════════════════════════════════════════════════╗
# ║                     PALETTE                          ║
# ╚══════════════════════════════════════════════════════╝
C_BG     = 0x0A1628
C_ACCENT = 0x00BCD4
C_HI     = 0x26C6DA
C_PRI    = 0xCFD8DC
C_MUT    = 0x546E7A
C_OK     = 0x00E676
C_WARN   = 0xFFCA28
C_ERR    = 0xFF5252
C_SEP    = 0x1A3248

# ╔══════════════════════════════════════════════════════╗
# ║                      STATE                           ║
# ╚══════════════════════════════════════════════════════╝
PAGE_HOME     = 0
PAGE_INDOOR   = 1
PAGE_FORECAST = 2
PAGE_CLOUD    = 3
PAGE_SETTINGS = 4
PAGE_VOICE    = 5
TOTAL_PAGES   = 6

current_page = PAGE_HOME
prev_page    = PAGE_HOME
room_idx     = 0
settings_sel = 0

wifi_ok         = False
cloud_status    = 'En attente'
last_cloud_send = '--:--:--'
last_api_time   = '--:--:--'
time_valid      = False

outdoor_temp = '--'
weather_main = '--'
weather_desc = '--'
forecast_1 = forecast_2 = forecast_3 = '--'

indoor_temp = indoor_hum = tvoc_val = eco2_val = '--'
motion_on = False

t_clock = t_iread = t_wifi = t_wfetch = t_isend = t_wsend = t_ntp = 0

# Spinner voice
SPIN_FRAMES = ['|', '/', '-', '\\']
_spin_i = 0

# ╔══════════════════════════════════════════════════════╗
# ║                    SCREEN SETUP                      ║
# ╚══════════════════════════════════════════════════════╝
screen = M5Screen()
screen.clean_screen()
screen.set_screen_bg_color(C_BG)

# ── HEADER (permanent) ───────────────────────────────
h_room = M5Label('Salon',    x=8,   y=4,  color=C_ACCENT, font=FONT_MONT_14)
h_time = M5Label('--:--:--', x=100, y=4,  color=C_PRI,    font=FONT_MONT_14)
h_dot  = M5Label('●',        x=301, y=4,  color=C_MUT,    font=FONT_MONT_14)
h_sep  = M5Label('________________________________', x=0, y=22, color=C_SEP, font=FONT_MONT_10)

# ── FOOTER (permanent) ───────────────────────────────
f_sep  = M5Label('________________________________', x=0,   y=202, color=C_SEP,    font=FONT_MONT_10)
btn_a  = M5Label('',  x=8,   y=212, color=C_MUT,    font=FONT_MONT_10)
btn_b  = M5Label('',  x=122, y=212, color=C_ACCENT, font=FONT_MONT_10)
btn_c  = M5Label('',  x=255, y=212, color=C_MUT,    font=FONT_MONT_10)
f_dots = M5Label('',  x=115, y=228, color=C_MUT,    font=FONT_MONT_10)

# ── PAGE 0 — HOME ────────────────────────────────────
h0_pg   = M5Label('HOME', x=8, y=32,  color=C_MUT, font=FONT_MONT_10)
h0_temp = M5Label('--',   x=8, y=50,  color=C_HI,  font=FONT_MONT_14)
h0_unit = M5Label('C',    x=145,y=50, color=C_MUT, font=FONT_MONT_14)
h0_main = M5Label('--',   x=8, y=82,  color=C_PRI, font=FONT_MONT_14)
h0_desc = M5Label('--',   x=8, y=108, color=C_MUT, font=FONT_MONT_10)
h0_sep2 = M5Label('- - - - - - - - - - - - - - -', x=8, y=130, color=C_SEP, font=FONT_MONT_10)
h0_date = M5Label('',     x=8, y=146, color=C_MUT, font=FONT_MONT_14)
h0_api  = M5Label('',     x=8, y=182, color=C_MUT, font=FONT_MONT_10)

# ── PAGE 1 — INDOOR ──────────────────────────────────
i_pg     = M5Label('INDOOR', x=8, y=32,  color=C_MUT, font=FONT_MONT_10)
i_temp   = M5Label('',       x=8, y=50,  color=C_PRI, font=FONT_MONT_14)
i_hum    = M5Label('',       x=8, y=82,  color=C_PRI, font=FONT_MONT_14)
i_sep    = M5Label('- - - - - - - - - - - - - - -', x=8, y=110, color=C_SEP, font=FONT_MONT_10)
i_tvoc   = M5Label('',       x=8, y=124, color=C_PRI, font=FONT_MONT_14)
i_eco2   = M5Label('',       x=8, y=156, color=C_PRI, font=FONT_MONT_14)
i_motion = M5Label('',       x=8, y=184, color=C_MUT, font=FONT_MONT_10)

# ── PAGE 2 — FORECAST ────────────────────────────────
fc_pg  = M5Label('FORECAST', x=8, y=32,  color=C_MUT, font=FONT_MONT_10)
fc_f1  = M5Label('',         x=8, y=55,  color=C_PRI, font=FONT_MONT_14)
fc_f2  = M5Label('',         x=8, y=97,  color=C_PRI, font=FONT_MONT_14)
fc_f3  = M5Label('',         x=8, y=139, color=C_PRI, font=FONT_MONT_14)
fc_api = M5Label('',         x=8, y=184, color=C_MUT, font=FONT_MONT_10)

# ── PAGE 3 — CLOUD ───────────────────────────────────
cl_pg   = M5Label('CLOUD', x=8, y=32,  color=C_MUT, font=FONT_MONT_10)
cl_wifi = M5Label('',      x=8, y=54,  color=C_PRI, font=FONT_MONT_14)
cl_stat = M5Label('',      x=8, y=88,  color=C_OK,  font=FONT_MONT_14)
cl_last = M5Label('',      x=8, y=122, color=C_MUT, font=FONT_MONT_14)
cl_ni   = M5Label('',      x=8, y=155, color=C_MUT, font=FONT_MONT_10)
cl_nw   = M5Label('',      x=8, y=175, color=C_MUT, font=FONT_MONT_10)

# ── PAGE 4 — SETTINGS ────────────────────────────────
st_pg   = M5Label('SETTINGS', x=8,   y=32,  color=C_MUT,    font=FONT_MONT_10)
st_c0   = M5Label('',         x=4,   y=52,  color=C_ACCENT, font=FONT_MONT_14)
st_l0   = M5Label('Indoor Send ',  x=20, y=52,  color=C_PRI, font=FONT_MONT_14)
st_v0   = M5Label('',         x=230, y=52,  color=C_HI,     font=FONT_MONT_14)
st_sep0 = M5Label('- - - - - - - - - - - - - - -', x=8, y=76, color=C_SEP, font=FONT_MONT_10)
st_c1   = M5Label('',         x=4,   y=88,  color=C_ACCENT, font=FONT_MONT_14)
st_l1   = M5Label('Weather Send',  x=20, y=88,  color=C_PRI, font=FONT_MONT_14)
st_v1   = M5Label('',         x=230, y=88,  color=C_HI,     font=FONT_MONT_14)
st_sep1 = M5Label('- - - - - - - - - - - - - - -', x=8, y=112, color=C_SEP, font=FONT_MONT_10)
st_c2   = M5Label('',         x=4,   y=124, color=C_ACCENT, font=FONT_MONT_14)
st_l2   = M5Label('Weather Fetch', x=20, y=124, color=C_PRI, font=FONT_MONT_14)
st_v2   = M5Label('',         x=230, y=124, color=C_HI,     font=FONT_MONT_14)
st_sep2 = M5Label('- - - - - - - - - - - - - - -', x=8, y=148, color=C_SEP, font=FONT_MONT_10)
st_hint = M5Label('',         x=8,   y=160, color=C_MUT,    font=FONT_MONT_10)

# ── PAGE 5 — VOICE ───────────────────────────────────
vc_pg      = M5Label('VOICE ASSISTANT', x=8,  y=32,  color=C_MUT,    font=FONT_MONT_10)
vc_status  = M5Label('Pret',            x=8,  y=52,  color=C_PRI,    font=FONT_MONT_14)
vc_step    = M5Label('',                x=8,  y=76,  color=C_MUT,    font=FONT_MONT_10)
vc_spin    = M5Label('',                x=295,y=76,  color=C_ACCENT, font=FONT_MONT_10)
vc_q_tag   = M5Label('',               x=8,  y=105, color=C_MUT,    font=FONT_MONT_10)
vc_q1      = M5Label('',               x=8,  y=120, color=C_PRI,    font=FONT_MONT_10)
vc_q2      = M5Label('',               x=8,  y=136, color=C_PRI,    font=FONT_MONT_10)
vc_r_tag   = M5Label('',               x=8,  y=155, color=C_MUT,    font=FONT_MONT_10)
vc_r1      = M5Label('',               x=8,  y=170, color=C_OK,     font=FONT_MONT_10)
vc_r2      = M5Label('',               x=8,  y=186, color=C_OK,     font=FONT_MONT_10)

# ── GROUPES PAR PAGE ─────────────────────────────────
PAGES = [
    [h0_pg, h0_temp, h0_unit, h0_main, h0_desc, h0_sep2, h0_date, h0_api],
    [i_pg, i_temp, i_hum, i_sep, i_tvoc, i_eco2, i_motion],
    [fc_pg, fc_f1, fc_f2, fc_f3, fc_api],
    [cl_pg, cl_wifi, cl_stat, cl_last, cl_ni, cl_nw],
    [st_pg, st_c0, st_l0, st_v0, st_sep0,
             st_c1, st_l1, st_v1, st_sep1,
             st_c2, st_l2, st_v2, st_sep2, st_hint],
    [vc_pg, vc_status, vc_step, vc_spin,
             vc_q_tag, vc_q1, vc_q2,
             vc_r_tag, vc_r1, vc_r2],
]

BTN_MAP = {
    PAGE_HOME:     ('◄ prev', 'ROOM ▶', 'next ►'),
    PAGE_INDOOR:   ('◄ prev', 'ROOM ▶', 'next ►'),
    PAGE_FORECAST: ('◄ prev', 'REFRESH', 'next ►'),
    PAGE_CLOUD:    ('◄ prev', 'SEND',   'next ►'),
    PAGE_SETTINGS: ('▼ val',  'suivant', '▲ val'),
    PAGE_VOICE:    ('◄ prev', 'PARLER', 'next ►'),
}

# ╔══════════════════════════════════════════════════════╗
# ║                     SENSORS                          ║
# ╚══════════════════════════════════════════════════════╝
env3 = None; pir = None; gas = None
try:    env3 = unit.get(unit.ENV3, unit.PORTA)
except: pass
try:    pir  = unit.get(unit.PIR,  unit.PORTB)
except: pass
try:    gas  = unit.get(unit.TVOC, unit.PORTA)
except:
    try:    gas = unit.get(unit.SGP30, unit.PORTA)
    except: pass

mic = MicRecord()

# ╔══════════════════════════════════════════════════════╗
# ║                 HELPERS GÉNÉRAUX                     ║
# ╚══════════════════════════════════════════════════════╝
def room():    return ROOMS[room_idx]
def now_str():
    t = time.localtime()
    return '{:02d}:{:02d}:{:02d}'.format(t[3], t[4], t[5])
def date_str():
    t = time.localtime()
    return '{:02d} / {:02d} / {}'.format(t[2], t[1], t[0])
def ms_to_str(ms):
    if ms <= 0: return '0s'
    s = int(ms / 1000)
    return '{}m{}s'.format(int(s/60), s%60) if s >= 60 else '{}s'.format(s)
def trunc(text, n=36):
    s = str(text); return s if len(s) <= n else s[:n]
def cloud_c(s):
    if 'OK' in s: return C_OK
    if any(x in s for x in ('ERR','EXC','No')): return C_ERR
    return C_WARN
def safe_close(r):
    try:
        if r: r.close()
    except: pass
def free_ram():
    gc.collect()
def safe_remove(path):
    try:    os.remove(path)
    except: pass
def file_exists(path):
    try:    os.stat(path); return True
    except: return False
def file_size(path):
    try:    return os.stat(path)[6]
    except: return 0

# ╔══════════════════════════════════════════════════════╗
# ║             HELPERS DISPLAY VOICE                    ║
# ╚══════════════════════════════════════════════════════╝
def vc_set_status(text, color=C_PRI):
    vc_status.set_text(str(text)[:38])
    vc_status.set_text_color(color)

def vc_set_step(text):
    vc_step.set_text(str(text)[:38])

def vc_spin_tick():
    global _spin_i
    _spin_i = (_spin_i + 1) % 4
    vc_spin.set_text(SPIN_FRAMES[_spin_i])

def vc_spin_clear():
    vc_spin.set_text('')

def vc_show_question(text):
    vc_q_tag.set_text('QUESTION :')
    s = str(text)
    vc_q1.set_text(s[:38])
    vc_q2.set_text(s[38:76])

def vc_show_answer(text):
    vc_r_tag.set_text('REPONSE :')
    s = str(text)
    vc_r1.set_text(s[:38])
    vc_r2.set_text(s[38:76])

def vc_reset():
    vc_q_tag.set_text(''); vc_q1.set_text(''); vc_q2.set_text('')
    vc_r_tag.set_text(''); vc_r1.set_text(''); vc_r2.set_text('')
    vc_set_step(''); vc_spin_clear()

# ╔══════════════════════════════════════════════════════╗
# ║          HTTPS POST JSON (avec spinner voice)        ║
# ╚══════════════════════════════════════════════════════╝
def https_post_json_voice(host, port, path, payload_dict, api_key):
    body   = json.dumps(payload_dict)
    body_b = body.encode('utf-8')
    req = (
        'POST ' + path + ' HTTP/1.1\r\n'
        'Host: ' + host + '\r\n'
        'Content-Type: application/json\r\n'
        'x-api-key: ' + api_key + '\r\n'
        'Content-Length: ' + str(len(body_b)) + '\r\n'
        'Connection: close\r\n\r\n'
    ).encode('utf-8') + body_b
    s = ss = None
    try:
        addr = usocket.getaddrinfo(host, port, 0, usocket.SOCK_STREAM)[0][-1]
        s = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
        s.settimeout(30)
        s.connect(addr)
        ss = ussl.wrap_socket(s, server_hostname=host)
        ss.write(req)
        raw = b''
        while True:
            chunk = ss.read(512)
            if not chunk: break
            raw += chunk
            vc_spin_tick()
        first_line  = raw.split(b'\r\n')[0].decode('utf-8')
        status_code = int(first_line.split(' ')[1])
        parts       = raw.split(b'\r\n\r\n', 1)
        body_text   = parts[1].decode('utf-8') if len(parts) > 1 else ''
        return status_code, body_text
    except Exception as e:
        return None, str(e)
    finally:
        if ss:
            try: ss.close()
            except: pass
        elif s:
            try: s.close()
            except: pass

# ╔══════════════════════════════════════════════════════╗
# ║       HTTPS POST AUDIO → FILE (chunked stream)       ║
# ╚══════════════════════════════════════════════════════╝
def https_post_audio_to_file(host, port, path, payload_dict, api_key, out_file):
    body   = json.dumps(payload_dict)
    body_b = body.encode('utf-8')
    req = (
        'POST ' + path + ' HTTP/1.1\r\n'
        'Host: ' + host + '\r\n'
        'Content-Type: application/json\r\n'
        'x-api-key: ' + api_key + '\r\n'
        'Content-Length: ' + str(len(body_b)) + '\r\n'
        'Connection: close\r\n\r\n'
    ).encode('utf-8') + body_b
    s = ss = f = None
    try:
        addr = usocket.getaddrinfo(host, port, 0, usocket.SOCK_STREAM)[0][-1]
        s = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
        s.settimeout(30)
        s.connect(addr)
        ss = ussl.wrap_socket(s, server_hostname=host)
        ss.write(req)
        header_data = b''
        while b'\r\n\r\n' not in header_data:
            chunk = ss.read(128)
            if not chunk: break
            header_data += chunk
            vc_spin_tick()
        if b'\r\n\r\n' not in header_data:
            return False, 'Invalid HTTP response'
        header_part, body_start = header_data.split(b'\r\n\r\n', 1)
        first_line  = header_part.split(b'\r\n')[0].decode('utf-8')
        status_code = int(first_line.split(' ')[1])
        if status_code != 200:
            return False, 'HTTP ' + str(status_code)
        safe_remove(out_file)
        f = open(out_file, 'wb')
        if body_start:
            f.write(body_start)
        bw = len(body_start)
        while True:
            chunk = ss.read(512)
            if not chunk: break
            f.write(chunk)
            bw += len(chunk)
            vc_spin_tick()
        f.close(); f = None
        return True, str(bw) + 'B'
    except Exception as e:
        return False, str(e)
    finally:
        if f:
            try: f.close()
            except: pass
        if ss:
            try: ss.close()
            except: pass
        elif s:
            try: s.close()
            except: pass

# ╔══════════════════════════════════════════════════════╗
# ║         ENCODE WAV BASE64 CHUNKED (économise RAM)    ║
# ╚══════════════════════════════════════════════════════╝
def encode_wav_chunked(filepath):
    import ubinascii
    result = ''
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(384)   # 384 → 512 chars base64
            if not chunk: break
            result += ubinascii.b2a_base64(chunk).decode().replace('\n', '')
            free_ram()
            vc_spin_tick()
    return result

# ╔══════════════════════════════════════════════════════╗
# ║                   VOICE FLOW                         ║
# ╚══════════════════════════════════════════════════════╝
def voice_flow():
    try:
        vc_reset()
        free_ram()

        # Feedback immédiat
        vc_set_status('Bouton detecte !', C_WARN)
        wait_ms(200)

        # Compte à rebours
        for i in range(3, 0, -1):
            vc_set_status('Parlez dans ' + str(i) + 's...', C_WARN)
            wait_ms(1000)

        vc_set_status('>>> PARLEZ MAINTENANT <<<', C_ERR)
        wait_ms(100)

        # 1/5 Enregistrement
        vc_set_step('1/5  Enregistrement...')
        mic.record2file(RECORD_SECONDS, VOICE_FILE)
        free_ram()

        sz = file_size(VOICE_FILE)
        if sz < 1000:
            vc_set_status('Enregistrement vide', C_ERR)
            return

        vc_set_status('Traitement en cours...', C_ACCENT)

        # 2/5 Encodage base64
        vc_set_step('2/5  Encodage audio...')
        audio_b64 = encode_wav_chunked(VOICE_FILE)
        free_ram()

        # 3/5 STT
        vc_set_step('3/5  Transcription...')
        code, body = https_post_json_voice(
            VOICE_HOST, 443, '/',
            {'audio_base64': audio_b64, 'language_code': 'fr-FR'},
            CLOUD_API_KEY
        )
        audio_b64 = None
        free_ram()

        if code is None:
            vc_set_status('STT erreur reseau', C_ERR)
            vc_set_step(str(body)[:38])
            vc_spin_clear(); return
        if code != 200:
            vc_set_status('STT HTTP ' + str(code), C_ERR)
            vc_set_step(str(body)[:38])
            vc_spin_clear(); return

        try:
            resp_data  = json.loads(body)
            transcript = resp_data.get('transcript', '').strip()
        except Exception as e:
            vc_set_status('STT JSON ERR', C_ERR)
            vc_set_step(str(e))
            vc_spin_clear(); return

        if not transcript:
            vc_set_status('Rien entendu, reessayez', C_WARN)
            vc_set_step('Parlez plus fort et plus pres')
            vc_spin_clear(); return

        vc_show_question(transcript)

        # 4/5 LLM
        vc_set_step('4/5  Reflexion...')
        code2, body2 = https_post_json_voice(
            ASK_HOST, 443, '/',
            {'question': transcript},
            CLOUD_API_KEY
        )
        free_ram()

        if code2 is None:
            vc_set_status('LLM erreur reseau', C_ERR)
            vc_set_step(str(body2)[:38])
            vc_spin_clear(); return
        if code2 != 200:
            vc_set_status('LLM HTTP ' + str(code2), C_ERR)
            vc_set_step(str(body2)[:38])
            vc_spin_clear(); return

        try:
            answer = json.loads(body2).get('answer', '')
        except Exception as e:
            vc_set_status('LLM JSON ERR', C_ERR)
            vc_set_step(str(e))
            vc_spin_clear(); return

        if not answer:
            vc_set_status('Reponse vide', C_WARN)
            vc_spin_clear(); return

        vc_show_answer(answer)

        # 5/5 TTS
        vc_set_step('5/5  Synthese vocale...')
        ok, msg = https_post_audio_to_file(
            RESP_HOST, 443, '/',
            {'answer': answer},
            CLOUD_API_KEY,
            RESP_FILE_FLASH
        )
        free_ram()

        if not ok:
            vc_set_status('TTS ERR', C_ERR)
            vc_set_step(msg)
            vc_spin_clear(); return

        # Lecture
        vc_set_step('Lecture...')
        vc_spin_clear()
        vc_set_status('Reponse en cours...', C_OK)
        speaker.playWAV('res/resp.wav', volume=10)

        vc_set_step('')
        vc_set_status('Pret — appuie sur B', C_PRI)

    except Exception as e:
        vc_set_status('ERREUR', C_ERR)
        vc_set_step(str(e)[:38])
        vc_spin_clear()
        free_ram()

# ╔══════════════════════════════════════════════════════╗
# ║                     DISPLAY                          ║
# ╚══════════════════════════════════════════════════════╝
def _set_btn_labels(p):
    a, b, c = BTN_MAP.get(p, ('◄', '', '►'))
    btn_a.set_text(a)
    btn_b.set_text(b)
    btn_c.set_text(c)

def _draw_dots():
    dots = ''
    for i in range(TOTAL_PAGES):
        dots += ('●' if i == current_page else '○')
    f_dots.set_text(dots)

def show_page():
    for pg in PAGES:
        for w in pg:
            w.set_hidden(True)
    for w in PAGES[current_page]:
        w.set_hidden(False)
    _draw_dots()
    _set_btn_labels(current_page)
    _draw_header()
    _draw_page()

def _draw_header():
    h_room.set_text(room())
    t = time.localtime()
    h_time.set_text('{:02d}:{:02d}:{:02d}'.format(t[3], t[4], t[5]))
    h_dot.set_text_color(C_OK if wifi_ok else C_ERR)

def _draw_page():
    p = current_page

    if p == PAGE_HOME:
        h0_temp.set_text(str(outdoor_temp))
        h0_main.set_text(str(weather_main))
        h0_desc.set_text(trunc(str(weather_desc), 38))
        h0_date.set_text(date_str())
        h0_api.set_text('MAJ : ' + last_api_time)

    elif p == PAGE_INDOOR:
        i_temp.set_text('Temp      ' + str(indoor_temp) + ' C')
        i_hum.set_text('Humidite  ' + str(indoor_hum) + ' %')
        i_tvoc.set_text('TVOC      ' + str(tvoc_val))
        i_eco2.set_text('eCO2      ' + str(eco2_val))
        i_motion.set_text('Mouvement : ' + ('Detecte !' if motion_on else 'Aucun'))
        i_motion.set_text_color(C_WARN if motion_on else C_MUT)

    elif p == PAGE_FORECAST:
        fc_f1.set_text('J+1   ' + str(forecast_1))
        fc_f2.set_text('J+2   ' + str(forecast_2))
        fc_f3.set_text('J+3   ' + str(forecast_3))
        fc_api.set_text('MAJ : ' + last_api_time)

    elif p == PAGE_CLOUD:
        cl_wifi.set_text('WiFi     ' + ('Connecte' if wifi_ok else 'Hors ligne'))
        cl_wifi.set_text_color(C_OK if wifi_ok else C_ERR)
        cl_stat.set_text('Cloud    ' + cloud_status)
        cl_stat.set_text_color(cloud_c(cloud_status))
        cl_last.set_text('Envoi    ' + last_cloud_send)
        now_ms = time.ticks_ms()
        ri = ms_to_str(FREQ_OPTS[freq_indoor_idx][1]  - time.ticks_diff(now_ms, t_isend))
        rw = ms_to_str(FREQ_OPTS[freq_weather_idx][1] - time.ticks_diff(now_ms, t_wsend))
        cl_ni.set_text('Next indoor   ' + ri)
        cl_nw.set_text('Next weather  ' + rw)

    elif p == PAGE_SETTINGS:
        _draw_settings()

    elif p == PAGE_VOICE:
        pass   # géré dynamiquement par voice_flow()

def _draw_settings():
    st_c0.set_text('►' if settings_sel == 0 else ' ')
    st_c1.set_text('►' if settings_sel == 1 else ' ')
    st_c2.set_text('►' if settings_sel == 2 else ' ')
    st_l0.set_text_color(C_PRI if settings_sel == 0 else C_MUT)
    st_l1.set_text_color(C_PRI if settings_sel == 1 else C_MUT)
    st_l2.set_text_color(C_PRI if settings_sel == 2 else C_MUT)
    st_v0.set_text(FREQ_OPTS[freq_indoor_idx][0])
    st_v1.set_text(FREQ_OPTS[freq_weather_idx][0])
    st_v2.set_text(FREQ_OPTS[freq_fetch_idx][0])
    st_hint.set_text('B : suivant  →  RETOUR' if settings_sel == 2 else 'B : ligne suivante')

def redraw():
    _draw_header()
    _draw_page()

# ╔══════════════════════════════════════════════════════╗
# ║                   WIFI & TIME                        ║
# ╚══════════════════════════════════════════════════════╝
def check_wifi():
    global wifi_ok
    try:    wifi_ok = wifiCfg.is_connected()
    except: wifi_ok = False

def sync_ntp():
    global time_valid
    try:    ntptime.client(host='pool.ntp.org', timezone=1); time_valid = True
    except:
        try:    ntptime.settime(); time_valid = True
        except: pass

# ╔══════════════════════════════════════════════════════╗
# ║                  OPENWEATHER                         ║
# ╚══════════════════════════════════════════════════════╝
def fetch_weather():
    global outdoor_temp, weather_main, weather_desc, last_api_time
    r = None
    try:
        url = ('http://api.openweathermap.org/data/2.5/weather?lat=' + LAT +
               '&lon=' + LON + '&appid=' + OW_API_KEY + '&units=metric&lang=fr')
        r = urequests.get(url)
        d = r.json()
        outdoor_temp  = str(round(d['main']['temp'], 1))
        weather_main  = str(d['weather'][0]['main'])
        weather_desc  = str(d['weather'][0]['description'])
        last_api_time = now_str()
    except:
        outdoor_temp = '--'; weather_main = 'API ERR'; weather_desc = '--'
    finally:
        safe_close(r)

def fetch_forecast():
    global forecast_1, forecast_2, forecast_3, last_api_time
    r = None
    try:
        url = ('http://api.openweathermap.org/data/2.5/forecast?lat=' + LAT +
               '&lon=' + LON + '&appid=' + OW_API_KEY + '&units=metric&lang=fr')
        r = urequests.get(url)
        d = r.json()
        lst = d['list']
        def fmt(i): return str(int(lst[i]['main']['temp'])) + 'C  ' + lst[i]['weather'][0]['main']
        forecast_1 = fmt(8); forecast_2 = fmt(16); forecast_3 = fmt(24)
        last_api_time = now_str()
    except:
        forecast_1 = 'ERR'; forecast_2 = '--'; forecast_3 = '--'
    finally:
        safe_close(r)

def do_weather_fetch():
    fetch_weather(); fetch_forecast(); redraw()

# ╔══════════════════════════════════════════════════════╗
# ║               CLOUD SEND (données capteurs)          ║
# ╚══════════════════════════════════════════════════════╝
def _https_post(host, path, payload):
    body = json.dumps(payload).encode('utf-8')
    req  = (
        'POST ' + path + ' HTTP/1.0\r\n'
        'Host: ' + host + '\r\n'
        'Content-Type: application/json\r\n'
        'x-api-key: ' + CLOUD_API_KEY + '\r\n'
        'Content-Length: ' + str(len(body)) + '\r\n'
        'Connection: close\r\n\r\n'
    ).encode('utf-8') + body
    s = ss = None
    try:
        addr = usocket.getaddrinfo(host, CLOUD_PORT, 0, usocket.SOCK_STREAM)[0][-1]
        s = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
        s.settimeout(15)
        s.connect(addr)
        ss = ussl.wrap_socket(s, server_hostname=host)
        ss.write(req)
        raw = b''
        while True:
            c = ss.read(512)
            if not c: break
            raw += c
        code  = int(raw.split(b'\r\n')[0].decode().split(' ')[1])
        parts = raw.split(b'\r\n\r\n', 1)
        body2 = parts[1].decode('utf-8') if len(parts) > 1 else ''
        return code, body2
    except Exception as e:
        return None, str(e)
    finally:
        if ss:
            try: ss.close()
            except: pass
        elif s:
            try: s.close()
            except: pass

def read_indoor():
    global indoor_temp, indoor_hum, tvoc_val, eco2_val, motion_on
    if env3:
        try:    indoor_temp = str(round(env3.temperature, 1))
        except: indoor_temp = '--'
        try:    indoor_hum  = str(round(env3.humidity, 1))
        except: indoor_hum  = '--'
    if gas:
        try:    tvoc_val = str(gas.tvoc);  eco2_val = str(gas.eco2)
        except:
            try:    tvoc_val = str(gas.TVOC); eco2_val = str(gas.eCO2)
            except: tvoc_val = '--'; eco2_val = '--'
    if pir:
        try:    motion_on = bool(pir.state)
        except: motion_on = False

def send_indoor():
    global cloud_status, last_cloud_send
    if not wifi_ok: cloud_status = 'No WiFi'; return False
    code, _ = _https_post(CLOUD_HOST, '/?type=indoor', {
        'room'            : room(),
        'indoor_temp'     : float(indoor_temp)  if indoor_temp != '--' else 0.0,
        'indoor_humidity' : float(indoor_hum)   if indoor_hum  != '--' else 0.0,
        'tvoc'            : int(float(tvoc_val)) if tvoc_val   != '--' else 0,
        'eco2'            : int(float(eco2_val)) if eco2_val   != '--' else 0,
        'motion_detected' : bool(motion_on),
    })
    if code == 200: cloud_status = 'Indoor OK'; last_cloud_send = now_str(); return True
    cloud_status = 'Indoor ' + (str(code) if code else 'EXC'); return False

def send_weather():
    global cloud_status, last_cloud_send
    if not wifi_ok: cloud_status = 'No WiFi'; return False
    code, _ = _https_post(CLOUD_HOST, '/?type=weather', {
        'location'      : 'Geneva',
        'outdoor_temp'  : float(outdoor_temp) if outdoor_temp != '--' else 0.0,
        'weather_main'  : str(weather_main),
        'weather_desc'  : str(weather_desc),
        'forecast_day_1': str(forecast_1),
        'forecast_day_2': str(forecast_2),
        'forecast_day_3': str(forecast_3),
    })
    if code == 200: cloud_status = 'Weather OK'; last_cloud_send = now_str(); return True
    cloud_status = 'Weather ' + (str(code) if code else 'EXC'); return False

def send_all():
    global cloud_status, last_cloud_send
    i = send_indoor(); w = send_weather()
    if i and w:   cloud_status = 'Cloud OK';    last_cloud_send = now_str()
    elif i:       cloud_status = 'Indoor only'
    elif w:       cloud_status = 'Weather only'
    else:         cloud_status = 'Cloud ERR'
    redraw()

# ╔══════════════════════════════════════════════════════╗
# ║                     BUTTONS                          ║
# ╚══════════════════════════════════════════════════════╝
def handle_buttons():
    global current_page, prev_page, room_idx, settings_sel
    global freq_indoor_idx, freq_weather_idx, freq_fetch_idx

    a = btnA.wasPressed()
    b = btnB.wasPressed()
    c = btnC.wasPressed()

    if not (a or b or c):
        return

    if current_page == PAGE_SETTINGS:
        if a:
            if   settings_sel == 0: freq_indoor_idx  = (freq_indoor_idx  - 1) % len(FREQ_OPTS)
            elif settings_sel == 1: freq_weather_idx = (freq_weather_idx - 1) % len(FREQ_OPTS)
            else:                   freq_fetch_idx   = (freq_fetch_idx   - 1) % len(FREQ_OPTS)
            _draw_settings()
        elif c:
            if   settings_sel == 0: freq_indoor_idx  = (freq_indoor_idx  + 1) % len(FREQ_OPTS)
            elif settings_sel == 1: freq_weather_idx = (freq_weather_idx + 1) % len(FREQ_OPTS)
            else:                   freq_fetch_idx   = (freq_fetch_idx   + 1) % len(FREQ_OPTS)
            _draw_settings()
        elif b:
            if settings_sel < 2:
                settings_sel += 1
                _draw_settings()
            else:
                settings_sel = 0
                current_page = prev_page
                show_page()
    else:
        if a:
            current_page = (current_page - 1) % TOTAL_PAGES
            show_page()
        elif c:
            current_page = (current_page + 1) % TOTAL_PAGES
            show_page()
        elif b:
            if   current_page == PAGE_HOME:     room_idx = (room_idx + 1) % len(ROOMS); redraw()
            elif current_page == PAGE_INDOOR:   room_idx = (room_idx + 1) % len(ROOMS); redraw()
            elif current_page == PAGE_FORECAST: do_weather_fetch()
            elif current_page == PAGE_CLOUD:    send_all()
            elif current_page == PAGE_VOICE:    voice_flow()

# ╔══════════════════════════════════════════════════════╗
# ║                       INIT                           ║
# ╚══════════════════════════════════════════════════════╝
check_wifi()
if wifi_ok: sync_ntp()
if time.localtime()[0] >= 2024: time_valid = True
read_indoor()
do_weather_fetch()
show_page()

now0     = time.ticks_ms()
t_clock  = now0; t_iread  = now0; t_wifi   = now0
t_wfetch = now0; t_isend  = now0; t_wsend  = now0; t_ntp = now0

# ╔══════════════════════════════════════════════════════╗
# ║                       LOOP                           ║
# ╚══════════════════════════════════════════════════════╝
while True:
    now = time.ticks_ms()

    handle_buttons()

    if time.ticks_diff(now, t_clock) >= 1000:
        if time.localtime()[0] >= 2024: time_valid = True
        _draw_header()
        if current_page == PAGE_CLOUD: _draw_page()
        t_clock = now

    if time.ticks_diff(now, t_iread) >= 3000:
        read_indoor()
        if current_page == PAGE_INDOOR: _draw_page()
        t_iread = now

    if time.ticks_diff(now, t_wifi) >= 5000:
        check_wifi()
        h_dot.set_text_color(C_OK if wifi_ok else C_ERR)
        t_wifi = now

    if time.ticks_diff(now, t_wfetch) >= FREQ_OPTS[freq_fetch_idx][1]:
        do_weather_fetch()
        t_wfetch = now

    if time.ticks_diff(now, t_isend) >= FREQ_OPTS[freq_indoor_idx][1]:
        send_indoor()
        if current_page == PAGE_CLOUD: _draw_page()
        t_isend = now

    if time.ticks_diff(now, t_wsend) >= FREQ_OPTS[freq_weather_idx][1]:
        send_weather()
        if current_page == PAGE_CLOUD: _draw_page()
        t_wsend = now

    if (not time_valid) and time.ticks_diff(now, t_ntp) >= 60000:
        if wifi_ok: sync_ntp()
        t_ntp = now

    time.sleep_ms(15)