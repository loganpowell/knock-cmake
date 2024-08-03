cmake_minimum_required(VERSION 3.14.0)

project(libgourou VERSION 0.0.1 LANGUAGES C CXX)

# CXXFLAGS
# add_compile_options("-Wall" "-fPIC")
include_directories(
    "./include"
)
# the cross option can be done using normal CMake cross compile methods
set(BUILD_STATIC 0 CACHE BOOL "build libgourou as static if 1, nothing if 0 (default value), can not be combined with BUILD_SHARED")
set(BUILD_SHARED 1 CACHE BOOL "build libgourou as shared if 1 (default value), nothing if 0, can not be combined with BUILD_STATIC")

# support for origional debug option
if(DEBUG)
    set(CMAKE_BUILD_TYPE Debug)
else()
    set(CMAKE_BUILD_TYPE Release)
endif()
set(CMAKE_CXX_FLAGS_DEBUG_INIT "-ggdb -O0" "-DDEBUG")
set(CMAKE_CXX_FLAGS_RELEASE_INIT "-O2")

if(STATIC_NONCE)
    add_compile_options("-DSTATIC_NONCE=1")
endif()

set(SOURCES src/libgourou.cpp src/user.cpp src/device.cpp src/fulfillment_item.cpp src/loan_token.cpp src/bytearray.cpp)

### targets
# unfortunately cmake can't build both static and shared
if(BUILD_STATIC)
    add_library(libgourou STATIC ${SOURCES})
elseif(BUILD_SHARED)
    add_library(libgourou SHARED ${SOURCES})
endif()


#find denpendencies
include(FetchContent)
FetchContent_Declare(
    libpugixml
    GIT_REPOSITORY https://github.com/zeux/pugixml.git
    GIT_TAG 30cc354fe37114ec7a0a4ed2192951690357c2ed
)
FetchContent_MakeAvailable(libpugixml)
# target_compile_options(pugixml INTERFACE "-FI ${CMAKE_BINARY_DIR}/_deps/libpugixml-src/src/pugixml.cpp")

set(updfparser_DIR ${CMAKE_SOURCE_DIR}/uPDFParser)
add_subdirectory(${updfparser_DIR} ${CMAKE_BINARY_DIR}/uPDFParser EXCLUDE_FROM_ALL)
include_directories(${updfparser_DIR}/include)

# link dependencies
target_link_libraries(libgourou 
    PUBLIC libupdfparser
    PUBLIC pugixml::pugixml
)
