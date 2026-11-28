// Minimal loader for one Android arm64 library with no Android: maps it, applies its relocations (including Android's
// packed ones) and resolves its few imports to functions here. Runs under qemu-aarch64 on a PC.
#include <elf.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
// bionic keeps the stack canary at tpidr_el0+40: reserve that part of the TLS so nothing else writes it
__thread char tls_pad[256] __attribute__((aligned(8))) = {1};

static int quiet = 1;
static int a_log(int prio, const char *tag, const char *fmt, ...) {
	if (quiet && prio < 6) return 0;
	va_list ap; va_start(ap, fmt); fprintf(stderr, "[%s] ", tag ? tag : "-"); vfprintf(stderr, fmt, ap); fputc('\n', stderr); va_end(ap); return 0;
}
static void *a_memcpy_chk(void *d, const void *s, size_t n, size_t m) { (void)m; return memcpy(d, s, n); }
static size_t a_strlen_chk(const char *s, size_t m) { (void)m; return strlen(s); }
static size_t a_strlcpy(char *d, const char *s, size_t n) { size_t l = strlen(s); if (n) { size_t c = l < n - 1 ? l : n - 1; memcpy(d, s, c); d[c] = 0; } return l; }
static size_t a_strlcat(char *d, const char *s, size_t n) { size_t dl = strnlen(d, n); if (dl == n) return n + strlen(s); return dl + a_strlcpy(d + dl, s, n - dl); }
static long a_zero(void) { return 0; }
static void a_chk_fail(void) { fprintf(stderr, "stack check failed\n"); abort(); }
static void *resolve(const char *n) {
#define F(x) if (!strcmp(n, #x)) return (void *)x;
#define M(x, y) if (!strcmp(n, #x)) return (void *)y;
	F(access) F(fclose) F(fopen) F(free) F(fseek) F(ftell) F(malloc) F(memcmp) F(memcpy) F(memmove) F(memset) F(remove) F(strcmp)
	F(strrchr) F(strstr)
	M(fread_unlocked, fread) M(fwrite_unlocked, fwrite) M(__android_log_print, a_log) M(__memcpy_chk, a_memcpy_chk)
	M(__strlen_chk, a_strlen_chk) M(strlcpy, a_strlcpy) M(strlcat, a_strlcat) M(__stack_chk_fail, a_chk_fail)
	M(__cxa_finalize, a_zero)
	if (!strncmp(n, "Diag_", 5) || !strncmp(n, "diagpkt_", 8)) return (void *)a_zero;
	return NULL;
}

static uint8_t *base; static Elf64_Sym *symtab; static const char *strtab;
static uint64_t symval(uint32_t i) {
	Elf64_Sym *s = &symtab[i];
	if (s->st_shndx != SHN_UNDEF) return (uint64_t)base + s->st_value;
	void *p = resolve(strtab + s->st_name);
	if (!p && ELF64_ST_BIND(s->st_info) != STB_WEAK) { fprintf(stderr, "unresolved %s\n", strtab + s->st_name); exit(1); }
	return (uint64_t)p;
}
static void reloc(uint64_t off, uint64_t info, int64_t add) {
	uint64_t *w = (uint64_t *)(base + off); uint32_t t = ELF64_R_TYPE(info), s = ELF64_R_SYM(info);
	if (t == R_AARCH64_RELATIVE) *w = (uint64_t)base + add;
	else if (t == R_AARCH64_ABS64 || t == R_AARCH64_GLOB_DAT || t == R_AARCH64_JUMP_SLOT) *w = symval(s) + add;
	else if (t) { fprintf(stderr, "relocation type %u\n", t); exit(1); }
}
static int64_t sleb(const uint8_t **p) {
	int64_t v = 0; int shift = 0; uint8_t b;
	do { b = *(*p)++; v |= (int64_t)(b & 0x7f) << shift; shift += 7; } while (b & 0x80);
	if (shift < 64 && (b & 0x40)) v |= -((int64_t)1 << shift);
	return v;
}
static void packed(const uint8_t *p) {
	if (memcmp(p, "APS2", 4)) { fprintf(stderr, "bad packed relocations\n"); exit(1); }
	p += 4; int64_t count = sleb(&p); uint64_t off = sleb(&p); int64_t addend = 0;
	while (count > 0) {
		int64_t n = sleb(&p), f = sleb(&p), delta = 0; uint64_t info = 0;
		if (f & 2) delta = sleb(&p);
		if (f & 1) info = sleb(&p);
		if ((f & 8) && (f & 4)) addend += sleb(&p);
		for (int64_t i = 0; i < n; i++) {
			off += (f & 2) ? delta : sleb(&p);
			uint64_t in = (f & 1) ? info : (uint64_t)sleb(&p);
			if ((f & 8) && !(f & 4)) addend += sleb(&p);
			reloc(off, in, (f & 8) ? addend : 0);
		}
		if (!(f & 8)) addend = 0;
		count -= n;
	}
}

void *lib_load(const char *path, uint8_t **out_base) {
	FILE *f = fopen(path, "rb"); if (!f) { perror(path); exit(1); }
	fseek(f, 0, SEEK_END); long size = ftell(f); rewind(f);
	uint8_t *file = malloc(size); if (fread(file, 1, size, f) != (size_t)size) exit(1); fclose(f);
	Elf64_Ehdr *eh = (void *)file; Elf64_Phdr *ph = (void *)(file + eh->e_phoff); uint64_t top = 0; Elf64_Dyn *dyn = NULL;
	for (int i = 0; i < eh->e_phnum; i++) if (ph[i].p_type == PT_LOAD && ph[i].p_vaddr + ph[i].p_memsz > top) top = ph[i].p_vaddr + ph[i].p_memsz;
	base = mmap(NULL, (top + 0xffff) & ~0xffffUL, PROT_READ | PROT_WRITE | PROT_EXEC, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
	if (base == MAP_FAILED) { perror("mmap"); exit(1); }
	for (int i = 0; i < eh->e_phnum; i++) {
		if (ph[i].p_type == PT_LOAD) memcpy(base + ph[i].p_vaddr, file + ph[i].p_offset, ph[i].p_filesz);
		if (ph[i].p_type == PT_DYNAMIC) dyn = (void *)(file + ph[i].p_offset);
	}
	uint64_t rela = 0, relasz = 0, jmp = 0, jmpsz = 0, android = 0, relr = 0, relrsz = 0, init = 0, initsz = 0;
	for (Elf64_Dyn *d = dyn; d->d_tag != DT_NULL; d++) switch ((uint64_t)d->d_tag) {
		case DT_SYMTAB: symtab = (void *)(base + d->d_un.d_ptr); break;
		case DT_STRTAB: strtab = (void *)(base + d->d_un.d_ptr); break;
		case DT_RELA: rela = d->d_un.d_ptr; break; case DT_RELASZ: relasz = d->d_un.d_val; break;
		case DT_JMPREL: jmp = d->d_un.d_ptr; break; case DT_PLTRELSZ: jmpsz = d->d_un.d_val; break;
		case 0x60000011: android = d->d_un.d_ptr; break;
		case 0x6fffe000: case 36: relr = d->d_un.d_ptr; break; case 0x6fffe001: case 35: relrsz = d->d_un.d_val; break;
		case DT_INIT_ARRAY: init = d->d_un.d_ptr; break; case DT_INIT_ARRAYSZ: initsz = d->d_un.d_val; break;
	}
	if (android) packed(base + android);
	for (uint64_t i = 0; rela && i < relasz / sizeof(Elf64_Rela); i++) { Elf64_Rela *r = (Elf64_Rela *)(base + rela) + i; reloc(r->r_offset, r->r_info, r->r_addend); }
	uint64_t *where = NULL;
	for (uint64_t i = 0; relr && i < relrsz / 8; i++) {
		uint64_t e = ((uint64_t *)(base + relr))[i];
		if (!(e & 1)) { where = (uint64_t *)(base + e); *where++ += (uint64_t)base; }
		else { for (int b = 1; b < 64; b++) if (e >> b & 1) where[b - 1] += (uint64_t)base; where += 63; }
	}
	for (uint64_t i = 0; jmp && i < jmpsz / sizeof(Elf64_Rela); i++) { Elf64_Rela *r = (Elf64_Rela *)(base + jmp) + i; reloc(r->r_offset, r->r_info, r->r_addend); }
	__builtin___clear_cache((char *)base, (char *)base + top);
	for (uint64_t i = 0; init && i < initsz / 8; i++) { void (*fn)(void) = ((void (**)(void))(base + init))[i]; if (fn && fn != (void *)-1) fn(); }
	free(file); if (out_base) *out_base = base; return base;
}
void *lib_sym(const char *name) {
	for (Elf64_Sym *s = symtab + 1; (const char *)s < strtab; s++) if (s->st_shndx != SHN_UNDEF && !strcmp(strtab + s->st_name, name)) return base + s->st_value;
	return NULL;
}
void lib_verbose(int on) { quiet = !on; }
