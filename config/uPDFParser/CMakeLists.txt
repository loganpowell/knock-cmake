cmake_minimum_required(VERSION 3.14.0)

project(uPDFParser VERSION 0.0.0 LANGUAGES C CXX)

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