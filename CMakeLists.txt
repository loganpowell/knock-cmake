
cmake_minimum_required(VERSION 3.14)

project(knock-cmake VERSION 0.0.1 LANGUAGES C CXX)

set(HELP "option overrided by top level CMakeLists.txt, please change the build configurations there instead of using -D...")

#set build configuration varibales, these paths must also be change in build.py if changed here. they must match
set(CMAKE_INSTALL_PREFIX "${CMAKE_SOURCE_DIR}/knock" CACHE STRING ${HELP} FORCE)

set(updfparser_DIR "${CMAKE_SOURCE_DIR}/~checkout/uPDFParser" CACHE STRING ${HELP} FORCE)
set(libgourou_DIR "${CMAKE_SOURCE_DIR}/~checkout/libgourou" CACHE STRING ${HELP} FORCE)

# default build static so a kernal can be published without having to deal with linking shared libraries
set(BUILD_STATIC ON CACHE BOOL ${HELP} FORCE)
set(BUILD_SHARED OFF CACHE BOOL ${HELP} FORCE)
set(BUILD_SHARED_LIBS OFF CACHE BOOL ${HELP} FORCE)
set(BUILD_STATIC_LIBS ON CACHE BOOL ${HELP} FORCE)
set(CMAKE_EXE_LINKER_FLAGS "-static") # enforce linking static on pre-built libraries

# this script is set up to track version 79 of knock
set(KNOCK_VERSION "3.0.79" CACHE STRING ${HELP} FORCE)

# this will add the knock target to the build. No EXCLUDE_FROM_ALL so the knock binary will be included by default 
add_subdirectory(${CMAKE_SOURCE_DIR}/~checkout/knock ${CMAKE_BINARY_DIR}/knock)
install(TARGETS knock DESTINATION ${CMAKE_INSTALL_PREFIX})