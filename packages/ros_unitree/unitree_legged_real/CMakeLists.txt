cmake_minimum_required(VERSION 2.8.3)
project(unitree_legged_real)

# Unitree's official ROS-to-real bridge for Go1 (v3.8.0)
# From: https://github.com/unitreerobotics/unitree_ros_to_real
# Patched to use SDK from unitree_guide package

add_compile_options(-std=c++11)

find_package(catkin REQUIRED COMPONENTS
    roscpp
    geometry_msgs
    unitree_legged_msgs
)

catkin_package()

message("-- CMAKE_SYSTEM_PROCESSOR: ${CMAKE_SYSTEM_PROCESSOR}")
if("${CMAKE_SYSTEM_PROCESSOR}" MATCHES "x86_64.*")
  set(ARCH amd64)
else()
  set(ARCH arm64)
endif()

# SDK path: use the one bundled with unitree_guide
set(SDK_PATH ${CMAKE_CURRENT_SOURCE_DIR}/../unitree_guide/unitree_guide/library/unitree_legged_sdk-3.8.0)

link_directories(${SDK_PATH}/lib/cpp/${ARCH})

# Use static library (.a) — the Go1 SDK ships as static
set(EXTRA_LIBS -pthread libunitree_legged_sdk.a lcm)

set(CMAKE_CXX_FLAGS "-O3 -fPIC")

include_directories(
    include
    ${catkin_INCLUDE_DIRS}
    ${SDK_PATH}/include
)

# High-level walk example
add_executable(example_walk src/exe/example_walk.cpp)
target_link_libraries(example_walk ${EXTRA_LIBS} ${catkin_LIBRARIES})
add_dependencies(example_walk ${${PROJECT_NAME}_EXPORTED_TARGETS} ${catkin_EXPORTED_TARGETS})

# Low-level position example
add_executable(example_position src/exe/example_position.cpp)
target_link_libraries(example_position ${EXTRA_LIBS} ${catkin_LIBRARIES})
add_dependencies(example_position ${${PROJECT_NAME}_EXPORTED_TARGETS} ${catkin_EXPORTED_TARGETS})

# State subscriber (prints robot feedback)
add_executable(state_sub src/exe/state_sub.cpp)
target_link_libraries(state_sub ${EXTRA_LIBS} ${catkin_LIBRARIES})
add_dependencies(state_sub ${${PROJECT_NAME}_EXPORTED_TARGETS} ${catkin_EXPORTED_TARGETS})

# ROS-UDP bridge (high_cmd/low_cmd topics <-> UDP)
add_executable(ros_udp src/exe/ros_udp.cpp)
target_link_libraries(ros_udp ${EXTRA_LIBS} ${catkin_LIBRARIES})
add_dependencies(ros_udp ${${PROJECT_NAME}_EXPORTED_TARGETS} ${catkin_EXPORTED_TARGETS})

# Keyboard control (WASD -> /cmd_vel)
add_executable(control_via_keyboard src/exe/control_via_keyboard.cpp)
target_link_libraries(control_via_keyboard ${EXTRA_LIBS} ${catkin_LIBRARIES})
add_dependencies(control_via_keyboard ${${PROJECT_NAME}_EXPORTED_TARGETS} ${catkin_EXPORTED_TARGETS})

# Twist subscriber (/cmd_vel -> high-level walk)
add_executable(twist_sub src/exe/twist_sub.cpp)
target_link_libraries(twist_sub ${EXTRA_LIBS} ${catkin_LIBRARIES})
add_dependencies(twist_sub ${${PROJECT_NAME}_EXPORTED_TARGETS} ${catkin_EXPORTED_TARGETS})
