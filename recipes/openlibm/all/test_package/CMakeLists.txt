cmake_minimum_required(VERSION 3.15)
project(link_test C)

find_package(openlibm CONFIG REQUIRED)

add_executable(${PROJECT_NAME} link_test.c)
target_link_libraries(${PROJECT_NAME} openlibm::openlibm)
