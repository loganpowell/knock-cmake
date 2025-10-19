#include <iostream>
#include <filesystem>
#include "drmprocessorclientimpl.h"
#include "libgourou.h"
#include "libgourou_common.h"

#ifndef KNOCK_VERSION
#error KNOCK_VERSION must be defined
#endif

std::string get_data_dir();
void verify_absence(std::string file);
void verify_presence(std::string file);

int main(int argc, char **argv) try {
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
  std::filesystem::create_directories(data_dir);

  const std::string acsm_file = argv[1];
  const std::string acsm_stem = acsm_file.substr(0, acsm_file.find_last_of("."));
  const std::string drm_file = acsm_stem + ".drm";
  const std::string pdf_file = acsm_stem + ".pdf";
  const std::string epub_file = acsm_stem + ".epub";
  verify_presence(acsm_file);
  verify_absence(drm_file);
  verify_absence(pdf_file);
  verify_absence(epub_file);

  DRMProcessorClientImpl client;
  gourou::DRMProcessor *processor = gourou::DRMProcessor::createDRMProcessor(
      &client,
      false, // don't "always generate a new device" (default)
      data_dir
  );

  std::cout << "anonymously signing in..." << std::endl;
  processor->signIn("anonymous", "");
  processor->activateDevice();

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
      std::filesystem::remove(drm_file);
      std::filesystem::remove(acsm_file);
      std::cout << "PDF file generated at " << pdf_file << std::endl;
      break;
    }
    case gourou::DRMProcessor::ITEM_TYPE::EPUB: {
      // for epubs the drm is removed in-place so in == out
      processor->removeDRM(drm_file, drm_file, type);
      std::filesystem::rename(drm_file, epub_file);
      std::filesystem::remove(acsm_file);
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
} catch (const std::filesystem::filesystem_error &e) {
  std::cerr << "filesystem error: " << e.what() << std::endl;
  std::cerr << "Check file permissions and available disk space." << std::endl;
  return 1;
} catch (const std::exception &e) {
  std::cerr << "error: " << e.what() << std::endl;
  return 1;
}

std::string get_data_dir() {
  // Check for Lambda-specific temp directory first
  char *lambda_runtime_dir = std::getenv("LAMBDA_RUNTIME_DIR");
  if (lambda_runtime_dir != nullptr) {
    return std::string(lambda_runtime_dir) + "/knock/acsm";
  }
  
  // Check for Lambda task root
  char *lambda_task_root = std::getenv("LAMBDA_TASK_ROOT");
  if (lambda_task_root != nullptr) {
    return std::string(lambda_task_root) + "/tmp/knock/acsm";
  }
  
  // Standard Lambda temp directory
  if (std::filesystem::exists("/tmp") && std::filesystem::is_directory("/tmp")) {
    return "/tmp/knock/acsm";
  }

  // Fallback to XDG standard
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
  if (std::filesystem::exists(file)) {
    throw std::runtime_error("file " + file + " must be moved out of the way or deleted");
  }
}

void verify_presence(std::string file) {
  if (!std::filesystem::exists(file)) {
    throw std::runtime_error("file " + file + " does not exist");
  }
}
