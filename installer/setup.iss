; Inno Setup script for Bluetooth Speaker Mirror.
;
; Compile with Inno Setup Compiler (ISCC.exe), either via build\build.ps1
; (which finds it automatically if installed) or manually:
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\setup.iss
;
; Requires that build\build.ps1 (or a manual PyInstaller build) has already
; produced ..\dist\BTSpeakerMirror\BTSpeakerMirror.exe before compiling this.

#define MyAppName "Bluetooth Speaker Mirror"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Bluetooth Speaker Mirror"
#define MyAppExeName "BTSpeakerMirror.exe"

[Setup]
AppId={{B7B6B7B0-2B7E-4E9B-9C7C-BTSPKRMIRROR}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=BTSpeakerMirrorSetup
Compression=lzma2
SolidCompression=yes
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\BTSpeakerMirror\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName} now"; Flags: nowait postinstall skipifsilent
