; FreeCrawl independent NSIS installer fallback.
; This is NOT compiled by PortableApps.com Installer and is NOT a certified PA.c release.
; It is a real Windows installer whose payload uses the PortableApps.com folder layout.
; Preserve the existing Data directory throughout every update.
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "StrFunc.nsh"
${StrStr}
!ifndef STAGE_DIR
  !error "Missing STAGE_DIR. Pass /DSTAGE_DIR=<absolute directory> to makensis."
!endif
!ifndef OUTPUT_FILE
  !error "Missing OUTPUT_FILE. Pass /DOUTPUT_FILE=<absolute file> to makensis."
!endif
!ifndef APP_VERSION
  !error "Missing APP_VERSION. Pass /DAPP_VERSION=x.y.z to makensis."
!endif

Unicode True
Name "FreeCrawl SEO Tool Portable (Independent Package)"
OutFile "${OUTPUT_FILE}"
InstallDir "$EXEDIR"
RequestExecutionLevel user
SetCompressor /SOLID lzma
SetCompressorDictSize 16
ShowInstDetails show
AutoCloseWindow true

VIProductVersion "${APP_VERSION}.0"
VIAddVersionKey "ProductName" "FreeCrawl SEO Tool Portable"
VIAddVersionKey "FileDescription" "FreeCrawl independent portable installer"
VIAddVersionKey "CompanyName" "Independent FreeCrawl Portable Builder"
VIAddVersionKey "FileVersion" "${APP_VERSION}"
VIAddVersionKey "OriginalFilename" "FreeCrawlPortable.paf.exe"
Icon "${STAGE_DIR}\App\AppInfo\appicon.ico"

!define MUI_ABORTWARNING
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_LANGUAGE "English"

Section "Install or update FreeCrawl Portable" SecMain
    ; $INSTDIR is the *parent* directory (e.g. X:\PortableApps).
    ; Check that the application executable isn't running before modifying App.
    ; tasklist is a documented Windows system command; no plugins or registry writes.
    nsExec::ExecToStack '"$SYSDIR\tasklist.exe" /FI "IMAGENAME eq FreeCrawl SEO Tool.exe" /FO CSV /NH'
    Pop $0
    Pop $1
    StrCmp $0 "0" +3
      MessageBox MB_OK|MB_ICONSTOP "Unable to verify that FreeCrawl is closed. Close the app and retry."
      Abort
    ${StrStr} $2 $1 "FreeCrawl SEO Tool.exe"
    StrCmp $2 "" +3
      MessageBox MB_OK|MB_ICONSTOP "FreeCrawl is running. Close FreeCrawl SEO Tool before updating."
      Abort

    ; Never delete, replace, or overwrite files under Data.
    ; Remove old program binaries to avoid retaining stale files after upgrades.
    RMDir /r "$INSTDIR\FreeCrawlPortable\App"
    RMDir /r "$INSTDIR\FreeCrawlPortable\Other"
    SetOutPath "$INSTDIR\FreeCrawlPortable"
    File /oname=FreeCrawlPortable.exe "${STAGE_DIR}\FreeCrawlPortable.exe"
    File /oname=help.html "${STAGE_DIR}\help.html"
    SetOutPath "$INSTDIR\FreeCrawlPortable\App"
    File /r "${STAGE_DIR}\App\*.*"
    SetOutPath "$INSTDIR\FreeCrawlPortable\Other"
    File /r "${STAGE_DIR}\Other\*.*"
    CreateDirectory "$INSTDIR\FreeCrawlPortable\App\DefaultData"
    CreateDirectory "$INSTDIR\FreeCrawlPortable\Data"
SectionEnd
