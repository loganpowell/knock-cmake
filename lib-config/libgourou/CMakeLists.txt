cmake_minimum_required(VERSION 3.14.0)

file(READ "include/libgourou.h" file_contain_version)
string(REGEX MATCH "\#define[ \t\r\n]*LIBGOUROU_VERSION[ \t\r\n]*\"(.*)\"" _ file_contain_version)
project(libgourou VERSION ${CMAKE_MATCH_1} LANGUAGES C CXX)

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

set(libgourou_SOURCES src/libgourou.cpp src/user.cpp src/device.cpp src/fulfillment_item.cpp src/loan_token.cpp src/bytearray.cpp)
set(utilsCommon_SOURCES utils/drmprocessorclientimpl.cpp utils/utils_common.cpp)

### targets
# unfortunately cmake can't build both static and shared
if(BUILD_STATIC)
    add_library(libgourou STATIC ${libgourou_SOURCES})
    add_library(libgourou_utils STATIC ${utilsCommon_SOURCES})
elseif(BUILD_SHARED)
    add_library(libgourou SHARED ${libgourou_SOURCES})
    add_library(libgourou_utils SHARED ${utilsCommon_SOURCES})
endif()


#find denpendencies

set(updfparser_DIR ${CMAKE_SOURCE_DIR}/lib/uPDFParser)
add_subdirectory(${updfparser_DIR} ${CMAKE_BINARY_DIR}/uPDFParser EXCLUDE_FROM_ALL)
target_include_directories(libgourou PUBLIC ${updfparser_DIR}/include)

find_package(OpenSSL REQUIRED COMPONENTS Crypto SSL)
target_include_directories(libgourou_utils PUBLIC ${OPENSSL_INCLUDE_DIR})

find_package(CURL REQUIRED)
target_include_directories(libgourou_utils PUBLIC ${CURL_INCLUDE_DIRS})

include(FindZLIB REQUIRED)
target_include_directories(libgourou_utils PUBLIC ${ZLIB_INCLUDE_DIRS})

include(FetchContent)
FetchContent_Declare(
    libpugixml
    GIT_REPOSITORY https://github.com/zeux/pugixml.git
    GIT_TAG 30cc354fe37114ec7a0a4ed2192951690357c2ed
)
FetchContent_Declare(
    libzip
    GIT_REPOSITORY https://github.com/nih-at/libzip.git
    GIT_TAG v1.10.1
)
set(LIBZIP_DO_INSTALL OFF CACHE BOOL "" FORCE) # prevent libzip from installing 

FetchContent_MakeAvailable(libpugixml libzip)

# link dependencies
target_link_libraries(libgourou 
    PUBLIC libupdfparser
    PUBLIC pugixml::pugixml
)
target_link_libraries(libgourou_utils
    PUBLIC libgourou
    PUBLIC pugixml::pugixml
    PUBLIC ${OPENSSL_LIBRARIES}
    PUBLIC ${CURL_LIBRARIES}
    PUBLIC ${ZLIB_LIBRARIES}
    PUBLIC zip
)
