
cmake_minimum_required(VERSION 3.15)

project(knock-cmake VERSION 0.0.1 LANGUAGES C CXX)

set(HELP "option overrided by top level CMakeLists.txt, please change the build configurations there instead of using -D...")

#set build configuration varibales
set(CMAKE_INSTALL_PREFIX "${CMAKE_SOURCE_DIR}/knock" CACHE STRING ${HELP} FORCE)

set(BUILD_STATIC ON CACHE BOOL ${HELP} FORCE)
set(BUILD_SHARED OFF CACHE BOOL ${HELP} FORCE)
set(BUILD_SHARED_LIBS OFF CACHE BOOL ${HELP} FORCE)
set(BUILD_STATIC_LIBS ON CACHE BOOL ${HELP} FORCE)

set(KNOCK_VERSION "3.0.79" CACHE STRING ${HELP} FORCE)

# this will add the knock target to the build. No EXCLUDE_FROM_ALL so the knock binary will be included by default 
add_subdirectory(${CMAKE_SOURCE_DIR}/checkout/knock)
install(TARGETS knock DESTINATION ${CMAKE_INSTALL_PREFIX})