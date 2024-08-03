cmake_minimum_required(VERSION 3.14)

project(knock-cmake VERSION 0.0.1 LANGUAGES C CXX)

set(BUILD_STATIC 1)
set(BUILD_SHARED 0)
set(BUILD_SHARED_LIBS FALSE)

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
