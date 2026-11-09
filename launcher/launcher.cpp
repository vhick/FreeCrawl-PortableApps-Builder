// FreeCrawl SEO Tool PortableApps community launcher, b1r1.
// No elevation, registry modification, host file harvesting, or global environment changes.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <filesystem>
#include <string>
#include <vector>

namespace fs = std::filesystem;

static std::wstring executablePath() {
  std::vector<wchar_t> buffer(512);
  for (;;) {
    DWORD n = GetModuleFileNameW(nullptr, buffer.data(), static_cast<DWORD>(buffer.size()));
    if (n == 0) return L"";
    if (n < buffer.size() - 1) return std::wstring(buffer.data(), n);
    if (buffer.size() >= 32768) return L"";
    buffer.resize(buffer.size() * 2);
  }
}

static void errorBox(const wchar_t* message) {
  MessageBoxW(nullptr, message, L"FreeCrawl SEO Tool Portable", MB_OK | MB_ICONERROR);
}

int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR arguments, int) {
  try {
    auto self = executablePath();
    if (self.empty()) { errorBox(L"Cannot locate the portable launcher."); return 10; }
    const fs::path root = fs::path(self).parent_path();
    const fs::path application = root / L"App" / L"FreeCrawl" / L"FreeCrawl SEO Tool.exe";
    const fs::path data = root / L"Data";
    const fs::path profile = data / L"Profile";
    const fs::path temp = data / L"Temp";
    const fs::path browser = profile / L"playwright-browsers";
    // Never silently follow a linked Data directory into an unrelated host profile.
    if (fs::exists(data) && fs::is_symlink(fs::symlink_status(data))) {
      errorBox(L"Data is a symbolic link or junction. Inspect the destination before launching.");
      return 15;
    }
    if (!fs::is_regular_file(application)) {
      errorBox(L"App\\FreeCrawl\\FreeCrawl SEO Tool.exe is missing. Reinstall without deleting Data.");
      return 11;
    }
    fs::create_directories(profile);
    fs::create_directories(temp);
    fs::create_directories(browser);

    // Child-scoped only: never alter permanent Windows environment variables.
    // Electron's app.setPath calls in the patched main module do the primary redirection.
    if (!SetEnvironmentVariableW(L"FREECRAWL_PORTABLE_DATA", data.c_str()) ||
        !SetEnvironmentVariableW(L"PLAYWRIGHT_BROWSERS_PATH", browser.c_str()) ||
        !SetEnvironmentVariableW(L"TEMP", temp.c_str()) ||
        !SetEnvironmentVariableW(L"TMP", temp.c_str())) {
      errorBox(L"Could not prepare isolated application paths.");
      return 12;
    }
    // The wWinMain argument string is the Windows-provided, already-quoted command tail.
    // Preserve it verbatim (including Unicode and quotes).
    std::wstring command = L"\"" + application.wstring() + L"\"";
    if (arguments && arguments[0]) { command += L" "; command += arguments; }
    std::vector<wchar_t> mutableCommand(command.begin(), command.end());
    mutableCommand.push_back(L'\0');

    STARTUPINFOW startup{};
    startup.cb = sizeof(startup);
    PROCESS_INFORMATION child{};
    const std::wstring executable = application.wstring();
    const std::wstring workingDir = application.parent_path().wstring();
    if (!CreateProcessW(executable.c_str(), mutableCommand.data(), nullptr, nullptr,
                        FALSE, 0, nullptr, workingDir.c_str(), &startup, &child)) {
      errorBox(L"FreeCrawl could not start. Inspect Windows Event Viewer and the portable Data folder.");
      return 13;
    }
    CloseHandle(child.hThread);
    // Tray windows and downloads can continue after a window closes. Wait for the main
    // Electron process; its own orderly shutdown owns its browser/worker lifecycle.
    WaitForSingleObject(child.hProcess, INFINITE);
    DWORD exitCode = 1;
    GetExitCodeProcess(child.hProcess, &exitCode);
    CloseHandle(child.hProcess);
    return static_cast<int>(exitCode);
  } catch (...) {
    errorBox(L"Portable storage could not be initialized. Check disk access and free space.");
    return 14;
  }
}
