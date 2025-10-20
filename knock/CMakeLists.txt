cmake_minimum_required(VERSION 3.14)

set(KNOCK_VERSION "0.0.0" CACHE STRING "Set Version of knock")
project(knock VERSION ${KNOCK_VERSION} LANGUAGES C CXX)

if(NOT DEFINED libgourou_DIR)
    message(FATAL_ERROR "knock depends on libgourou, please define libgourou_DIR so cmake can find it.")
endif()

add_subdirectory(${libgourou_DIR} ${CMAKE_BINARY_DIR}/libgourou EXCLUDE_FROM_ALL)

add_executable(knock src/knock.cpp)
target_include_directories(knock 
    PUBLIC ${libgourou_DIR}/include
    PUBLIC ${libgourou_DIR}/utils)
target_link_libraries(knock 
    PUBLIC libgourou
    PUBLIC libgourou_utils
)
target_compile_definitions(knock
    PUBLIC KNOCK_VERSION="${KNOCK_VERSION}"
)

# Ensure adept_activate is built alongside knock
# Since libgourou is added with EXCLUDE_FROM_ALL, we need to explicitly build adept_activate
add_dependencies(knock adept_activate)

# Install adept_activate alongside knock
install(TARGETS adept_activate DESTINATION .)
