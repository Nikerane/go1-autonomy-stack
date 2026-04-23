#include "unitree_legged_sdk/unitree_legged_sdk.h"
#include <unistd.h>
#include <cstring>
#include <iostream>

using namespace UNITREE_LEGGED_SDK;

int main(int argc, char *argv[]) {
    int target_mode = 5; // default: stand down
    if (argc > 1) {
        target_mode = atoi(argv[1]);
    }

    const char* mode_names[] = {
        "idle", "force stand", "vel walk", "pos walk", "",
        "stand DOWN", "stand UP", "damping", "recovery"
    };
    if (target_mode >= 0 && target_mode <= 8 && strlen(mode_names[target_mode]) > 0) {
        std::cout << "Sending mode " << target_mode << " (" << mode_names[target_mode] << ")..." << std::endl;
    } else {
        std::cout << "Sending mode " << target_mode << "..." << std::endl;
    }

    UDP udp(8090, "192.168.123.161", 8082, sizeof(HighCmd), sizeof(HighState));
    HighCmd cmd = {0};
    HighState state = {0};

    udp.InitCmdData(cmd);

    cmd.mode = target_mode;

    // Send for 3 seconds at 100Hz
    for (int i = 0; i < 300; i++) {
        udp.SetSend(cmd);
        udp.Send();
        udp.Recv();
        udp.GetRecv(state);
        if (i % 50 == 0) {
            std::cout << "  tick=" << i << " current_mode=" << (int)state.mode
                      << " battery=" << (int)state.bms.SOC << "%" << std::endl;
        }
        usleep(10000); // 10ms
    }

    std::cout << "Done. Final mode: " << (int)state.mode << std::endl;
    return 0;
}
