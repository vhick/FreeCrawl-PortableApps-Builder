// FreeCrawlPortable: conventional, auditable Win32 C++ launcher.
// No registry changes, elevated privileges, process injection, or background persistence.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <filesystem>
#include <string>
#include <system_error>

namespace fs = std::filesystem;

static void errorMessage(const std::wstring &message, DWORD code = 0) {
    std::wstring text = message;
    if (code) text += L"\nWindows error: " + std::to_wstring(code);
    MessageBoxW(nullptr, text.c_str(), L"FreeCrawl Portable", MB_OK | MB_ICONERROR);
}

static std::wstring forwardedArgs() {
    const wchar_t *cmd = GetCommandLineW();
    if (!cmd) return L"";
    // Preserve the original Windows command-line quoting for all forwarded parameters.
    if (*cmd == L'"') {
        ++cmd;
        while (*cmd && *cmd != L'"') ++cmd;
        if (*cmd == L'"') ++cmd;
    } else {
        while (*cmd && *cmd != L' ' && *cmd != L'\t') ++cmd;
    }
    return std::wstring(cmd); // Includes separating whitespace, if any.
}

int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) {
    wchar_t filename[32768] = {};
    const DWORD length = GetModuleFileNameW(nullptr, filename, 32768);
    if (!length || length >= 32768) {
        errorMessage(L"Cannot locate the portable launcher.", GetLastError());
        return 1;
    }
    const fs::path root = fs::path(filename).parent_path();
    const fs::path executable = root / L"App" / L"FreeCrawl" / L"FreeCrawl SEO Tool.exe";
    const fs::path data = root / L"Data";
    const fs::path profile = data / L"Profile";
    const fs::path chromium = profile / L"Chromium";
    const fs::path browsers = profile / L"playwright-browsers";
    const fs::path cache = data / L"Cache";
    const fs::path temp = data / L"Temp";
    if (!fs::exists(executable)) {
        errorMessage(L"FreeCrawl application executable was not found:\n" + executable.wstring());
        return 2;
    }
    std::error_code ec;
    for (const auto &dir : {data, profile, chromium, browsers, cache, temp}) {
        fs::create_directories(dir, ec);
        if (ec) {
            errorMessage(L"Cannot create portable data folder:\n" + dir.wstring());
            return 3;
        }
    }
    // Child-only environment; the user's Windows environment is never changed permanently.
    if (!SetEnvironmentVariableW(L"FREECRAWL_PORTABLE_PROFILE", profile.c_str()) ||
        !SetEnvironmentVariableW(L"PLAYWRIGHT_BROWSERS_PATH", browsers.c_str()) ||
        !SetEnvironmentVariableW(L"TEMP", temp.c_str()) ||
        !SetEnvironmentVariableW(L"TMP", temp.c_str())) {
        errorMessage(L"Could not set the portable process environment.", GetLastError());
        return 4;
    }
    // Electron main-process patch also sets userData and sessionData before app.whenReady().
    // Chromium's switches provide a second line of protection for disk-cache paths.
    std::wstring command = L"\"" + executable.wstring() +
        L"\" --user-data-dir=\"" + profile.wstring() +
        L"\" --disk-cache-dir=\"" + cache.wstring() + L"\"" + forwardedArgs();
    STARTUPINFOW si{};
    si.cb = sizeof(si);
    PROCESS_INFORMATION pi{};
    if (!CreateProcessW(executable.c_str(), command.data(), nullptr, nullptr, FALSE,
                        0, nullptr, executable.parent_path().c_str(), &si, &pi)) {
        errorMessage(L"Cannot launch FreeCrawl.", GetLastError());
        return 5;
    }
    CloseHandle(pi.hThread);
    // Wait so the menu launcher remains associated with the running app.
    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD exitCode = 0;
    if (!GetExitCodeProcess(pi.hProcess, &exitCode)) exitCode = 6;
    CloseHandle(pi.hProcess);
    return static_cast<int>(exitCode);
}
