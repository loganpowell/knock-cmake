cmake_minimum_required(VERSION 3.15)

set(KNOCK_VERSION "0.0.0" CACHE STRING "Set Version of knock")
project(knock VERSION ${KNOCK_VERSION} LANGUAGES C CXX)

add_subdirectory(${CMAKE_SOURCE_DIR}/lib/libgourou EXCLUDE_FROM_ALL)

add_executable(knock src/knock.cpp)
target_include_directories(knock 
    PUBLIC ${CMAKE_SOURCE_DIR}/lib/libgourou/include
    PUBLIC ${CMAKE_SOURCE_DIR}/lib/libgourou/utils)
target_link_libraries(knock 
    PUBLIC libgourou
    PUBLIC libgourou_utils
)
target_compile_definitions(knock
    PUBLIC KNOCK_VERSION="${CMAKE_PROJECT_VERSION}"
)
