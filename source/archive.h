#ifndef ARC_LIBRARY_ARCHIVE_H
#define ARC_LIBRARY_ARCHIVE_H
typedef unsigned char al_u8;
typedef unsigned int al_u32;
typedef unsigned long long al_u64;
typedef struct { char name[256]; al_u32 offset, compressed, size, crc, method; } ALZipEntry;
int al_zip_scan(const al_u8 *bytes, al_u64 length, ALZipEntry *entries, al_u32 *count);
int al_aff_validate(const al_u8 *bytes, al_u64 length);
#endif

void al_sha256(const al_u8 *data, al_u64 length, char hex[65]);
