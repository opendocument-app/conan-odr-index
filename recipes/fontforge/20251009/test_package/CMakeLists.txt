cmake_minimum_required(VERSION 3.15)
project(FontForgeTest CXX)

find_package(fontforge CONFIG REQUIRED)

add_executable(link_test link_test.cpp)
target_link_libraries(link_test fontforge::fontforge)
