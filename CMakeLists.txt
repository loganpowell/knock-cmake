
cmake_minimum_required(VERSION 3.14)

project(knock-cmake VERSION 0.0.1 LANGUAGES C CXX)

set(HELP "option overrided by top level CMakeLists.txt, please change the build configurations there instead of using -D...")

#set build configuration varibales, these paths must also be change in build.py if changed here. they must match
set(CMAKE_INSTALL_PREFIX "${CMAKE_SOURCE_DIR}/build-output" CACHE STRING ${HELP} FORCE)

set(updfparser_DIR "${CMAKE_SOURCE_DIR}/deps/uPDFParser" CACHE STRING ${HELP} FORCE)
set(libgourou_DIR "${CMAKE_SOURCE_DIR}/deps/libgourou" CACHE STRING ${HELP} FORCE)

# default build static so a kernel can be published without having to deal with linking shared libraries
# Allow override from command line for container builds (e.g., -DBUILD_STATIC=OFF)
if(NOT DEFINED BUILD_STATIC)
    set(BUILD_STATIC ON CACHE BOOL "Build static libraries" FORCE)
    set(BUILD_SHARED OFF CACHE BOOL "Build shared libraries" FORCE)
    set(BUILD_SHARED_LIBS OFF CACHE BOOL "Build shared libraries" FORCE)
    set(BUILD_STATIC_LIBS ON CACHE BOOL "Build static libraries" FORCE)
    
    # Force CMake to prefer static libraries
    set(CMAKE_FIND_LIBRARY_SUFFIXES ".a" CACHE STRING "Library suffixes" FORCE)
    set(CMAKE_EXE_LINKER_FLAGS "-static-libgcc -static-libstdc++" CACHE STRING "Linker flags" FORCE)
endif()

# this script is set up to track version 79 of knock
set(KNOCK_VERSION "3.0.79" CACHE STRING ${HELP} FORCE)

# this will add the knock target to the build. No EXCLUDE_FROM_ALL so the knock binary will be included by default 
add_subdirectory(${CMAKE_SOURCE_DIR}/knock ${CMAKE_BINARY_DIR}/knock)
install(TARGETS knock DESTINATION .)
