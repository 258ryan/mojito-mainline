# hold the hostless voice PCMs (hw:0,4) PREPARED AND STARTED (stop threshold = boundary, so playback runs without
# data, as the OnePlus 6T's q6voiced fix): the voice front end then keeps its back ends running across the sound
# server's stream changes. Runs until killed.
import ctypes, sys, time, signal
a = ctypes.CDLL("libasound.so.2")
pcms = []
for stream in (0, 1):  # playback, capture
    p = ctypes.c_void_p()
    r = a.snd_pcm_open(ctypes.byref(p), b"hw:0,4", stream, 0)
    if r < 0: sys.exit("open %d: %d" % (stream, r))
    r = a.snd_pcm_set_params(p, 2, 3, 1, 8000, 0, 100000)   # S16_LE, RW interleaved, mono, 8 kHz, 100 ms
    if r < 0: sys.exit("params %d: %d" % (stream, r))
    sw = ctypes.c_void_p(); a.snd_pcm_sw_params_malloc(ctypes.byref(sw))
    a.snd_pcm_sw_params_current(p, sw)
    b = ctypes.c_ulong(); a.snd_pcm_sw_params_get_boundary(sw, ctypes.byref(b))
    a.snd_pcm_sw_params_set_stop_threshold(p, sw, b)
    r = a.snd_pcm_sw_params(p, sw); a.snd_pcm_sw_params_free(sw)
    if r < 0: sys.exit("sw params %d: %d" % (stream, r))
    pcms.append(p)
for p in pcms:
    a.snd_pcm_prepare(p)
for i, p in enumerate(pcms):
    print("start", "playback" if i == 0 else "capture", a.snd_pcm_start(p), flush=True)
signal.signal(signal.SIGTERM, lambda *x: sys.exit(0))
try:
    while True:
        time.sleep(60)
finally:
    for p in pcms:
        a.snd_pcm_drop(p); a.snd_pcm_close(p)
