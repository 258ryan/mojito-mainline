#!/usr/bin/env python3
# Off-screen OpenGL ES test on the Adreno render node: GBM device -> EGL (surfaceless) -> FBO -> clear + shader triangle -> readback.
import ctypes as C, os, sys
from ctypes import c_int, c_uint, c_void_p, c_char_p, c_float, c_ubyte, POINTER
gbm = C.CDLL("libgbm.so.1"); egl = C.CDLL("libEGL.so.1"); gl = C.CDLL("libGLESv2.so.2")
def sig(lib, name, res, *args):
    f = getattr(lib, name); f.restype = res; f.argtypes = list(args); return f

fd = os.open("/dev/dri/renderD128", os.O_RDWR)
sig(gbm, "gbm_create_device", c_void_p, c_int); dev = gbm.gbm_create_device(fd)
print("gbm device:", bool(dev), "backend:", C.cast(sig(gbm, "gbm_device_get_backend_name", c_char_p, c_void_p)(dev), c_char_p).value if dev else None)
getdpy = sig(egl, "eglGetPlatformDisplay", c_void_p, c_uint, c_void_p, c_void_p)
dpy = getdpy(0x31D7, dev, None); print("egl display:", bool(dpy))
maj, mino = c_int(), c_int()
assert sig(egl, "eglInitialize", c_uint, c_void_p, POINTER(c_int), POINTER(c_int))(dpy, C.byref(maj), C.byref(mino)), "eglInitialize failed"
q = sig(egl, "eglQueryString", c_char_p, c_void_p, c_int)
print("EGL %d.%d vendor=%s" % (maj.value, mino.value, q(dpy, 0x3053).decode()))
assert sig(egl, "eglBindAPI", c_uint, c_uint)(0x30A0)
cfg = c_void_p(); n = c_int()
attrs = (c_int * 3)(0x3040, 0x4, 0x3038)           # RENDERABLE_TYPE = ES2, NONE
assert sig(egl, "eglChooseConfig", c_uint, c_void_p, POINTER(c_int), POINTER(c_void_p), c_int, POINTER(c_int))(dpy, attrs, C.byref(cfg), 1, C.byref(n)) and n.value, "no EGL config"
cattrs = (c_int * 3)(0x3098, 2, 0x3038)             # CONTEXT_CLIENT_VERSION = 2
ctx = sig(egl, "eglCreateContext", c_void_p, c_void_p, c_void_p, c_void_p, POINTER(c_int))(dpy, cfg, None, cattrs)
assert ctx, "eglCreateContext failed: 0x%x" % sig(egl, "eglGetError", c_int)()
assert sig(egl, "eglMakeCurrent", c_uint, c_void_p, c_void_p, c_void_p, c_void_p)(dpy, None, None, ctx), "eglMakeCurrent failed (surfaceless unsupported?)"

gs = sig(gl, "glGetString", c_char_p, c_uint)
for name, e in (("GL_VENDOR", 0x1F00), ("GL_RENDERER", 0x1F01), ("GL_VERSION", 0x1F02)):
    print("%-12s %s" % (name, (gs(e) or b"?").decode()))

W = H = 64
tex = c_uint(); fbo = c_uint()
sig(gl, "glGenTextures", None, c_int, POINTER(c_uint))(1, C.byref(tex))
sig(gl, "glBindTexture", None, c_uint, c_uint)(0x0DE1, tex.value)
sig(gl, "glTexParameteri", None, c_uint, c_uint, c_int)(0x0DE1, 0x2801, 0x2600)
sig(gl, "glTexParameteri", None, c_uint, c_uint, c_int)(0x0DE1, 0x2800, 0x2600)
sig(gl, "glTexImage2D", None, c_uint, c_int, c_int, c_int, c_int, c_int, c_uint, c_uint, c_void_p)(0x0DE1, 0, 0x1908, W, H, 0, 0x1908, 0x1401, None)
sig(gl, "glGenFramebuffers", None, c_int, POINTER(c_uint))(1, C.byref(fbo))
sig(gl, "glBindFramebuffer", None, c_uint, c_uint)(0x8D40, fbo.value)
sig(gl, "glFramebufferTexture2D", None, c_uint, c_uint, c_uint, c_uint, c_int)(0x8D40, 0x8CE0, 0x0DE1, tex.value, 0)
st = sig(gl, "glCheckFramebufferStatus", c_uint, c_uint)(0x8D40); print("framebuffer status: 0x%x (complete=0x8cd5)" % st)
assert st == 0x8CD5
def readpix(x, y):
    buf = (c_ubyte * 4)()
    sig(gl, "glReadPixels", None, c_int, c_int, c_int, c_int, c_uint, c_uint, c_void_p)(x, y, 1, 1, 0x1908, 0x1401, buf)
    return tuple(buf)
# test 1: clear
sig(gl, "glViewport", None, c_int, c_int, c_int, c_int)(0, 0, W, H)
sig(gl, "glClearColor", None, c_float, c_float, c_float, c_float)(1.0, 0.0, 0.5, 1.0)
sig(gl, "glClear", None, c_uint)(0x4000); sig(gl, "glFinish", None)()
p = readpix(W // 2, H // 2); print("clear test:  read", p, "expected (255, 0, 128, 255) ->", "PASS" if abs(p[0]-255) <= 1 and p[1] == 0 and abs(p[2]-128) <= 2 else "FAIL")
# test 2: shader-drawn triangle covering the viewport, fragment colour green
def shader(kind, src):
    s = sig(gl, "glCreateShader", c_uint, c_uint)(kind)
    arr = (c_char_p * 1)(src.encode()); sig(gl, "glShaderSource", None, c_uint, c_int, POINTER(c_char_p), POINTER(c_int))(s, 1, arr, None)
    sig(gl, "glCompileShader", None, c_uint)(s)
    ok = c_int(); sig(gl, "glGetShaderiv", None, c_uint, c_uint, POINTER(c_int))(s, 0x8B81, C.byref(ok))
    if not ok.value:
        log = C.create_string_buffer(512); sig(gl, "glGetShaderInfoLog", None, c_uint, c_int, POINTER(c_int), c_char_p)(s, 512, None, log); print("shader error:", log.value.decode()); sys.exit(2)
    return s
vs = shader(0x8B31, "attribute vec2 p; void main(){ gl_Position = vec4(p, 0.0, 1.0); }")
fs = shader(0x8B30, "precision mediump float; void main(){ gl_FragColor = vec4(0.0, 1.0, 0.0, 1.0); }")
prog = sig(gl, "glCreateProgram", c_uint)()
sig(gl, "glAttachShader", None, c_uint, c_uint)(prog, vs); sig(gl, "glAttachShader", None, c_uint, c_uint)(prog, fs)
sig(gl, "glLinkProgram", None, c_uint)(prog)
ok = c_int(); sig(gl, "glGetProgramiv", None, c_uint, c_uint, POINTER(c_int))(prog, 0x8B82, C.byref(ok)); print("program link:", "ok" if ok.value else "FAILED")
sig(gl, "glUseProgram", None, c_uint)(prog)
verts = (c_float * 6)(-1, -1, 3, -1, -1, 3)
loc = sig(gl, "glGetAttribLocation", c_int, c_uint, c_char_p)(prog, b"p")
sig(gl, "glEnableVertexAttribArray", None, c_uint)(loc)
sig(gl, "glVertexAttribPointer", None, c_uint, c_int, c_uint, c_ubyte, c_int, c_void_p)(loc, 2, 0x1406, 0, 0, C.cast(verts, c_void_p))
sig(gl, "glClearColor", None, c_float, c_float, c_float, c_float)(0, 0, 0, 1); sig(gl, "glClear", None, c_uint)(0x4000)
sig(gl, "glDrawArrays", None, c_uint, c_int, c_int)(0x4, 0, 3); sig(gl, "glFinish", None)()
c, e = readpix(W // 2, H // 2), readpix(1, 1)
print("triangle test: centre", c, "corner", e, "expected (0, 255, 0, 255) ->", "PASS" if c == (0, 255, 0, 255) and e == (0, 255, 0, 255) else "FAIL")
print("GPU RENDER TEST COMPLETE")
