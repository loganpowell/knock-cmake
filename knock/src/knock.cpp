#include <iostream>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <openssl/opensslv.h>
#include <openssl/crypto.h>
#include <curl/curl.h>
#include "drmprocessorclientimpl.h"
#include "libgourou.h"
#include "libgourou_common.h"

// Filesystem compatibility functions for older GCC
namespace fs_compat {
    bool exists(const std::string& path) {
        struct stat buffer;
        return (stat(path.c_str(), &buffer) == 0);
    }
    
    bool is_directory(const std::string& path) {
        struct stat buffer;
        return (stat(path.c_str(), &buffer) == 0 && S_ISDIR(buffer.st_mode));
    }
    
    bool create_directories(const std::string& path) {
        char* path_copy = strdup(path.c_str());
        char* p = path_copy;
        
        // Skip leading slash
        if (*p == '/') p++;
        
        while (*p) {
            while (*p && *p != '/') p++;
            char temp = *p;
            *p = 0;
            
            if (strlen(path_copy) > 0) {
                mkdir(path_copy, 0755);
            }
            
            if (temp == 0) break;
            *p = temp;
            p++;
        }
        
        free(path_copy);
        return true;
    }
    
    bool remove_file(const std::string& path) {
        return std::remove(path.c_str()) == 0;
    }
    
    bool rename_file(const std::string& from, const std::string& to) {
        return std::rename(from.c_str(), to.c_str()) == 0;
    }
}

#ifndef KNOCK_VERSION
#error KNOCK_VERSION must be defined
#endif

std::string get_data_dir();
void verify_absence(std::string file);
void verify_presence(std::string file);

int main(int argc, char **argv) try {
  // Print version information for debugging
  std::cerr << "[DEBUG] Knock version: " KNOCK_VERSION << std::endl;
  std::cerr << "[DEBUG] libgourou version: " LIBGOUROU_VERSION << std::endl;
  std::cerr << "[DEBUG] OpenSSL version: " << OPENSSL_VERSION_TEXT << std::endl;
  std::cerr << "[DEBUG] libcurl version: " << curl_version() << std::endl;
  
  // Check if running in Lambda
  const char* lambda_root = std::getenv("LAMBDA_TASK_ROOT");
  const char* aws_region = std::getenv("AWS_REGION");
  if (lambda_root) {
    std::cerr << "[DEBUG] Running in AWS Lambda" << std::endl;
    std::cerr << "[DEBUG] LAMBDA_TASK_ROOT: " << lambda_root << std::endl;
  }
  if (aws_region) {
    std::cerr << "[DEBUG] AWS_REGION: " << aws_region << std::endl;
  }
  
  if (argc == 1) {
    std::cout << "info: knock version " KNOCK_VERSION ", libgourou version " LIBGOUROU_VERSION "\n"
      "usage: " << argv[0] << " [ACSM]\n"
      "result: converts ACSM to a plain PDF/EPUB if present, otherwise prints this" << std::endl;
    return 0;
  }

  if (argc != 2) {
    throw std::invalid_argument("the ACSM file must be passed as the sole argument");
  }
  
  // Ensure data directory exists
  std::string data_dir = get_data_dir();
  fs_compat::create_directories(data_dir);

  const std::string acsm_file = argv[1];
  const std::string acsm_stem = acsm_file.substr(0, acsm_file.find_last_of("."));
  const std::string drm_file = acsm_stem + ".drm";
  const std::string pdf_file = acsm_stem + ".pdf";
  const std::string epub_file = acsm_stem + ".epub";
  verify_presence(acsm_file);
  verify_absence(drm_file);
  verify_absence(pdf_file);
  verify_absence(epub_file);

  std::cerr << "[DEBUG] Creating DRM processor with data_dir: " << data_dir << std::endl;
  
  DRMProcessorClientImpl client;
  gourou::DRMProcessor *processor = nullptr;
  
  try {
    processor = gourou::DRMProcessor::createDRMProcessor(
        &client,
        false, // don't "always generate a new device" (default)
        data_dir
    );
    std::cerr << "[DEBUG] DRM processor created successfully" << std::endl;
  } catch (const std::exception& e) {
    std::cerr << "[ERROR] Failed to create DRM processor: " << e.what() << std::endl;
    throw;
  }

  std::cout << "anonymously signing in..." << std::endl;
  std::cerr << "[DEBUG] Calling signIn()..." << std::endl;
  try {
    processor->signIn("anonymous", "");
    std::cerr << "[DEBUG] signIn() completed" << std::endl;
  } catch (const std::exception& e) {
    std::cerr << "[ERROR] signIn() failed: " << e.what() << std::endl;
    delete processor;
    throw;
  }
  
  std::cerr << "[DEBUG] Calling activateDevice()..." << std::endl;
  try {
    processor->activateDevice();
    std::cerr << "[DEBUG] activateDevice() completed" << std::endl;
  } catch (const std::exception& e) {
    std::cerr << "[ERROR] activateDevice() failed: " << e.what() << std::endl;
    delete processor;
    throw;
  }

  std::cout << "downloading the file from Adobe..." << std::endl;
  gourou::FulfillmentItem *item = processor->fulfill(acsm_file);
  gourou::DRMProcessor::ITEM_TYPE type = processor->download(item, drm_file);

  std::cout << "removing DRM from the file..." << std::endl;
  int result = 0;
  try {
    switch (type) {
    case gourou::DRMProcessor::ITEM_TYPE::PDF: {
      // for pdfs the function moves the pdf while removing drm
      processor->removeDRM(drm_file, pdf_file, type);
            std::cout << "downloaded pdf" << std::endl;
      fs_compat::remove_file(drm_file);
      fs_compat::remove_file(acsm_file);
      std::cout << "PDF file generated at " << pdf_file << std::endl;
      break;
    }
    case gourou::DRMProcessor::ITEM_TYPE::EPUB: {
      // for epubs the drm is removed in-place so in == out
      processor->removeDRM(drm_file, drm_file, type);
      std::cout << "downloaded epub" << std::endl;
      fs_compat::rename_file(drm_file, epub_file);
      fs_compat::remove_file(acsm_file);
      std::cout << "EPUB file generated at " << epub_file << std::endl;
      break;
    }
    default:
      throw std::domain_error("the downloaded file is not a PDF nor an EPUB");
    }
  } catch (...) {
    // Clean up processor before rethrowing
    delete processor;
    throw;
  }
  
  // Clean up processor
  delete processor;
  return result;
} catch (const gourou::Exception &e) {
  std::cerr << "gourou library error: " << e.what() << std::endl;
  std::cerr << "This typically indicates an issue with Adobe DRM processing." << std::endl;
  return 1;
} catch (const std::runtime_error &e) {
  std::cerr << "filesystem error: " << e.what() << std::endl;
  std::cerr << "Check file permissions and available disk space." << std::endl;
  return 1;
} catch (const std::exception &e) {
  std::cerr << "error: " << e.what() << std::endl;
  return 1;
}

std::string get_data_dir() {
  // For Lambda, always use /tmp as it's the only writable directory
  char *lambda_task_root = std::getenv("LAMBDA_TASK_ROOT");
  if (lambda_task_root != nullptr) {
    return "/tmp/knock/acsm";
  }
  
  // Standard Lambda temp directory (force rebuild)
  if (fs_compat::exists("/tmp") && fs_compat::is_directory("/tmp")) {
    return "/tmp/knock/acsm";
  }

  // Fallback to XDG standard for non-Lambda environments
  char *xdg_data_home = std::getenv("XDG_DATA_HOME");
  if (xdg_data_home != nullptr) {
    return std::string(xdg_data_home) + "/knock/acsm";
  }

  char *home = std::getenv("HOME");
  if (home != nullptr) {
    return std::string(home) + "/.local/share/knock/acsm";
  }

  return "/var/knock/acsm";
}

void verify_absence(std::string file) {
  if (fs_compat::exists(file)) {
    throw std::runtime_error("file " + file + " must be moved out of the way or deleted");
  }
}

void verify_presence(std::string file) {
  if (!fs_compat::exists(file)) {
    throw std::runtime_error("file " + file + " does not exist");
  }
}
