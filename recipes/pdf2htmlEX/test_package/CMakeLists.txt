cmake_minimum_required(VERSION 3.15)
project(pdf2htmlEXTest C)

find_package(pdf2htmlEX CONFIG REQUIRED)

add_executable(link_test src/link_test.c)
target_link_libraries(link_test pdf2htmlEX::pdf2htmlEX)

