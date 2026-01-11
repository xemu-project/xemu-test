#include <hal/debug.h>

#include <hal/video.h>
#include <windows.h>
#include <nxdk/mount.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    XVideoSetMode(640, 480, 32, REFRESH_DEFAULT);

    for (int i = 0; i < 2; i++) {
        debugPrint("Hello nxdk!\n");
        Sleep(500);
    }

    BOOL ret = nxMountDrive('C', "\\Device\\Harddisk0\\Partition2\\");
    if (!ret) {
        debugPrint("Failed to mount C: drive!\n");
        goto shutdown;
    }

    CreateDirectoryA("C:\\results", NULL);

    FILE *f = fopen("C:\\results\\results.txt", "w");
    if (!f) {
        goto shutdown;
    }

    const char *buf = "Success";
    fwrite(buf, strlen(buf), 1, f);
    fclose(f);


shutdown:
    HalInitiateShutdown();
    while (1) {
        Sleep(2000);
    }

    return 0;
}
