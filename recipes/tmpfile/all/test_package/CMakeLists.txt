cmake_minimum_required(VERSION 3.15)
project(tmpfile_tests CXX)

find_package(tmpfile CONFIG REQUIRED)

add_executable(${PROJECT_NAME} libTests.exe.cpp)
target_link_libraries(${PROJECT_NAME} tmpfile::tmpfile)
