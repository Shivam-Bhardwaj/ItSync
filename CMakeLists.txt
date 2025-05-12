cmake_minimum_required(VERSION 3.12) # Increased for better C++17 and filesystem support visibility

project(WinRealTimeDirSync VERSION 0.1.0 LANGUAGES CXX)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)
set(CMAKE_CXX_EXTENSIONS OFF) # Don't use compiler-specific extensions like -std=gnu++17

# Ensure correct settings for Windows, especially for Unicode
if(WIN32)
  add_compile_definitions(UNICODE _UNICODE)
  # For MSVC, /EHsc is a common default for exception handling
  # set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} /EHsc") # Usually handled by VS generator, but can be explicit
endif()

# Add the executable target and specify its source file
# Sources are relative to this CMakeLists.txt file's directory
add_executable(${PROJECT_NAME} src/RealTimeSync.cpp)

# If you had separate header files in an 'include' directory:
# target_include_directories(${PROJECT_NAME} PUBLIC include)

# For std::filesystem with some compilers/linkers (especially older MinGW or non-MSVC on Windows),
# you might need to explicitly link against the filesystem library.
# MSVC typically handles this automatically when C++17 is enabled.
# Example for GCC/Clang if needed:
# if(CMAKE_COMPILER_ID STREQUAL "GNU" OR CMAKE_COMPILER_ID STREQUAL "Clang")
#   # Check if __cpp_lib_filesystem is defined to indicate library support
#   include(CheckCXXSourceCompiles)
#   check_cxx_source_compiles("#include <filesystem>\nint main() { std::filesystem::path p; return 0; }" CXX_HAS_FILESYSTEM_HEADER)
#   if(NOT CXX_HAS_FILESYSTEM_HEADER)
#       message(WARNING "Compiler may not fully support <filesystem> header or may require linking -lstdc++fs or -lc++fs")
#   else()
#       # For some linkers, explicit linking might still be required
#       # target_link_libraries(${PROJECT_NAME} PRIVATE stdc++fs) # For GCC
#       # target_link_libraries(${PROJECT_NAME} PRIVATE c++fs)   # For Clang with libc++
#   endif()
# endif()

# Set output directory for the executable (optional, good practice)
# This will place the .exe in WinRealTimeDirSync/build/bin/
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
# For Visual Studio multi-config generators, you might want:
# set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_DEBUG ${CMAKE_BINARY_DIR}/bin/Debug)
# set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_RELEASE ${CMAKE_BINARY_DIR}/bin/Release)


# Enable CTest for testing (optional, for future expansion)
# enable_testing()
# add_test(NAME ${PROJECT_NAME}_Runs
#          COMMAND ${PROJECT_NAME} # Add dummy args or a test script
#          WORKING_DIRECTORY ${CMAKE_BINARY_DIR}/bin)