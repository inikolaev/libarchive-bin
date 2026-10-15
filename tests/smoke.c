#include <archive.h>
#include <archive_entry.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(x) do { if (!(x)) { fprintf(stderr, "check failed at line %d: %s\n", __LINE__, #x); exit(1); } } while (0)
static void roundtrip(int format, int filter) {
    char buffer[65536], payload[] = "Commander static libarchive smoke test\n", readback[128];
    size_t used = 0;
    struct archive *w = archive_write_new();
    CHECK(w != NULL);
    CHECK(archive_write_set_format(w, format) == ARCHIVE_OK);
    // ARCHIVE_WARN means an external compression program was selected: reject it.
    CHECK(archive_write_add_filter(w, filter) == ARCHIVE_OK);
    CHECK(archive_write_open_memory(w, buffer, sizeof(buffer), &used) == ARCHIVE_OK);
    struct archive_entry *e = archive_entry_new();
    archive_entry_set_pathname(e, "folder/");
    archive_entry_set_filetype(e, AE_IFDIR);
    archive_entry_set_perm(e, 0755);
    archive_entry_set_size(e, 0);
    CHECK(archive_write_header(w, e) == ARCHIVE_OK);
    archive_entry_clear(e);
    archive_entry_set_pathname(e, "folder/hello.txt");
    archive_entry_set_filetype(e, AE_IFREG);
    archive_entry_set_perm(e, 0644);
    archive_entry_set_size(e, sizeof(payload)-1);
    CHECK(archive_write_header(w, e) == ARCHIVE_OK);
    CHECK(archive_write_data(w, payload, sizeof(payload)-1) == sizeof(payload)-1);
    archive_entry_free(e);
    CHECK(archive_write_close(w) == ARCHIVE_OK);
    CHECK(archive_write_free(w) == ARCHIVE_OK);
    struct archive *r = archive_read_new();
    CHECK(archive_read_support_filter_all(r) == ARCHIVE_OK);
    CHECK(archive_read_support_format_all(r) == ARCHIVE_OK);
    CHECK(archive_read_open_memory(r, buffer, used) == ARCHIVE_OK);
    CHECK(archive_filter_code(r, 0) == filter);
    int files = 0, directories = 0;
    for (int i = 0; i < 2; ++i) {
        CHECK(archive_read_next_header(r, &e) == ARCHIVE_OK);
        if (archive_entry_filetype(e) == AE_IFDIR) {
            CHECK(strcmp(archive_entry_pathname(e), "folder/") == 0);
            directories++;
        } else {
            CHECK(strcmp(archive_entry_pathname(e), "folder/hello.txt") == 0);
            CHECK(archive_entry_size(e) == sizeof(payload)-1);
            CHECK(archive_read_data(r, readback, sizeof(readback)) == sizeof(payload)-1);
            CHECK(memcmp(payload, readback, sizeof(payload)-1) == 0);
            files++;
        }
    }
    CHECK(files == 1 && directories == 1);
    CHECK(archive_read_next_header(r, &e) == ARCHIVE_EOF);
    CHECK(archive_read_free(r) == ARCHIVE_OK);
}
int main(void) {
    CHECK(archive_version_number() == ARCHIVE_VERSION_NUMBER);
    CHECK(archive_zlib_version() != NULL);
    CHECK(archive_liblzma_version() != NULL);
    CHECK(archive_bzlib_version() != NULL);
    CHECK(archive_libzstd_version() != NULL);
    printf("%s\n", archive_version_details());
    int filters[] = {ARCHIVE_FILTER_NONE, ARCHIVE_FILTER_GZIP, ARCHIVE_FILTER_BZIP2, ARCHIVE_FILTER_XZ, ARCHIVE_FILTER_ZSTD};
    for (size_t i = 0; i < sizeof(filters)/sizeof(filters[0]); ++i)
        roundtrip(ARCHIVE_FORMAT_TAR_PAX_RESTRICTED, filters[i]);
    roundtrip(ARCHIVE_FORMAT_ZIP, ARCHIVE_FILTER_NONE);
    roundtrip(ARCHIVE_FORMAT_7ZIP, ARCHIVE_FILTER_NONE);
    struct archive *r = archive_read_new();
    archive_read_support_format_all(r);
    CHECK(archive_read_open_memory(r, "not an archive", 14) < ARCHIVE_OK);
    archive_read_free(r);
    puts("All archive/codec smoke tests passed");
}
