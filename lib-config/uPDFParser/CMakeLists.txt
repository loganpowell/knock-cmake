cmake_minimum_required(VERSION 3.14.0)

project(uPDFParser VERSION 0.0.1 LANGUAGES C CXX)

# CXXFLAGS
# add_compile_options("-Wall" "-fPIC")
include_directories(
    "./include"
)
# the cross option can be done using normal CMake cross compile methods 
set(BUILD_STATIC 0 CACHE BOOL "build libupdfparser as static if 1, nothing if 0 (default value), can not be combined with BUILD_SHARED")
set(BUILD_SHARED 1 CACHE BOOL "build libupdfparser as shared if 1 (default value), nothing if 0, can not be combined with BUILD_STATIC")

# support for origional debug option
if(DEBUG)
    set(CMAKE_BUILD_TYPE Debug)
else()
    set(CMAKE_BUILD_TYPE Release)
endif()
set(CMAKE_CXX_FLAGS_DEBUG_INIT "-ggdb -O0")
set(CMAKE_CXX_FLAGS_RELEASE_INIT "-O2")

set(SOURCES src/uPDFParser.cpp src/uPDFTypes.cpp)

if(WIN32)
include(FetchContent)

# unistd subsitute on windows
FetchContent_Declare(
    libunistd
# temporily dependent on a fork due to libunistd master branch not providing a working memmem polyfill
#   GIT_REPOSITORY https://github.com/robinrowe/libunistd.git
#   GIT_TAG        aa70d7b123d31f39ce1eb30331a4145123ae4f47 # master at 08/01/2024

    GIT_REPOSITORY https://github.com/Alvin-He/libunistd_memmemfix.git
    GIT_TAG master
)
FetchContent_MakeAvailable(libunistd)
include_directories(
    ${CMAKE_BINARY_DIR}/_deps/libunistd-src/unistd
    ${CMAKE_SOURCE_DIR}/windows
)
# memmem polyfill 
add_compile_options("-FI ${CMAKE_BINARY_DIR}/_deps/libunistd-src/unistd/mem.h")
# so msvc generate .lib files correctly
set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)
endif()

# unfortunately cmake can't build both static and shared
if(BUILD_STATIC)
    add_library(libupdfparser STATIC ${SOURCES})
elseif(BUILD_SHARED) 
    add_library(libupdfparser SHARED ${SOURCES})
endif()

#test 
add_executable(test tests/test.cpp)
target_link_libraries(test PUBLIC libupdfparser)
add_test(NAME test COMMAND test)