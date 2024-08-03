cmake_minimum_required(VERSION 3.14)

project(knock-cmake VERSION 3.0.79 LANGUAGES C CXX)

set(BUILD_STATIC ON CACHE BOOL "" FORCE)
set(BUILD_SHARED OFF CACHE BOOL "" FORCE)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(BUILD_STATIC_LIBS ON CACHE BOOL "" FORCE)

add_subdirectory(lib/libgourou EXCLUDE_FROM_ALL)

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
