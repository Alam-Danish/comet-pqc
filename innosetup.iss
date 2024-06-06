; Inno Setup template

#ifndef Version
    #error The define variable Version is not set! Use /D Version=value to set it.
#endif

#define Organization "HEPHY"
#define Name "PQC"
#define ExeName "pqc.exe"

[Setup]
AppId={#Organization}_{#Name}_{#Version}
AppName={#Name}
AppVersion={#Version}
AppPublisher=HEPHY Detector Development
AppPublisherURL=https://github.com/hephy-dd/
DefaultDirName={userappdata}\{#Organization}\pqc\{#Version}
DefaultGroupName={#Name}
OutputDir=dist
OutputBaseFilename=pqc-{#Version}-win-x64-setup
SetupIconFile=pqc\assets\icons\pqc.ico
UninstallDisplayIcon={app}\{#ExeName}
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest

[Files]
Source: "dist\pqc\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userdesktop}\{#Name} {#Version}"; Filename: "{app}\{#ExeName}"
Name: "{group}\{#Name} {#Version}"; Filename: "{app}\{#ExeName}"; WorkingDir: "{app}"

[Run]
Filename: "{app}\{#ExeName}"; Description: "{cm:LaunchProgram,{#Name} {#Version}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[UninstallRun]
Filename: "{app}\uninstall.exe"
