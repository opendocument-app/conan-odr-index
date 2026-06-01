cmake_minimum_required(VERSION 3.15)
project(FontForgeTest C CXX)

find_package(fontforge CONFIG REQUIRED)

add_executable(link_test link_test.c)
target_link_libraries(link_test fontforge::fontforge)
set_target_properties(link_test PROPERTIES LINKER_LANGUAGE CXX)
